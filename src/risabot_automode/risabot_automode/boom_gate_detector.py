#!/usr/bin/env python3
"""
Boom Gate Detector Node (Pure Camera Red Bar Detection)
=========================================================
Detects whether a red boom gate barrier is blocking the lane ahead
using the camera color feed.

Isolates red pixels (HSV), checks for horizontal bar contours across
the lower-to-middle ROI (y: 0.20 to 0.98, x: 0.05 to 0.95), and applies
hysteresis filtering.

Publishes Bool on /boom_gate_open (True = open/clear, False = blocked).
"""

from typing import Dict
import rclpy
from rclpy.node import Node
from rclpy.qos import QoSPresetProfiles
from rcl_interfaces.msg import SetParametersResult
from std_msgs.msg import Bool

try:
    import cv2
    from cv_bridge import CvBridge
    from sensor_msgs.msg import Image
    CV_AVAILABLE = True
except ImportError:
    CV_AVAILABLE = False

from .topics import BOOM_GATE_TOPIC


class BoomGateDetector(Node):
    """Pure camera-based Boom Gate Detector node."""

    def __init__(self):
        super().__init__('boom_gate_detector')

        # --- Parameters ---
        self.declare_parameter('enable_camera', True)
        self.declare_parameter('cam_roi_y_min', 0.20)     # 20% from top
        self.declare_parameter('cam_roi_y_max', 0.98)     # 98% (down to hood)
        self.declare_parameter('cam_red_min_width', 40)   # min contour width (pixels)
        self.declare_parameter('cam_red_sat_min', 30)     # low sat for indoor lighting
        self.declare_parameter('cam_red_val_min', 30)     # low val for dim/shadowed bars
        self.declare_parameter('hysteresis', 3)
        self.declare_parameter('heartbeat_sec', 0.1)

        self._param_cache: Dict[str, object] = {}
        self._update_param_cache()
        self.add_on_set_parameters_callback(self._on_params)

        # Publisher
        self.gate_pub = self.create_publisher(Bool, BOOM_GATE_TOPIC, 10)

        # Subscriber
        self.camera_blocked = False
        if CV_AVAILABLE:
            self.bridge = CvBridge()
            self.cam_sub = self.create_subscription(
                Image,
                '/camera/color/image_raw',
                self.camera_callback,
                QoSPresetProfiles.SENSOR_DATA.value
            )

        # State
        self.gate_blocked = False
        self.blocked_count = 0
        self.clear_count = 0

        # Heartbeat timer to guarantee continuous publishing (prevents stale warnings)
        self._heartbeat_timer = self.create_timer(
            float(self._param_cache['heartbeat_sec']),
            self._heartbeat_publish
        )

        self.get_logger().info(
            f'Boom Gate Detector Started (PURE CAMERA) | CV_AVAILABLE={CV_AVAILABLE} | '
            f'sat_min={self._param_cache["cam_red_sat_min"]} | val_min={self._param_cache["cam_red_val_min"]}'
        )

    def _update_param_cache(self) -> None:
        """Cache frequently used parameters."""
        self._param_cache = {
            'enable_camera': bool(self.get_parameter('enable_camera').value),
            'cam_roi_y_min': float(self.get_parameter('cam_roi_y_min').value),
            'cam_roi_y_max': float(self.get_parameter('cam_roi_y_max').value),
            'cam_red_min_width': int(self.get_parameter('cam_red_min_width').value),
            'cam_red_sat_min': int(self.get_parameter('cam_red_sat_min').value),
            'cam_red_val_min': int(self.get_parameter('cam_red_val_min').value),
            'hysteresis': int(self.get_parameter('hysteresis').value),
            'heartbeat_sec': float(self.get_parameter('heartbeat_sec').value),
        }

    def _on_params(self, params) -> SetParametersResult:
        """Update cached parameters when set via CLI or services."""
        for p in params:
            if p.name in self._param_cache:
                self._param_cache[p.name] = p.value
        return SetParametersResult(successful=True)

    def _heartbeat_publish(self) -> None:
        """Publish last gate state on a fixed heartbeat."""
        gate_msg = Bool()
        gate_msg.data = not self.gate_blocked
        self.gate_pub.publish(gate_msg)

    def camera_callback(self, msg: Image) -> None:
        if not CV_AVAILABLE or not self._param_cache.get('enable_camera', True):
            self.camera_blocked = False
            self._eval_and_publish()
            return

        try:
            cv_img = self.bridge.imgmsg_to_cv2(msg, 'bgr8')
            h, w = cv_img.shape[:2]
            if w != 320 or h != 240:
                cv_img = cv2.resize(cv_img, (320, 240))
                h, w = 240, 320

            # Scan full lower-to-middle region (20% to 98% of height) to catch red bar up-close
            y_min = int(h * float(self._param_cache.get('cam_roi_y_min', 0.20)))
            y_max = int(h * float(self._param_cache.get('cam_roi_y_max', 0.98)))
            x_min = int(w * 0.05)
            x_max = int(w * 0.95)

            roi = cv_img[y_min:y_max, x_min:x_max]
            hsv = cv2.cvtColor(roi, cv2.COLOR_BGR2HSV)

            sat_min = int(self._param_cache.get('cam_red_sat_min', 30))
            val_min = int(self._param_cache.get('cam_red_val_min', 30))

            # Red hue ranges in HSV (handles warm red to crimson)
            mask1 = cv2.inRange(hsv, (0, sat_min, val_min), (15, 255, 255))
            mask2 = cv2.inRange(hsv, (155, sat_min, val_min), (180, 255, 255))
            mask = cv2.bitwise_or(mask1, mask2)

            # Morphological close with horizontal kernel to join red bar segments
            kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (15, 3))
            mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)

            contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

            min_w = int(self._param_cache.get('cam_red_min_width', 40))
            found_red_bar = False
            for cnt in contours:
                x, y, cw, ch = cv2.boundingRect(cnt)
                aspect = float(cw) / max(1.0, float(ch))
                # Horizontal red bar spanning horizontally (aspect >= 1.8 and width >= min_w)
                if cw >= min_w and aspect >= 1.8:
                    found_red_bar = True
                    break

            self.camera_blocked = found_red_bar
            self._eval_and_publish()

        except Exception as e:
            self.get_logger().error(f"Camera boom gate processing error: {e}")

    def _eval_and_publish(self) -> None:
        """Evaluate camera detection status with hysteresis filtering."""
        is_blocked = self.camera_blocked

        # Hysteresis to avoid flicker
        if is_blocked:
            self.blocked_count += 1
            self.clear_count = 0
        else:
            self.clear_count += 1
            self.blocked_count = 0

        hysteresis = int(self._param_cache.get('hysteresis', 3))
        if self.blocked_count >= hysteresis and not self.gate_blocked:
            self.gate_blocked = True
            self.get_logger().warn('Boom gate CLOSED - red horizontal bar detected by camera!')
        elif self.clear_count >= hysteresis and self.gate_blocked:
            self.gate_blocked = False
            self.get_logger().info('Boom gate OPEN - path clear')

        # Publish
        gate_msg = Bool()
        gate_msg.data = not self.gate_blocked  # True = open
        self.gate_pub.publish(gate_msg)

        status = "CLOSED" if self.gate_blocked else "OPEN"
        self.get_logger().debug(
            f"{status} | cam_blocked:{self.camera_blocked} | "
            f"blocked_cnt:{self.blocked_count} | clear_cnt:{self.clear_count}"
        )


def main(args=None) -> None:
    rclpy.init(args=args)
    node = BoomGateDetector()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
