#!/usr/bin/env python3
"""
Signage Detector Node — YOLOv8 Object Detection for RISA-Bot

Runs a trained YOLOv8-nano model on camera frames to detect parking signage
(and optionally traffic lights, stop signs, etc.).

When a parking sign is detected with sufficient confidence for N consecutive
frames AND the bounding box is large enough (close enough), publishes True
on /parking_signboard_detected to trigger the parking maneuver.

Topics:
  Subscribes: /camera/color/image_raw (Image)
  Publishes:  /parking_signboard_detected (Bool)
              /signage_detections (String, JSON)
              /camera/debug/signage (Image)
"""

import json
import time
from pathlib import Path
from typing import Dict, List, Optional

import cv2
import numpy as np
import rclpy
from cv_bridge import CvBridge
from rcl_interfaces.msg import SetParametersResult
from rclpy.node import Node
from rclpy.qos import QoSPresetProfiles
from sensor_msgs.msg import Image
from std_msgs.msg import Bool, String

from .topics import (
    CAMERA_DEBUG_SIGNAGE_TOPIC,
    CAMERA_IMAGE_TOPIC,
    PARKING_SIGN_TOPIC,
    SIGNAGE_DETECTIONS_TOPIC,
)


# ── Auto-discover workspace root and model path ─────────────────────────
_THIS_DIR = Path(__file__).resolve().parent
_WS_ROOT = _THIS_DIR.parent.parent.parent  # risabotcar_ws/

# Common locations where best.pt might live (searched in order)
_MODEL_SEARCH_PATHS = [
    _WS_ROOT / 'tools' / 'train_signage_model' / 'runs',
    _WS_ROOT / 'models',
    _THIS_DIR / 'models',
    _THIS_DIR,
]


def _find_best_pt() -> str:
    """Search known directories for the most recent best.pt file."""
    for search_root in _MODEL_SEARCH_PATHS:
        if search_root.exists():
            candidates = list(search_root.rglob('best.pt'))
            if candidates:
                # Return the most recently modified one
                best = max(candidates, key=lambda p: p.stat().st_mtime)
                return str(best)
    return ''


class SignageDetector(Node):
    """YOLOv8-based signage detector with confidence gating."""

    def __init__(self):
        super().__init__('signage_detector')

        # ── Parameters ───────────────────────────────────────────────────
        self.declare_parameter('model_path', _find_best_pt())
        self.declare_parameter('confidence_threshold', 0.6)
        self.declare_parameter('min_bbox_area', 800)          # px² minimum to trigger
        self.declare_parameter('required_confidence', 3)       # consecutive frames
        self.declare_parameter('process_every_n', 2)           # frame skip (1=every)
        self.declare_parameter('resize_width', 320)
        self.declare_parameter('parking_class_name', 'parking_sign')
        self.declare_parameter('show_debug', True)
        self.declare_parameter('print_debug', False)
        self.declare_parameter('debug_print_rate', 0.5)
        self.declare_parameter('heartbeat_sec', 0.5)

        self._param_cache: Dict[str, object] = {}
        self._update_param_cache()
        self.add_on_set_parameters_callback(self._on_params)

        # ── Load YOLO model ──────────────────────────────────────────────
        self.model = None
        self.model_loaded = False
        self._load_model()

        # ── Publishers ───────────────────────────────────────────────────
        self.signboard_pub = self.create_publisher(Bool, PARKING_SIGN_TOPIC, 10)
        self.detections_pub = self.create_publisher(
            String, SIGNAGE_DETECTIONS_TOPIC, 10
        )
        self.debug_pub = self.create_publisher(
            Image, CAMERA_DEBUG_SIGNAGE_TOPIC, 10
        )

        # ── Subscriber ───────────────────────────────────────────────────
        self.bridge = CvBridge()
        self.camera_sub = self.create_subscription(
            Image,
            CAMERA_IMAGE_TOPIC,
            self.camera_callback,
            QoSPresetProfiles.SENSOR_DATA.value,
        )

        # ── Detection state ──────────────────────────────────────────────
        self.frame_count = 0
        self.parking_confidence_count = 0
        self.parking_detected = False
        self._last_debug_print = 0.0

        # ── Heartbeat — re-publish last state on a timer ─────────────────
        self._heartbeat_timer = self.create_timer(
            float(self._param_cache['heartbeat_sec']),
            self._heartbeat_publish,
        )

        self.get_logger().info('Signage Detector started (YOLOv8)')

    # ──────────────────────────────────────────────────────────────────────
    # Parameter helpers
    # ──────────────────────────────────────────────────────────────────────

    def _update_param_cache(self) -> None:
        self._param_cache = {
            'model_path':            str(self.get_parameter('model_path').value),
            'confidence_threshold':  float(self.get_parameter('confidence_threshold').value),
            'min_bbox_area':         int(self.get_parameter('min_bbox_area').value),
            'required_confidence':   int(self.get_parameter('required_confidence').value),
            'process_every_n':       int(self.get_parameter('process_every_n').value),
            'resize_width':          int(self.get_parameter('resize_width').value),
            'parking_class_name':    str(self.get_parameter('parking_class_name').value),
            'show_debug':            bool(self.get_parameter('show_debug').value),
            'print_debug':           bool(self.get_parameter('print_debug').value),
            'debug_print_rate':      float(self.get_parameter('debug_print_rate').value),
            'heartbeat_sec':         float(self.get_parameter('heartbeat_sec').value),
        }

    def _on_params(self, params) -> SetParametersResult:
        for p in params:
            if p.name in self._param_cache:
                self._param_cache[p.name] = p.value
            # Reload model if path changed
            if p.name == 'model_path':
                self._load_model()
        return SetParametersResult(successful=True)

    # ──────────────────────────────────────────────────────────────────────
    # Model loading
    # ──────────────────────────────────────────────────────────────────────

    def _load_model(self) -> None:
        """Load YOLOv8 model from the configured path."""
        model_path = self._param_cache.get('model_path', '')

        # Auto-discover if no path configured or path doesn't exist
        if not model_path or not Path(model_path).exists():
            discovered = _find_best_pt()
            if discovered:
                model_path = discovered
                self._param_cache['model_path'] = discovered
                self.get_logger().info(
                    f'Auto-discovered model: {discovered}'
                )

        if not model_path:
            self.get_logger().warn(
                'No model_path set and no best.pt found in workspace. '
                'Signage detection disabled. '
                'Set the model_path parameter to your trained best.pt file.'
            )
            self.model = None
            self.model_loaded = False
            return

        path = Path(model_path)
        if not path.exists():
            self.get_logger().error(f'Model file not found: {path}')
            self.model = None
            self.model_loaded = False
            return

        try:
            from ultralytics import YOLO
            self.model = YOLO(str(path))
            self.model_loaded = True
            # Log class names from the model
            class_names = self.model.names if hasattr(self.model, 'names') else {}
            self.get_logger().info(
                f'Loaded YOLO model: {path.name} '
                f'({len(class_names)} classes: {class_names})'
            )
        except ImportError:
            self.get_logger().error(
                'ultralytics not installed! Run: pip install ultralytics'
            )
            self.model = None
            self.model_loaded = False
        except Exception as e:
            self.get_logger().error(f'Failed to load model {path}: {e}')
            self.model = None
            self.model_loaded = False

    # ──────────────────────────────────────────────────────────────────────
    # Camera callback
    # ──────────────────────────────────────────────────────────────────────

    def camera_callback(self, msg: Image) -> None:
        """Run YOLO inference on camera frame."""
        if not self.model_loaded or self.model is None:
            return

        # Frame skipping for performance
        self.frame_count += 1
        skip = max(1, int(self._param_cache['process_every_n']))
        if self.frame_count % skip != 0:
            return

        try:
            bgr = self.bridge.imgmsg_to_cv2(msg, 'bgr8')
            h, w = bgr.shape[:2]

            # Resize for faster inference
            resize_w = self._param_cache['resize_width']
            if resize_w > 0 and w > resize_w:
                scale = resize_w / float(w)
                bgr = cv2.resize(bgr, (resize_w, int(h * scale)))

            # ── Run YOLO inference ───────────────────────────────────────
            results = self.model(
                bgr,
                conf=self._param_cache['confidence_threshold'],
                verbose=False,
            )

            # ── Parse detections ─────────────────────────────────────────
            parking_class = self._param_cache['parking_class_name']
            min_area = self._param_cache['min_bbox_area']
            parking_found = False
            detections: List[Dict] = []

            if results and len(results) > 0:
                result = results[0]
                if result.boxes is not None and len(result.boxes) > 0:
                    for box in result.boxes:
                        cls_id = int(box.cls[0])
                        conf = float(box.conf[0])
                        class_name = self.model.names.get(cls_id, f'class_{cls_id}')

                        # Bounding box (xyxy format)
                        x1, y1, x2, y2 = box.xyxy[0].tolist()
                        bbox_area = (x2 - x1) * (y2 - y1)

                        det = {
                            'class': class_name,
                            'confidence': round(conf, 3),
                            'bbox': [round(x1), round(y1), round(x2), round(y2)],
                            'area': round(bbox_area),
                        }
                        detections.append(det)

                        # Check for parking sign with sufficient size
                        if class_name == parking_class and bbox_area >= min_area:
                            parking_found = True

            # ── Confidence gating (consecutive frames) ───────────────────
            if parking_found:
                self.parking_confidence_count += 1
            else:
                self.parking_confidence_count = 0

            required = self._param_cache['required_confidence']
            new_detected = self.parking_confidence_count >= required

            # Only publish on state change
            if new_detected != self.parking_detected:
                self.parking_detected = new_detected
                sign_msg = Bool()
                sign_msg.data = new_detected
                self.signboard_pub.publish(sign_msg)
                if new_detected:
                    self.get_logger().info(
                        f'PARKING SIGN DETECTED (confidence: {self.parking_confidence_count})'
                    )
                else:
                    self.get_logger().info('Parking sign lost')

            # ── Publish all detections as JSON ───────────────────────────
            if detections:
                det_msg = String()
                det_msg.data = json.dumps(detections, separators=(',', ':'))
                self.detections_pub.publish(det_msg)

            # ── Debug visualization ──────────────────────────────────────
            if self._param_cache['show_debug']:
                self._draw_debug(bgr, detections, parking_found, required)

            # ── Console debug ────────────────────────────────────────────
            if self._param_cache['print_debug'] and detections:
                now = time.monotonic()
                if now - self._last_debug_print >= self._param_cache['debug_print_rate']:
                    classes = [d['class'] for d in detections]
                    print(
                        f'\r[SIG] Detections: {classes} '
                        f'| Park: {self.parking_confidence_count}/{required}',
                        end='', flush=True,
                    )
                    self._last_debug_print = now

        except Exception as e:
            self.get_logger().error(f'Signage detection error: {e}')

    # ──────────────────────────────────────────────────────────────────────
    # Debug visualization
    # ──────────────────────────────────────────────────────────────────────

    def _draw_debug(
        self,
        bgr: np.ndarray,
        detections: List[Dict],
        parking_found: bool,
        required: int,
    ) -> None:
        """Draw bounding boxes and status on debug image."""
        debug = bgr.copy()

        COLOR_MAP = {
            'parking_sign': (0, 255, 0),         # green
            'traffic_light_red': (0, 0, 255),     # red
            'traffic_light_yellow': (0, 255, 255), # yellow
            'traffic_light_green': (0, 255, 0),   # green
            'stop_sign': (0, 0, 255),             # red
        }
        DEFAULT_COLOR = (255, 255, 0)  # cyan

        for det in detections:
            x1, y1, x2, y2 = det['bbox']
            class_name = det['class']
            conf = det['confidence']
            color = COLOR_MAP.get(class_name, DEFAULT_COLOR)

            cv2.rectangle(debug, (x1, y1), (x2, y2), color, 2)
            label = f'{class_name} {conf:.2f}'
            (tw, th), _ = cv2.getTextSize(
                label, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 1
            )
            cv2.rectangle(
                debug, (x1, y1 - th - 6), (x1 + tw + 4, y1), color, -1
            )
            cv2.putText(
                debug, label, (x1 + 2, y1 - 4),
                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 1,
            )

        # Status bar
        status_text = (
            f'PARK: {self.parking_confidence_count}/{required} '
            f'| {"TRIGGERED" if self.parking_detected else "waiting"}'
        )
        status_color = (0, 255, 0) if self.parking_detected else (200, 200, 200)
        cv2.putText(
            debug, status_text, (5, 20),
            cv2.FONT_HERSHEY_SIMPLEX, 0.55, status_color, 2,
        )

        self.debug_pub.publish(
            self.bridge.cv2_to_imgmsg(debug, encoding='bgr8')
        )

    # ──────────────────────────────────────────────────────────────────────
    # Heartbeat
    # ──────────────────────────────────────────────────────────────────────

    def _heartbeat_publish(self) -> None:
        """Re-publish current detection state on a timer."""
        sign_msg = Bool()
        sign_msg.data = self.parking_detected
        self.signboard_pub.publish(sign_msg)


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
