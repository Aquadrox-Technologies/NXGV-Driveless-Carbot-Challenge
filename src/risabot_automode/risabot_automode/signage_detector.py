#!/usr/bin/env python3
"""
Signage Detector Node — YOLOv5 BPU Model Inference via hobot_dnn

Loads the compiled .bin model, subscribes to camera raw images,
runs hardware-accelerated BPU inference, and publishes processed state updates.
Features a platform-check so it runs gracefully on RDK X5 and idles on non-RDK systems.
"""

import time
from typing import Dict

import cv2
import numpy as np
import rclpy
from cv_bridge import CvBridge
from rcl_interfaces.msg import SetParametersResult
from rclpy.node import Node
from rclpy.qos import QoSPresetProfiles
from sensor_msgs.msg import Image
from std_msgs.msg import Bool, String

# Import topics from our shared module
from .topics import (
    CAMERA_IMAGE_TOPIC,
    HILL_SIGN_TOPIC,
    PARKING_SIGN_TOPIC,
    SIGNAGE_DEBUG_TOPIC,
    TRAFFIC_LIGHT_TOPIC,
)

# Graceful import of BPU runtime library
try:
    import hobot_dnn
    BPU_AVAILABLE = True
except ImportError:
    BPU_AVAILABLE = False


class SignageDetector(Node):
    """BPU-accelerated signage detector node for competition signs & traffic lights."""

    def __init__(self):
        super().__init__('signage_detector')

        # ── Tunable parameters ─────────────────────────────────────────────
        self.declare_parameter('model_path',             '/home/sunrise/risabot_signs_640x640_nv12.bin')
        self.declare_parameter('conf_threshold',         0.40)
        self.declare_parameter('iou_threshold',          0.45)
        self.declare_parameter('show_debug',             False)
        self.declare_parameter('heartbeat_sec',          0.5)
        self.declare_parameter('min_parking_sign_width', 0)  # Min pixel width for parking sign trigger (0 = disable)

        self._param_cache: Dict[str, object] = {}
        self._update_param_cache()
        self.add_on_set_parameters_callback(self._on_params)

        self.bridge = CvBridge()
        self.bpu_available = BPU_AVAILABLE

        # ── Detection & Gating state ────────────────────────────────────────
        self.hill_sign_active = False
        self.parking_sign_active = False
        self.traffic_light_active = 'unknown'

        self.detected_hill_consecutive = 0
        self.detected_parking_consecutive = 0
        self.detected_tl_red_consecutive = 0
        self.detected_tl_green_consecutive = 0
        self.detected_tl_yellow_consecutive = 0

        # ── ROS publishers & subscribers ────────────────────────────────────
        self.parking_pub = self.create_publisher(Bool, PARKING_SIGN_TOPIC, 10)
        self.traffic_light_pub = self.create_publisher(String, TRAFFIC_LIGHT_TOPIC, 10)
        self.hill_pub = self.create_publisher(Bool, HILL_SIGN_TOPIC, 10)
        self.debug_pub = self.create_publisher(Image, SIGNAGE_DEBUG_TOPIC, 10)

        # Heartbeat timer — continuously publishes last states to keep topics fresh
        self._heartbeat_timer = self.create_timer(
            float(self._param_cache['heartbeat_sec']),
            self.publish_states
        )

        # ── Initialize BPU Runtime ──────────────────────────────────────────
        if self.bpu_available:
            try:
                model_path = str(self._param_cache['model_path'])
                self.get_logger().info(f'Loading BPU model from: {model_path}')
                self.models = hobot_dnn.load(model_path)
                self.model = self.models[0]
                self.get_logger().info('BPU model loaded successfully.')
            except Exception as e:
                self.get_logger().error(f'Failed to load BPU model: {e}')
                self.bpu_available = False

        if not self.bpu_available:
            self.get_logger().warn(
                'hobot_dnn runtime not available or failed to load. '
                'Node will operate in dummy/idle mode (no BPU inference).'
            )

        # Camera raw subscriber
        self.color_sub = self.create_subscription(
            Image,
            CAMERA_IMAGE_TOPIC,
            self.image_callback,
            QoSPresetProfiles.SENSOR_DATA.value
        )
        self.get_logger().info('Signage Detector node initialized.')

    # ──────────────────────────────────────────────────────────────────────────
    # Parameter management
    # ──────────────────────────────────────────────────────────────────────────

    def _update_param_cache(self) -> None:
        self._param_cache = {
            'model_path':             str(self.get_parameter('model_path').value),
            'conf_threshold':         float(self.get_parameter('conf_threshold').value),
            'iou_threshold':          float(self.get_parameter('iou_threshold').value),
            'show_debug':             bool(self.get_parameter('show_debug').value),
            'heartbeat_sec':          float(self.get_parameter('heartbeat_sec').value),
            'min_parking_sign_width': int(self.get_parameter('min_parking_sign_width').value),
        }

    def _on_params(self, params) -> SetParametersResult:
        for p in params:
            if p.name in self._param_cache:
                self._param_cache[p.name] = p.value
        return SetParametersResult(successful=True)

    # ──────────────────────────────────────────────────────────────────────────
    # State publishing helper
    # ──────────────────────────────────────────────────────────────────────────

    def publish_states(self) -> None:
        """Publish the current latch states of the sign/light flags."""
        self.parking_pub.publish(Bool(data=self.parking_sign_active))
        self.traffic_light_pub.publish(String(data=self.traffic_light_active))
        self.hill_pub.publish(Bool(data=self.hill_sign_active))

    # ──────────────────────────────────────────────────────────────────────────
    # Image preprocessing (BGR to NV12)
    # ──────────────────────────────────────────────────────────────────────────

    def bgr_to_nv12(self, bgr: np.ndarray) -> np.ndarray:
        """Resize BGR image to 640x640 and convert to NV12 layout for BPU."""
        # 1. Resize image to model input shape
        resized = cv2.resize(bgr, (640, 640), interpolation=cv2.INTER_LINEAR)
        # 2. Convert to YUV I420
        yuv = cv2.cvtColor(resized, cv2.COLOR_BGR2YUV_I420)
        # yuv has shape (960, 640)
        
        # 3. Extract planar components
        y = yuv[0:640, :]
        u = yuv[640:800, :]
        v = yuv[800:960, :]
        
        # 4. Interleave U and V for NV12 format
        u_flat = u.reshape(-1)
        v_flat = v.reshape(-1)
        
        uv_interleaved = np.zeros(len(u_flat) + len(v_flat), dtype=np.uint8)
        uv_interleaved[0::2] = u_flat
        uv_interleaved[1::2] = v_flat
        uv_planar = uv_interleaved.reshape(320, 640)
        
        # 5. Stack Y and interleaved UV planes
        nv12 = np.vstack((y, uv_planar))
        return nv12

    # ──────────────────────────────────────────────────────────────────────────
    # Vectorized Non-Maximum Suppression
    # ──────────────────────────────────────────────────────────────────────────

    def nms(self, boxes: np.ndarray, scores: np.ndarray, iou_threshold: float) -> list:
        """Standard vectorized NMS in Numpy."""
        if len(boxes) == 0:
            return []
        x1 = boxes[:, 0]
        y1 = boxes[:, 1]
        x2 = boxes[:, 2]
        y2 = boxes[:, 3]
        areas = (x2 - x1) * (y2 - y1)
        
        order = scores.argsort()[::-1]
        keep = []
        
        while order.size > 0:
            i = order[0]
            keep.append(i)
            
            xx1 = np.maximum(x1[i], x1[order[1:]])
            yy1 = np.maximum(y1[i], y1[order[1:]])
            xx2 = np.minimum(x2[i], x2[order[1:]])
            yy2 = np.minimum(y2[i], y2[order[1:]])
            
            w = np.maximum(0.0, xx2 - xx1)
            h = np.maximum(0.0, yy2 - yy1)
            
            inter = w * h
            ovr = inter / (areas[i] + areas[order[1:]] - inter)
            
            inds = np.where(ovr <= iou_threshold)[0]
            order = order[inds + 1]
            
        return keep

    # ──────────────────────────────────────────────────────────────────────────
    # Main camera callback
    # ──────────────────────────────────────────────────────────────────────────

    def image_callback(self, msg: Image) -> None:
        """Receive image, perform BPU inference, parse predictions, filter and publish."""
        if not self.bpu_available:
            return

        try:
            # Convert ROS Image to OpenCV BGR
            bgr = self.bridge.imgmsg_to_cv2(msg, 'bgr8')
            
            # Preprocess to NV12 format
            nv12 = self.bgr_to_nv12(bgr)
            
            # Forward pass on BPU
            # hobot_dnn forward takes list of inputs
            outputs = self.model.forward([nv12])
            pred = outputs[0].buffer
            
            # Reshape/squeeze predictions to 2D
            if len(pred.shape) == 3:
                pred = pred[0] # Shape is now (25200, nc + 5)
                
            conf_threshold = float(self._param_cache['conf_threshold'])
            iou_threshold = float(self._param_cache['iou_threshold'])
            
            # YOLOv5 outputs: box coordinates [0:4], objectness score [4], class scores [5:]
            # Calculate absolute score = objectness * class_probability
            scores = pred[:, 4:5] * pred[:, 5:]
            class_ids = np.argmax(pred[:, 5:], axis=1)
            max_scores = pred[:, 4] * pred[np.arange(len(pred)), 5 + class_ids]
            
            # Filter by confidence threshold
            keep_indices = max_scores >= conf_threshold
            filtered_boxes = pred[keep_indices, 0:4]
            filtered_scores = max_scores[keep_indices]
            filtered_class_ids = class_ids[keep_indices]
            
            if len(filtered_boxes) > 0:
                # Convert from [x_center, y_center, w, h] to [x1, y1, x2, y2]
                x_center = filtered_boxes[:, 0]
                y_center = filtered_boxes[:, 1]
                w = filtered_boxes[:, 2]
                h = filtered_boxes[:, 3]
                
                x1 = x_center - w / 2.0
                y1 = y_center - h / 2.0
                x2 = x_center + w / 2.0
                y2 = y_center + h / 2.0
                
                boxes_x1y1x2y2 = np.stack([x1, y1, x2, y2], axis=1)
                
                # Perform Non-Maximum Suppression
                keep = self.nms(boxes_x1y1x2y2, filtered_scores, iou_threshold)
                final_boxes = boxes_x1y1x2y2[keep]
                final_scores = filtered_scores[keep]
                final_class_ids = filtered_class_ids[keep]
            else:
                final_boxes = np.empty((0, 4))
                final_scores = np.array([])
                final_class_ids = np.array([])

            # Update detection states and publish updates
            self.update_detection_states(final_boxes, final_class_ids)
            self.publish_states()

            # Render debug frames if requested
            if self._param_cache['show_debug']:
                self.draw_debug(bgr, final_boxes, final_scores, final_class_ids)

        except Exception as e:
            self.get_logger().error(f'Inference error: {e}')

    # ──────────────────────────────────────────────────────────────────────────
    # Temporal filtering / confidence gating
    # ──────────────────────────────────────────────────────────────────────────

    def update_detection_states(self, boxes: np.ndarray, class_ids: np.ndarray) -> None:
        """Applies hysteresis / temporal filtering on current detections."""
        
        # 1. Hill sign (Class 0)
        saw_hill = 0 in class_ids
        if saw_hill:
            self.detected_hill_consecutive = min(10, self.detected_hill_consecutive + 1)
            if self.detected_hill_consecutive >= 3:
                self.hill_sign_active = True
        else:
            self.detected_hill_consecutive = max(0, self.detected_hill_consecutive - 1)
            if self.detected_hill_consecutive == 0:
                self.hill_sign_active = False

        # 2. Parking sign (Class 1)
        # Optional: check if the bounding box meets minimum width constraints
        saw_parking = False
        min_width = int(self._param_cache['min_parking_sign_width'])
        
        for idx, cid in enumerate(class_ids):
            if cid == 1:
                if min_width > 0:
                    box = boxes[idx]
                    box_w = box[2] - box[0]
                    if box_w >= min_width:
                        saw_parking = True
                        break
                else:
                    saw_parking = True
                    break

        if saw_parking:
            self.detected_parking_consecutive = min(10, self.detected_parking_consecutive + 1)
            if self.detected_parking_consecutive >= 3:
                self.parking_sign_active = True
        else:
            self.detected_parking_consecutive = max(0, self.detected_parking_consecutive - 1)
            if self.detected_parking_consecutive == 0:
                self.parking_sign_active = False

        # 3. Traffic light states
        # Classes: 2: traffic_light, 3: traffic_light_green, 4: traffic_light_red, 5: traffic_light_yellow
        saw_red = (2 in class_ids) or (4 in class_ids)
        saw_green = 3 in class_ids
        saw_yellow = 5 in class_ids

        if saw_red:
            self.detected_tl_red_consecutive = min(10, self.detected_tl_red_consecutive + 1)
            self.detected_tl_green_consecutive = 0
            self.detected_tl_yellow_consecutive = 0
            if self.detected_tl_red_consecutive >= 3:
                self.traffic_light_active = 'red'
        elif saw_green:
            self.detected_tl_green_consecutive = min(10, self.detected_tl_green_consecutive + 1)
            self.detected_tl_red_consecutive = 0
            self.detected_tl_yellow_consecutive = 0
            if self.detected_tl_green_consecutive >= 3:
                self.traffic_light_active = 'green'
        elif saw_yellow:
            self.detected_tl_yellow_consecutive = min(10, self.detected_tl_yellow_consecutive + 1)
            self.detected_tl_red_consecutive = 0
            self.detected_tl_green_consecutive = 0
            if self.detected_tl_yellow_consecutive >= 3:
                self.traffic_light_active = 'yellow'
        else:
            # Decay all states
            self.detected_tl_red_consecutive = max(0, self.detected_tl_red_consecutive - 1)
            self.detected_tl_green_consecutive = max(0, self.detected_tl_green_consecutive - 1)
            self.detected_tl_yellow_consecutive = max(0, self.detected_tl_yellow_consecutive - 1)
            
            if (self.detected_tl_red_consecutive == 0 and 
                    self.detected_tl_green_consecutive == 0 and 
                    self.detected_tl_yellow_consecutive == 0):
                self.traffic_light_active = 'unknown'

    # ──────────────────────────────────────────────────────────────────────────
    # Debug visualization publisher
    # ──────────────────────────────────────────────────────────────────────────

    def draw_debug(self, bgr: np.ndarray, boxes: np.ndarray, scores: np.ndarray, class_ids: np.ndarray) -> None:
        """Resize original frame to 640x640, overlay boxes/labels and publish debug stream."""
        debug_img = cv2.resize(bgr, (640, 640), interpolation=cv2.INTER_LINEAR)
        
        CLASS_NAMES = [
            'hill_sign',             # Class 0
            'parking_sign',          # Class 1
            'traffic_light',         # Class 2
            'traffic_light_green',   # Class 3
            'traffic_light_red',     # Class 4
            'traffic_light_yellow'   # Class 5
        ]
        
        COLOR_MAP = [
            (255, 0, 0),     # Hill sign (Blue)
            (0, 255, 0),     # Parking sign (Green)
            (0, 0, 255),     # Traffic light generic (Red)
            (0, 255, 0),     # Traffic light green (Green)
            (0, 0, 255),     # Traffic light red (Red)
            (0, 255, 255),   # Traffic light yellow (Yellow)
        ]

        for i, box in enumerate(boxes):
            x1, y1, x2, y2 = map(int, box)
            score = scores[i]
            cid = class_ids[i]
            
            name = CLASS_NAMES[cid] if cid < len(CLASS_NAMES) else f'class_{cid}'
            color = COLOR_MAP[cid] if cid < len(COLOR_MAP) else (255, 255, 255)
            
            # Draw bbox
            cv2.rectangle(debug_img, (x1, y1), (x2, y2), color, 2)
            
            # Label background & text
            label = f'{name}: {score:.2f}'
            text_size = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.45, 1)[0]
            cv2.rectangle(debug_img, (x1, y1 - text_size[1] - 8), (x1 + text_size[0], y1), color, -1)
            cv2.putText(
                debug_img,
                label,
                (x1, y1 - 4),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.45,
                (255, 255, 255) if color != (0, 255, 255) else (0, 0, 0),
                1,
                lineType=cv2.LINE_AA
            )
            
        # Draw status summaries on top left
        summary_text = (
            f"HILL: {'ACTIVE' if self.hill_sign_active else 'OFF'} "
            f"| PARK: {'ACTIVE' if self.parking_sign_active else 'OFF'} "
            f"| TL: {self.traffic_light_active.upper()}"
        )
        cv2.putText(
            debug_img,
            summary_text,
            (10, 25),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.55,
            (0, 255, 0) if self.parking_sign_active or self.hill_sign_active else (255, 255, 255),
            2,
            lineType=cv2.LINE_AA
        )

        try:
            debug_msg = self.bridge.cv2_to_imgmsg(debug_img, encoding='bgr8')
            self.debug_pub.publish(debug_msg)
        except Exception as e:
            self.get_logger().error(f'Failed to publish debug image: {e}')


def main(args=None) -> None:
    rclpy.init(args=args)
    node = SignageDetector()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
