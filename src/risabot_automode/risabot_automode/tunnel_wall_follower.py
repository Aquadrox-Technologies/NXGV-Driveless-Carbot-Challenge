#!/usr/bin/env python3
"""
Tunnel Wall Follower Node — RANSAC Enhanced
=============================================================================
LiDAR-based wall following for the tunnel section where camera lane detection
may not work due to poor lighting/visibility.

Uses RANSAC line fitting to extract wall distance AND heading angle from 2D
LiDAR scans, enabling a dual-error PD controller for both centering and
alignment.

References:
  - "A Wall-Following Navigation Method for Autonomous Driving Based on
    LiDAR in Tunnel Scenes" (IEEE)
  - F1TENTH Lab 3: Wall Following (UPenn)
  - RANSAC: Fischler & Bolles, "Random Sample Consensus" (1981)

Publishes Twist on /tunnel_cmd_vel for auto_driver to use when in TUNNEL state.
"""

import math
from typing import Dict, Optional, Tuple

import numpy as np
import rclpy
from geometry_msgs.msg import Twist
from rcl_interfaces.msg import SetParametersResult
from rclpy.node import Node
from rclpy.qos import QoSPresetProfiles
from sensor_msgs.msg import LaserScan
from std_msgs.msg import Bool

from .topics import TUNNEL_CMD_TOPIC, TUNNEL_DETECTED_TOPIC


class TunnelWallFollower(Node):
    """LiDAR-based wall following with RANSAC line fitting."""

    def __init__(self):
        super().__init__('tunnel_wall_follower')

        # --- Parameters (existing + new RANSAC/hysteresis) ---
        self.declare_parameter('target_center_dist', 0.0)
        self.declare_parameter('forward_speed', 0.15)
        self.declare_parameter('kp', 1.2)
        self.declare_parameter('kd', 0.3)
        self.declare_parameter('kp_heading', 0.8)
        self.declare_parameter('kd_heading', 0.2)
        self.declare_parameter('max_angular', 0.8)
        self.declare_parameter('left_angle_min', 0.52)        # ~30°
        self.declare_parameter('left_angle_max', 1.57)        # ~90°
        self.declare_parameter('right_angle_min', -1.57)      # ~-90°
        self.declare_parameter('right_angle_max', -0.52)      # ~-30°
        self.declare_parameter('lidar_angle_offset', 1.5708)  # 90° mount correction
        self.declare_parameter('min_wall_points', 3)
        self.declare_parameter('max_wall_dist', 0.60)
        self.declare_parameter('ransac_threshold', 0.02)      # inlier distance (m)
        self.declare_parameter('ransac_iterations', 50)
        self.declare_parameter('tunnel_hysteresis_frames', 3)
        self.declare_parameter('heartbeat_sec', 0.2)

        self._param_cache: Dict[str, object] = {}
        self._update_param_cache()
        self.add_on_set_parameters_callback(self._on_params)

        # Publishers
        self.cmd_vel_pub = self.create_publisher(Twist, TUNNEL_CMD_TOPIC, 10)
        self.in_tunnel_pub = self.create_publisher(Bool, TUNNEL_DETECTED_TOPIC, 10)

        # Subscriber
        self.scan_sub = self.create_subscription(
            LaserScan, '/scan',
            self.scan_callback,
            QoSPresetProfiles.SENSOR_DATA.value
        )

        # State
        self.last_dist_error = 0.0
        self.last_heading_error = 0.0
        self.last_time = self.get_clock().now()
        self.last_cmd = Twist()
        self.last_in_tunnel = False

        # Hysteresis counters
        self._tunnel_on_count = 0
        self._tunnel_off_count = 0

        self._heartbeat_timer = self.create_timer(
            float(self._param_cache['heartbeat_sec']),
            self._heartbeat_publish
        )

        self.get_logger().info('Tunnel Wall Follower started (RANSAC enhanced)')

    # ── Parameter management ─────────────────────────────────────────────

    def _update_param_cache(self) -> None:
        """Cache frequently used parameters to avoid per-scan lookups."""
        self._param_cache = {
            'target_center_dist': float(self.get_parameter('target_center_dist').value),
            'forward_speed': float(self.get_parameter('forward_speed').value),
            'kp': float(self.get_parameter('kp').value),
            'kd': float(self.get_parameter('kd').value),
            'kp_heading': float(self.get_parameter('kp_heading').value),
            'kd_heading': float(self.get_parameter('kd_heading').value),
            'max_angular': float(self.get_parameter('max_angular').value),
            'left_angle_min': float(self.get_parameter('left_angle_min').value),
            'left_angle_max': float(self.get_parameter('left_angle_max').value),
            'right_angle_min': float(self.get_parameter('right_angle_min').value),
            'right_angle_max': float(self.get_parameter('right_angle_max').value),
            'lidar_angle_offset': float(self.get_parameter('lidar_angle_offset').value),
            'min_wall_points': int(self.get_parameter('min_wall_points').value),
            'max_wall_dist': float(self.get_parameter('max_wall_dist').value),
            'ransac_threshold': float(self.get_parameter('ransac_threshold').value),
            'ransac_iterations': int(self.get_parameter('ransac_iterations').value),
            'tunnel_hysteresis_frames': int(self.get_parameter('tunnel_hysteresis_frames').value),
            'heartbeat_sec': float(self.get_parameter('heartbeat_sec').value),
        }

    def _on_params(self, params) -> SetParametersResult:
        """Update cached parameters when set via CLI or services."""
        for p in params:
            if p.name in self._param_cache:
                self._param_cache[p.name] = p.value
        return SetParametersResult(successful=True)

    def _heartbeat_publish(self) -> None:
        """Republish last state on a fixed heartbeat."""
        self.in_tunnel_pub.publish(Bool(data=self.last_in_tunnel))
        self.cmd_vel_pub.publish(self.last_cmd)

    # ── RANSAC line fitting ──────────────────────────────────────────────

    @staticmethod
    def _ransac_line_fit(
        points_xy: np.ndarray,
        threshold: float,
        max_iter: int
    ) -> Optional[Tuple[float, float]]:
        """
        RANSAC 2D line fit — pure NumPy, no external dependencies.

        Fits a line (ax + by + c = 0, ||(a,b)||=1) to the given points.
        Reference: Fischler & Bolles, "Random Sample Consensus" (1981).

        Args:
            points_xy: Nx2 array of (x, y) in the robot's local frame.
            threshold: Max perpendicular distance (m) for an inlier.
            max_iter:  Number of RANSAC iterations.

        Returns:
            (perp_distance, wall_angle) or None.
            - perp_distance: distance from robot origin to the wall line.
            - wall_angle:    angle of wall relative to robot's forward axis.
                             0 = perfectly parallel to robot heading.
        """
        n = len(points_xy)
        if n < 2:
            return None

        best_inliers = 0
        best_params = None

        for _ in range(max_iter):
            i, j = np.random.choice(n, 2, replace=False)
            p1, p2 = points_xy[i], points_xy[j]

            dx = p2[0] - p1[0]
            dy = p2[1] - p1[1]
            length = math.sqrt(dx * dx + dy * dy)
            if length < 1e-6:
                continue

            # Normalised normal vector of the line
            a = -dy / length
            b = dx / length
            c = -(a * p1[0] + b * p1[1])

            # Vectorised inlier count
            dists = np.abs(a * points_xy[:, 0] + b * points_xy[:, 1] + c)
            count = int(np.sum(dists < threshold))

            if count > best_inliers:
                best_inliers = count
                best_params = (a, b, c)

        if best_params is None or best_inliers < 2:
            return None

        a, b, c = best_params

        # Perpendicular distance from origin to the wall
        perp_dist = abs(c)

        # Wall angle relative to forward (x) axis
        # Line direction vector is (b, -a), perpendicular to normal (a, b)
        wall_angle = math.atan2(-a, b)

        # Normalise to [-π/2, π/2] — tilt only, not direction
        if wall_angle > math.pi / 2:
            wall_angle -= math.pi
        elif wall_angle < -math.pi / 2:
            wall_angle += math.pi

        return perp_dist, wall_angle

    # ── Main scan processing ─────────────────────────────────────────────

    def scan_callback(self, msg: LaserScan) -> None:
        """Process each LiDAR scan: classify walls, RANSAC fit, PD control."""
        offset = self._param_cache['lidar_angle_offset']
        l_min = self._param_cache['left_angle_min']
        l_max = self._param_cache['left_angle_max']
        r_min = self._param_cache['right_angle_min']
        r_max = self._param_cache['right_angle_max']
        max_wall = self._param_cache['max_wall_dist']
        min_pts = int(self._param_cache['min_wall_points'])

        left_xy = []
        right_xy = []

        # ── 1. Convert polar → Cartesian, classify left / right ──────────
        for i, r in enumerate(msg.ranges):
            if not (msg.range_min <= r <= msg.range_max):
                continue
            if math.isnan(r) or math.isinf(r) or r > max_wall:
                continue

            angle = msg.angle_min + i * msg.angle_increment + offset
            # Wrap to [-π, π]
            angle = math.atan2(math.sin(angle), math.cos(angle))

            x = r * math.cos(angle)
            y = r * math.sin(angle)

            if l_min <= angle <= l_max:
                left_xy.append((x, y))
            elif r_min <= angle <= r_max:
                right_xy.append((x, y))

        has_left = len(left_xy) >= min_pts
        has_right = len(right_xy) >= min_pts
        walls_detected = has_left and has_right

        # ── 2. Hysteresis for tunnel detection ───────────────────────────
        hyst = int(self._param_cache['tunnel_hysteresis_frames'])

        if walls_detected:
            self._tunnel_on_count = min(self._tunnel_on_count + 1, hyst + 1)
            self._tunnel_off_count = 0
        else:
            self._tunnel_off_count = min(self._tunnel_off_count + 1, hyst + 1)
            self._tunnel_on_count = 0

        if not self.last_in_tunnel and self._tunnel_on_count >= hyst:
            self.last_in_tunnel = True
            self.get_logger().info(
                f'TUNNEL ENTERED (L={len(left_xy)} R={len(right_xy)} pts)')
        elif self.last_in_tunnel and self._tunnel_off_count >= hyst:
            self.last_in_tunnel = False
            self.get_logger().info('TUNNEL EXITED')

        self.in_tunnel_pub.publish(Bool(data=self.last_in_tunnel))

        # ── 3. RANSAC line fitting + PD control ──────────────────────────
        cmd = Twist()

        if self.last_in_tunnel and walls_detected:
            thresh = float(self._param_cache['ransac_threshold'])
            iters = int(self._param_cache['ransac_iterations'])

            left_arr = np.array(left_xy)
            right_arr = np.array(right_xy)

            left_fit = self._ransac_line_fit(left_arr, thresh, iters)
            right_fit = self._ransac_line_fit(right_arr, thresh, iters)

            if left_fit is not None and right_fit is not None:
                left_dist, left_angle = left_fit
                right_dist, right_angle = right_fit

                # Distance error: positive = closer to right wall → steer left
                # negative = closer to left wall → steer right
                target = float(self._param_cache['target_center_dist'])
                dist_error = (left_dist - right_dist) + target

                # Heading error: wall angle in robot frame
                # If robot rotated CW by θ, wall_angle ≈ -θ
                # We want angular_z > 0 (steer left) to correct
                # So heading_error = -wall_angle → correction = kp * heading_error
                avg_wall_angle = (left_angle + right_angle) / 2.0
                heading_error = -avg_wall_angle

                # Time delta
                now = self.get_clock().now()
                dt = (now - self.last_time).nanoseconds / 1e9
                if dt <= 0 or dt > 0.5:
                    dt = 0.1  # fallback

                # Derivatives
                d_dist = (dist_error - self.last_dist_error) / dt
                d_heading = (heading_error - self.last_heading_error) / dt

                # PD gains
                kp = float(self._param_cache['kp'])
                kd = float(self._param_cache['kd'])
                kp_h = float(self._param_cache['kp_heading'])
                kd_h = float(self._param_cache['kd_heading'])
                max_ang = float(self._param_cache['max_angular'])

                # Combined steering output
                angular_z = (kp * dist_error + kd * d_dist
                             + kp_h * heading_error + kd_h * d_heading)
                angular_z = max(-max_ang, min(max_ang, angular_z))

                cmd.linear.x = float(self._param_cache['forward_speed'])
                cmd.angular.z = angular_z

                self.last_dist_error = dist_error
                self.last_heading_error = heading_error
                self.last_time = now

                self.get_logger().debug(
                    f'L:{left_dist:.2f}m/{math.degrees(left_angle):.1f}° '
                    f'R:{right_dist:.2f}m/{math.degrees(right_angle):.1f}° '
                    f'dist_err:{dist_error:.3f} head_err:{heading_error:.3f} '
                    f'ang:{angular_z:.2f}')

            else:
                # RANSAC failed on one side — fall back to mean distances
                left_avg = float(np.mean(left_arr[:, 1])) if has_left else 0.0
                right_avg = float(np.mean(right_arr[:, 1])) if has_right else 0.0
                dist_error = (left_avg + right_avg)

                now = self.get_clock().now()
                dt = (now - self.last_time).nanoseconds / 1e9
                if dt <= 0 or dt > 0.5:
                    dt = 0.1
                d_dist = (dist_error - self.last_dist_error) / dt

                kp = float(self._param_cache['kp'])
                kd = float(self._param_cache['kd'])
                max_ang = float(self._param_cache['max_angular'])

                angular_z = kp * dist_error + kd * d_dist
                angular_z = max(-max_ang, min(max_ang, angular_z))

                cmd.linear.x = float(self._param_cache['forward_speed'])
                cmd.angular.z = angular_z

                self.last_dist_error = dist_error
                self.last_heading_error = 0.0
                self.last_time = now

                self.get_logger().debug(
                    f'RANSAC fallback — dist_err:{dist_error:.3f} ang:{angular_z:.2f}')
        else:
            # Not in tunnel — publish zero, reset errors
            self.last_dist_error = 0.0
            self.last_heading_error = 0.0

        self.cmd_vel_pub.publish(cmd)
        self.last_cmd = cmd


def main(args=None) -> None:
    rclpy.init(args=args)
    node = TunnelWallFollower()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
