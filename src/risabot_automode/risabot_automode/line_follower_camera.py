#!/usr/bin/env python3
"""
Line Follower Camera Node — Cytron-Inspired Multi-Scanline Algorithm
Uses multiple horizontal scanlines across a cropped road-surface ROI to detect
white lane boundary lines or dark lane surfaces (inverted mode).

MDPI Architecture Enhancements:
- IPM (Inverse Perspective Mapping): optional Bird's Eye View transformation
  to eliminate perspective distortion before scanline processing.
- Kalman Filter: 1D Constant Velocity Kalman Filter to smooth raw error,
  predict during frame drops, and handle camera jitter cleanly.
"""

import time
from typing import Dict, List, Optional, Tuple

import cv2
from cv_bridge import CvBridge
import numpy as np
import rclpy
from rcl_interfaces.msg import SetParametersResult
from rclpy.node import Node
from rclpy.qos import QoSPresetProfiles
from sensor_msgs.msg import Image
from std_msgs.msg import Bool, Float32

from .topics import (
    CAMERA_DEBUG_LINE_TOPIC,
    CAMERA_IMAGE_TOPIC,
    LANE_ERROR_TOPIC,
    LANE_LOST_TOPIC,
    LANE_WIDTH_INVALID_TOPIC,
)


# ──────────────────────────────────────────────────────────────────────────────
# 1D Kalman Filter for Lane Center Tracking (MDPI-inspired)
# ──────────────────────────────────────────────────────────────────────────────

class LaneKalmanFilter:
    """State: x = [position, velocity]^T
    Tracks lane error and its rate of change to smooth steering and coast
    during brief frame drops.
    """

    def __init__(self, process_noise: float = 0.01, measurement_noise: float = 0.1):
        # State vector: [position (lane_error), velocity (d_error/dt)]
        self.x = np.array([0.0, 0.0], dtype=np.float64)

        # Covariance matrix P
        self.P = np.eye(2, dtype=np.float64) * 1.0

        # Process noise multiplier (Q matrix built dynamically using dt)
        self.Q_base = process_noise

        # Measurement noise covariance R (scalar since measurement is position only)
        self.R = measurement_noise

        # Measurement matrix H: we only observe position, not velocity
        self.H = np.array([[1.0, 0.0]], dtype=np.float64)

    def predict(self, dt: float) -> None:
        """State transition update: x_k = F * x_{k-1}"""
        dt = max(0.001, min(0.5, dt))  # sanity clamp

        # F matrix: pos_new = pos + vel * dt
        F = np.array([[1.0, dt],
                      [0.0, 1.0]], dtype=np.float64)

        # Q matrix: piecewise white noise model
        q = self.Q_base
        Q = np.array([
            [0.25 * (dt ** 4) * q, 0.5 * (dt ** 3) * q],
            [0.5 * (dt ** 3) * q,  (dt ** 2) * q]
        ], dtype=np.float64)

        self.x = F @ self.x
        self.P = F @ self.P @ F.T + Q

        # Clamp position state to valid range [-1.0, 1.0]
        self.x[0] = np.clip(self.x[0], -1.0, 1.0)

    def update(self, z: float) -> None:
        """Measurement update with raw_error observation z."""
        z_arr = np.array([z], dtype=np.float64)

        # Innovation (residual)
        y = z_arr - self.H @ self.x

        # Innovation covariance
        S = self.H @ self.P @ self.H.T + self.R

        # Kalman gain
        K = self.P @ self.H.T / S[0, 0]

        # Update state and covariance
        self.x = self.x + K.flatten() * y[0]
        I = np.eye(2, dtype=np.float64)
        self.P = (I - K @ self.H) @ self.P

        # Clamp position state
        self.x[0] = np.clip(self.x[0], -1.0, 1.0)

    def decay_velocity(self, factor: float = 0.9) -> None:
        """Dampen velocity during frame holds so prediction settles."""
        self.x[1] *= factor

    @property
    def position(self) -> float:
        return float(self.x[0])

    @property
    def velocity(self) -> float:
        return float(self.x[1])


# ──────────────────────────────────────────────────────────────────────────────
# Main Node
# ──────────────────────────────────────────────────────────────────────────────

class LineFollowerCamera(Node):
    """Lane detection and steering error estimation from camera frames."""

    def __init__(self):
        super().__init__('line_follower_camera')
        self.lane_error = 0.0
        self.filtered_error = 0.0    # output (Kalman or EMA)
        self.last_valid_error = 0.0  # last error from a confident scan

        # ── Tunable parameters ─────────────────────────────────────────────
        # Scanline detection
        self.declare_parameter('n_scanlines', 8)
        self.declare_parameter('min_valid_scanlines', 2)
        self.declare_parameter('min_line_width_px', 5)
        self.declare_parameter('crop_ratio_base', 0.55)
        self.declare_parameter('search_radius_px', 50)   # blob-to-expected match radius
        # A scanline whose detected center sits further than this from the
        # frame's own median center is very likely looking at something
        # off-track (wall, floor past the lane edge) rather than the real
        # lane — this happens most often on upper/far scanlines during a
        # sharp turn, when the camera heading points off the actual track.
        # Such a scanline is excluded from the weighted average entirely
        # rather than being allowed to dilute it.
        self.declare_parameter('scanline_outlier_px', 70)
        # Thresholding
        self.declare_parameter('white_threshold', 100)   # gray threshold (inverted: pixels BELOW this = lane)
        self.declare_parameter('use_otsu', False)         # True = Otsu auto-threshold
        # Adaptive local thresholding: since your lane is always black-with-white-borders
        # and only room brightness changes, a single global threshold has to be re-tuned
        # per room. Adaptive thresholding computes a local threshold per pixel neighborhood,
        # so it self-adjusts to brightness gradients/shadows within a single frame too.
        # Takes priority over use_otsu/white_threshold when enabled.
        self.declare_parameter('use_adaptive_threshold', False)
        self.declare_parameter('adaptive_block_size', 51)  # must be odd; bigger = smoother/slower to react
        self.declare_parameter('adaptive_c', 15)            # constant subtracted from local mean; higher = stricter
        self.declare_parameter('use_color_sampler', True)     # True = dynamic road color memory sampler
        self.declare_parameter('road_patch_size', 20)        # patch size at bottom-center of crop
        self.declare_parameter('road_color_tolerance', 40)   # allowed intensity offset +/- Delta
        self.declare_parameter('color_memory_alpha', 0.10)   # EMA smoothing alpha for road intensity
        self.declare_parameter('max_road_intensity_threshold', 110) # max intensity allowed for road sampler
        self.declare_parameter('invert_binary', True)     # True = detect dark lane, False = detect white borders
        # Morphological cleanup
        self.declare_parameter('morph_open_size', 3)     # erosion→dilation kernel to remove noise (0=disable)
        self.declare_parameter('morph_close_size', 5)    # dilation→erosion kernel to fill gaps (0=disable)
        # CLAHE adaptive lighting
        self.declare_parameter('clahe_enabled', True)
        self.declare_parameter('clahe_clip_limit', 2.0)
        # IPM (Bird's Eye View) — MDPI-inspired
        # DISABLED by default: requires careful calibration for the specific camera
        # mount angle. Wrong IPM distorts lane lines and hurts detection.
        self.declare_parameter('ipm_enabled', False)
        self.declare_parameter('ipm_top_width_ratio', 0.35)   # narrow top of trapezoid
        self.declare_parameter('ipm_bottom_width_ratio', 1.0)  # wide bottom
        # Kalman filter — MDPI-inspired (replaces EMA when enabled)
        self.declare_parameter('kalman_enabled', True)
        self.declare_parameter('kalman_process_noise', 0.01)
        self.declare_parameter('kalman_measurement_noise', 0.1)
        # Legacy EMA smoothing (used when kalman_enabled=false)
        self.declare_parameter('smoothing_alpha', 0.3)
        self.declare_parameter('dead_zone', 0.05)
        # Steering persistence on lane loss
        self.declare_parameter('hold_error_frames', 15)
        self.declare_parameter('error_decay_rate', 0.92)
        # Nominal Lane Width bounds (for detecting invalid/shadow/floor lane width)
        self.declare_parameter('nominal_lane_width_min', 35)
        self.declare_parameter('nominal_lane_width_max', 0)
        # Display / debug
        self.declare_parameter('show_debug', False)
        self.declare_parameter('resize_width', 320)
        self.declare_parameter('print_debug', False)
        self.declare_parameter('debug_print_rate', 0.5)
        # ── Upper-scanline cap ──────────────────────────────────────────────
        # Restricts how far up (far-field) scanlines reach inside the crop.
        # 0.60 = only the bottom 60% of the crop is sampled, keeping all
        # scanlines close enough to the robot that perspective distortion and
        # off-track features (walls, roundabout hub, floor) are avoided.
        # Lower values = safer but shorter look-ahead. Range: 0.40–1.0.
        self.declare_parameter('max_scanline_frac', 0.60)
        # Hard minimum pixel width for any accepted lane blob.
        # Rejects tiny spurious blobs (tile cracks, shadow edges) that cause
        # the reported lane width to collapse to abnormal values (e.g. 18cm).
        self.declare_parameter('min_lane_width_px', 30)

        self._param_cache: Dict[str, object] = {}
        self._update_param_cache()
        self.add_on_set_parameters_callback(self._on_params)
        self._last_debug_print = 0.0

        # ── Internal state ──────────────────────────────────────────────────
        self.frames_lost = 0
        self.current_hold_frames = 0
        self.invalid_width_consecutive = 0
        self.last_lane_widths: Dict[int, int] = {}
        self._expected_left: Optional[int] = None
        self._expected_right: Optional[int] = None
        self.road_intensity_memory: Optional[float] = None
        self._last_frame_time = time.monotonic()

        # CLAHE object (reused across frames)
        self._clahe = cv2.createCLAHE(
            clipLimit=self._param_cache['clahe_clip_limit'],
            tileGridSize=(8, 8)
        )

        # IPM warp matrix (computed lazily on first frame)
        self._ipm_matrix = None
        self._ipm_inv_matrix = None
        self._ipm_cached_size = (0, 0)

        # Kalman filter for lane center tracking
        self._kalman = LaneKalmanFilter(
            process_noise=self._param_cache['kalman_process_noise'],
            measurement_noise=self._param_cache['kalman_measurement_noise'],
        )

        # ── ROS publishers / subscribers ────────────────────────────────────
        self.error_pub = self.create_publisher(Float32, LANE_ERROR_TOPIC, 10)
        self.lane_lost_pub = self.create_publisher(Bool, LANE_LOST_TOPIC, 10)
        self.lane_width_invalid_pub = self.create_publisher(Bool, LANE_WIDTH_INVALID_TOPIC, 10)
        self.debug_pub = self.create_publisher(Image, CAMERA_DEBUG_LINE_TOPIC, 10)
        self.bridge = CvBridge()
        self.color_sub = self.create_subscription(
            Image,
            CAMERA_IMAGE_TOPIC,
            self.color_callback,
            QoSPresetProfiles.SENSOR_DATA.value
        )
        self.get_logger().info(
            'Line Follower Camera: Ready (MDPI-enhanced — IPM + Kalman + Cytron scanline)'
        )

    # ──────────────────────────────────────────────────────────────────────────
    # Parameter helpers
    # ──────────────────────────────────────────────────────────────────────────

    def _update_param_cache(self) -> None:
        """Cache frequently used parameters to avoid per-frame lookups."""
        self._param_cache = {
            'n_scanlines':             int(self.get_parameter('n_scanlines').value),
            'min_valid_scanlines':     int(self.get_parameter('min_valid_scanlines').value),
            'min_line_width_px':       int(self.get_parameter('min_line_width_px').value),
            'crop_ratio_base':         float(self.get_parameter('crop_ratio_base').value),
            'search_radius_px':        int(self.get_parameter('search_radius_px').value),
            'scanline_outlier_px':     int(self.get_parameter('scanline_outlier_px').value),
            'white_threshold':         int(self.get_parameter('white_threshold').value),
            'use_otsu':                bool(self.get_parameter('use_otsu').value),
            'use_adaptive_threshold':  bool(self.get_parameter('use_adaptive_threshold').value),
            'adaptive_block_size':     int(self.get_parameter('adaptive_block_size').value),
            'adaptive_c':              int(self.get_parameter('adaptive_c').value),
            'use_color_sampler':     bool(self.get_parameter('use_color_sampler').value),
            'road_patch_size':       int(self.get_parameter('road_patch_size').value),
            'road_color_tolerance':  int(self.get_parameter('road_color_tolerance').value),
            'color_memory_alpha':    float(self.get_parameter('color_memory_alpha').value),
            'max_road_intensity_threshold': int(self.get_parameter('max_road_intensity_threshold').value),
            'invert_binary':           bool(self.get_parameter('invert_binary').value),
            'morph_open_size':         int(self.get_parameter('morph_open_size').value),
            'morph_close_size':        int(self.get_parameter('morph_close_size').value),
            'clahe_enabled':           bool(self.get_parameter('clahe_enabled').value),
            'clahe_clip_limit':        float(self.get_parameter('clahe_clip_limit').value),
            'ipm_enabled':             bool(self.get_parameter('ipm_enabled').value),
            'ipm_top_width_ratio':     float(self.get_parameter('ipm_top_width_ratio').value),
            'ipm_bottom_width_ratio':  float(self.get_parameter('ipm_bottom_width_ratio').value),
            'kalman_enabled':          bool(self.get_parameter('kalman_enabled').value),
            'kalman_process_noise':    float(self.get_parameter('kalman_process_noise').value),
            'kalman_measurement_noise': float(self.get_parameter('kalman_measurement_noise').value),
            'smoothing_alpha':         float(self.get_parameter('smoothing_alpha').value),
            'dead_zone':               float(self.get_parameter('dead_zone').value),
            'hold_error_frames':       int(self.get_parameter('hold_error_frames').value),
            'error_decay_rate':        float(self.get_parameter('error_decay_rate').value),
            'nominal_lane_width_min':  int(self.get_parameter('nominal_lane_width_min').value),
            'nominal_lane_width_max':  int(self.get_parameter('nominal_lane_width_max').value),
            'show_debug':              bool(self.get_parameter('show_debug').value),
            'resize_width':            int(self.get_parameter('resize_width').value),
            'print_debug':             bool(self.get_parameter('print_debug').value),
            'debug_print_rate':        float(self.get_parameter('debug_print_rate').value),
            'max_scanline_frac':        float(self.get_parameter('max_scanline_frac').value),
            'min_lane_width_px':        int(self.get_parameter('min_lane_width_px').value),
        }

    def _on_params(self, params) -> SetParametersResult:
        """Update cached parameters when set via CLI or dashboard."""
        for p in params:
            if p.name in self._param_cache:
                self._param_cache[p.name] = p.value
                if p.name == 'clahe_clip_limit':
                    self._clahe = cv2.createCLAHE(
                        clipLimit=float(p.value), tileGridSize=(8, 8)
                    )
                # Invalidate IPM matrix if IPM params changed
                if p.name.startswith('ipm_'):
                    self._ipm_matrix = None
                # Update Kalman noise params
                if p.name == 'kalman_process_noise':
                    self._kalman.Q_base = float(p.value)
                if p.name == 'kalman_measurement_noise':
                    self._kalman.R = float(p.value)
        return SetParametersResult(successful=True)

    # ──────────────────────────────────────────────────────────────────────────
    # IPM — Inverse Perspective Mapping (Bird's Eye View)
    # ──────────────────────────────────────────────────────────────────────────

    def _compute_ipm_matrix(self, w: int, h: int) -> None:
        """Compute the perspective warp matrix for Bird's Eye View.

        The source trapezoid represents the perspective view of the road:
          - Bottom edge: close to robot, wide field of view
          - Top edge: further away, narrower due to perspective

        Camera specs: Orbbec Astra Mini at 8.5cm height, 0° tilt (horizontal).
        """
        top_ratio = self._param_cache['ipm_top_width_ratio']
        bot_ratio = self._param_cache['ipm_bottom_width_ratio']

        # Source trapezoid (perspective view of road)
        top_margin = int(w * (1.0 - top_ratio) / 2)
        bot_margin = int(w * (1.0 - bot_ratio) / 2)

        src = np.float32([
            [top_margin,     0],      # top-left
            [w - top_margin, 0],      # top-right
            [w - bot_margin, h - 1],  # bottom-right
            [bot_margin,     h - 1],  # bottom-left
        ])

        # Destination rectangle (bird's eye view — full image)
        dst = np.float32([
            [0,     0],
            [w - 1, 0],
            [w - 1, h - 1],
            [0,     h - 1],
        ])

        self._ipm_matrix = cv2.getPerspectiveTransform(src, dst)
        self._ipm_inv_matrix = cv2.getPerspectiveTransform(dst, src)
        self._ipm_cached_size = (w, h)

    def _apply_ipm(self, img: np.ndarray) -> np.ndarray:
        """Apply Bird's Eye View warp to road crop."""
        h, w = img.shape[:2]

        # Recompute matrix if image size changed or first time
        if self._ipm_matrix is None or self._ipm_cached_size != (w, h):
            self._compute_ipm_matrix(w, h)

        return cv2.warpPerspective(img, self._ipm_matrix, (w, h),
                                   flags=cv2.INTER_LINEAR)

    # ──────────────────────────────────────────────────────────────────────────
    # Scanline detection — Cytron-style pixel scanning
    # ──────────────────────────────────────────────────────────────────────────

    def _find_all_white_regions(self, row: np.ndarray, min_w: int, max_w: int) -> List[Tuple[int, int, int]]:
        """Find all white regions within a width range.
        Returns list of (center, start, end) tuples.
        """
        regions = []
        in_white = False
        white_start = 0
        for x in range(len(row)):
            if row[x] == 255:
                if not in_white:
                    white_start = x
                    in_white = True
            else:
                if in_white:
                    width = x - white_start
                    if min_w <= width <= max_w:
                        regions.append(((white_start + x) // 2, white_start, x))
                    in_white = False
        if in_white:
            width = len(row) - white_start
            if min_w <= width <= max_w:
                regions.append(((white_start + len(row)) // 2, white_start, len(row)))
        return regions

    def _detect_scanlines(
        self, binary: np.ndarray, crop_h: int, w: int
    ) -> Tuple[List[Tuple[int, int]], List[Tuple[int, int]], List[Tuple[int, int]], List[float], int]:
        """Run robust multi-scanline blob matching."""
        n_scanlines = self._param_cache['n_scanlines']
        min_width = self._param_cache['min_line_width_px']
        invert = self._param_cache.get('invert_binary', False)
        # In invert mode the lane is wider than border lines
        max_width = w - 10 if invert else w // 3
        search_radius = self._param_cache['search_radius_px']

        left_points = []
        right_points = []
        center_points = []
        scanline_weights = []  # weight per valid scanline (bottom = higher)
        valid_count = 0

        # Start from last known good position, or center if completely lost
        if self._expected_left is None or self._expected_right is None:
            expected_left = w // 4
            expected_right = 3 * w // 4
        else:
            expected_left = self._expected_left
            expected_right = self._expected_right

        # FIX-1: Cap scanlines to the bottom fraction of the crop.
        # Prevents upper/far-field scanlines from locking onto walls, the
        # roundabout hub ring, or the floor boundary during a curve.
        max_frac = self._param_cache.get('max_scanline_frac', 0.60)
        for i in range(n_scanlines):
            y_frac = (i + 0.5) / n_scanlines * max_frac
            y_in_crop = int(crop_h * (1.0 - y_frac))
            y_in_crop = max(0, min(crop_h - 1, y_in_crop))

            row = binary[y_in_crop, :]
            raw_regions = self._find_all_white_regions(row, min_width, max_width)

            left_x = None
            right_x = None

            if invert and len(raw_regions) > 0:
                # INVERT MODE: the white region IS the lane.
                # Pick the region whose center is closest to expected lane center.
                expected_center = (expected_left + expected_right) // 2
                best = min(raw_regions, key=lambda r: abs(r[0] - expected_center))
                # Only accept if within search radius of expected center
                if abs(best[0] - expected_center) < search_radius:
                    cand_width = best[2] - best[1]
                    expected_width = self.last_lane_widths.get(i, None)
                    # Reject blobs whose width is wildly different from the last
                    # confirmed width at this scanline (e.g. a wall panel edge or
                    # doorway briefly in frame is much wider/narrower than the lane).
                    # Skipped on the very first lock or if the previous locked width
                    # was too small (e.g. < 40px) to allow escaping a collapsed trap.
                    # FIX-2a: Tighter width consistency gate.
                    # Previous tolerance (0.5–1.8) allowed width to halve or nearly
                    # double in a single frame, letting narrow spurious blobs pass.
                    # New tolerance (0.65–1.50) still handles real curves but rejects
                    # sudden collapses (e.g. 60 cm → 18 cm in one frame).
                    width_ok = (
                        expected_width is None
                        or expected_width <= 40
                        or 0.65 <= (cand_width / expected_width) <= 1.50
                    )
                    # FIX-2b: Hard minimum pixel width gate.
                    # No matter what the history says, never accept a blob that is
                    # physically narrower than min_lane_width_px pixels.
                    min_w_px = self._param_cache.get('min_lane_width_px', 30)
                    if width_ok and cand_width < min_w_px:
                        width_ok = False
                    if width_ok:
                        left_x = best[1]   # left edge of lane
                        right_x = best[2]  # right edge of lane

            elif len(raw_regions) > 0:
                # BORDER MODE (original): find left/right white border lines
                regions = [r[0] for r in raw_regions]  # extract centers only
                if i == 0 and (self._expected_left is None or self._expected_right is None):
                    if len(regions) >= 2:
                        target_w = self.last_lane_widths.get(0, w // 2)
                        best_pair = None
                        best_err = 9999
                        for a in range(len(regions)):
                            for b in range(a + 1, len(regions)):
                                err = abs((regions[b] - regions[a]) - target_w)
                                if err < best_err:
                                    best_err = err
                                    best_pair = (regions[a], regions[b])
                        if best_pair:
                            left_x, right_x = best_pair
                    elif len(regions) == 1:
                        if regions[0] < w // 2: left_x = regions[0]
                        else: right_x = regions[0]
                else:
                    # Pair-based selection: score every plausible (left, right)
                    # combination together, instead of picking left and right
                    # independently. Independent nearest-neighbor picking is
                    # what causes a lock onto a roundabout's inner hub ring —
                    # the hub's two edges can each individually be "closest"
                    # to expected_left/expected_right even though they don't
                    # belong to the same lane at all.
                    target_w = self.last_lane_widths.get(i, expected_right - expected_left)
                    width_tol = max(20, int(target_w * 0.4))  # allow for curves

                    best_pair = None
                    best_score = None
                    for a in range(len(regions)):
                        for b in range(a + 1, len(regions)):
                            cand_left, cand_right = regions[a], regions[b]
                            cand_width = cand_right - cand_left
                            if abs(cand_width - target_w) > width_tol:
                                continue  # doesn't look like the real lane width
                            score = (abs(cand_left - expected_left) +
                                     abs(cand_right - expected_right))
                            if score > 2 * search_radius:
                                continue  # too far from where we expect the lane
                            if best_score is None or score < best_score:
                                best_score = score
                                best_pair = (cand_left, cand_right)

                    if best_pair is not None:
                        left_x, right_x = best_pair
                    else:
                        # No width-consistent pair found — fall back to
                        # single-side tracking rather than guessing a pair
                        # that might span the wrong feature (e.g. the hub).
                        best_left = min(regions, key=lambda x: abs(x - expected_left))
                        if abs(best_left - expected_left) < search_radius:
                            left_x = best_left
                        best_right = min(regions, key=lambda x: abs(x - expected_right))
                        if abs(best_right - expected_right) < search_radius:
                            right_x = best_right
                        if left_x == right_x and left_x is not None:
                            if abs(left_x - expected_left) < abs(right_x - expected_right):
                                right_x = None
                            else:
                                left_x = None

            # Determine lane center
            if left_x is not None and right_x is not None:
                valid_count += 1
                self.last_lane_widths[i] = right_x - left_x
                center_x = (left_x + right_x) // 2
                expected_left = left_x
                expected_right = right_x

            elif left_x is not None:
                valid_count += 1
                width = self.last_lane_widths.get(i, w // 2)
                right_x = left_x + width
                center_x = (left_x + right_x) // 2
                expected_left = left_x
                expected_right = right_x

            elif right_x is not None:
                valid_count += 1
                width = self.last_lane_widths.get(i, w // 2)
                left_x = right_x - width
                center_x = (left_x + right_x) // 2
                expected_left = left_x
                expected_right = right_x

            else:
                continue

            # Save the bottom-most valid row as the expectation for the NEXT frame
            # Use aggressive EMA smoothing to prevent frame-to-frame jumps
            if valid_count == 1:
                smooth = 0.50  # Responsive tracking (was 0.15, which caused lag on curves)
                if self._expected_left is not None:
                    # Clamp jump: allow expected to shift up to 40px/frame for sharp turns
                    max_shift = 40
                    new_left = int(smooth * expected_left + (1 - smooth) * self._expected_left)
                    new_right = int(smooth * expected_right + (1 - smooth) * self._expected_right)
                    new_left = max(self._expected_left - max_shift, min(self._expected_left + max_shift, new_left))
                    new_right = max(self._expected_right - max_shift, min(self._expected_right + max_shift, new_right))
                    self._expected_left = new_left
                    self._expected_right = new_right
                else:
                    self._expected_left = expected_left
                    self._expected_right = expected_right

            left_points.append((int(left_x), y_in_crop))
            right_points.append((int(right_x), y_in_crop))
            center_points.append((int(center_x), y_in_crop))
            # FIX-3: Steeper weight falloff for upper scanlines.
            # Exponent raised from 0.5 → 2.0 (quadratic dropoff).
            # Bottom scanline weight: (0.95)^2 + 0.05 ≈ 0.95  (essentially unchanged)
            # Top  scanline weight:   (0.05)^2 + 0.05 ≈ 0.053 (was 0.37 — 7× reduction)
            # This makes a single far-field wall lock far less able to corrupt
            # the weighted average even without the outlier filter firing.
            scanline_weights.append((1.0 - y_frac) ** 2.0 + 0.05)

        # If completely lost, clear expectations so it resets next frame
        if valid_count == 0:
            self._expected_left = None
            self._expected_right = None
            self.last_lane_widths.clear()

        return left_points, right_points, center_points, scanline_weights, valid_count

    # ──────────────────────────────────────────────────────────────────────────
    # Main camera callback
    # ──────────────────────────────────────────────────────────────────────────

    def color_callback(self, msg: Image) -> None:
        """Process a camera frame and publish lane error."""
        try:
            now = time.monotonic()
            dt = now - self._last_frame_time
            self._last_frame_time = now
            if dt <= 0.0 or dt > 0.5:
                dt = 0.033  # assume ~30 fps

            # ── 1. Resize — ALWAYS force to exactly 320x240 ──────────────
            bgr = self.bridge.imgmsg_to_cv2(msg, 'bgr8')
            bgr = cv2.resize(bgr, (320, 240))
            h, w = 240, 320

            image_center = w / 2.0

            # ── 2. Crop bottom portion (road surface) ───────────────────────
            crop_ratio = self._param_cache['crop_ratio_base']
            crop_h = int(h * crop_ratio)
            road = bgr[h - crop_h:, :]

            # ── 3. IPM warp: perspective → Bird's Eye View ──────────────────
            if self._param_cache['ipm_enabled']:
                road = self._apply_ipm(road)

            # ── 4. CLAHE + threshold (fixed or Otsu) + morphology ───────────
            gray = cv2.cvtColor(road, cv2.COLOR_BGR2GRAY)

            if self._param_cache['clahe_enabled']:
                gray = self._clahe.apply(gray)

            blurred = cv2.GaussianBlur(gray, (5, 5), 0)
            invert = self._param_cache.get('invert_binary', False)

            if self._param_cache.get('use_color_sampler', True):
                # ── Dynamic Road Color Memory Sampler ───────────────────
                # Sample a patch directly in front of the robot's front bumper
                patch_sz = max(10, min(50, int(self._param_cache['road_patch_size'])))
                patch_y1 = max(0, crop_h - patch_sz)
                patch_x1 = max(0, (w // 2) - (patch_sz // 2))
                patch_x2 = min(w, (w // 2) + (patch_sz // 2))
                road_patch = gray[patch_y1:crop_h, patch_x1:patch_x2]

                max_road_thresh = float(self._param_cache.get('max_road_intensity_threshold', 110.0))
                if road_patch.size > 0:
                    sampled_i = float(np.median(road_patch))
                    # Dark-anchored gating: ONLY update road color memory if the sampled patch
                    # is actually dark (<= 110). If the robot drives over white tape/lines (> 110),
                    # IGNORE the sample and retain the previous dark road memory!
                    if sampled_i <= max_road_thresh:
                        if self.road_intensity_memory is None:
                            self.road_intensity_memory = sampled_i
                        else:
                            alpha = float(self._param_cache['color_memory_alpha'])
                            self.road_intensity_memory = alpha * sampled_i + (1.0 - alpha) * self.road_intensity_memory
                        # Hard upper ceiling to guarantee memory never drifts into light intensities
                        self.road_intensity_memory = min(100.0, self.road_intensity_memory)

                target_i = self.road_intensity_memory if self.road_intensity_memory is not None else 70.0
                tol = int(self._param_cache['road_color_tolerance'])
                lower_b = max(0, int(target_i - tol))
                # Upper bound capped at 115 so binarization range never encompasses white borders (>= 120)
                upper_b = min(115, int(target_i + tol))

                # Pixels matching remembered road color → 255 (white road region)
                binary = cv2.inRange(gray, lower_b, upper_b)

            elif self._param_cache['use_adaptive_threshold']:
                block_size = int(self._param_cache['adaptive_block_size'])
                if block_size % 2 == 0:
                    block_size += 1  # cv2 requires odd block size
                block_size = max(3, block_size)
                adaptive_c = int(self._param_cache['adaptive_c'])
                # invert=True (dark lane on light border) needs the INV variant so the
                # darker-than-local-neighborhood pixels become the white "lane" blob.
                thresh_type = cv2.THRESH_BINARY_INV if invert else cv2.THRESH_BINARY
                binary = cv2.adaptiveThreshold(
                    blurred, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                    thresh_type, block_size, adaptive_c
                )
            elif self._param_cache['use_otsu']:
                _, binary = cv2.threshold(
                    blurred, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU
                )
            else:
                thresh_val = self._param_cache['white_threshold']
                if invert:
                    # INVERT: pixels BELOW threshold (dark lane) → white
                    _, binary = cv2.threshold(
                        blurred, thresh_val, 255, cv2.THRESH_BINARY_INV
                    )
                else:
                    # NORMAL: pixels ABOVE threshold (white borders) → white
                    _, binary = cv2.threshold(
                        blurred, thresh_val, 255, cv2.THRESH_BINARY
                    )

            # Morphological cleanup: remove noise then fill small gaps
            open_sz = self._param_cache['morph_open_size']
            close_sz = self._param_cache['morph_close_size']
            if open_sz > 0:
                kernel_open = cv2.getStructuringElement(
                    cv2.MORPH_RECT, (open_sz, open_sz)
                )
                binary = cv2.morphologyEx(binary, cv2.MORPH_OPEN, kernel_open)
            if close_sz > 0:
                kernel_close = cv2.getStructuringElement(
                    cv2.MORPH_RECT, (close_sz, close_sz)
                )
                binary = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, kernel_close)

            # ── 5. Multi-scanline detection ─────────────────────────────────
            left_pts, right_pts, center_pts, scan_weights, valid_count = \
                self._detect_scanlines(binary, crop_h, w)

            # ── 6. Compute raw error ────────────────────────────────────────
            conf_min = self._param_cache['min_valid_scanlines']
            measurement_available = False

            if valid_count >= conf_min and len(center_pts) > 0:
                # Outlier rejection anchored to _expected_center (last-known
                # lane position) rather than the frame's global median.
                #
                # WHY: global median is easily corrupted when the robot
                # overshoots during a sharp turn and 5 of 10 scanlines pick up
                # the outer wall. The median then lands between wall and lane,
                # causing BOTH to exceed outlier_thresh — triggering the fallback
                # unfiltered average, which then lets heavy bottom-weighted wall
                # scanlines dominate and output the WRONG steering direction.
                #
                # With _expected_center as the anchor:
                #   wall at x=80, lane expected at x=240:
                #     |80 - 240| = 160 > thresh -> wall ZEROED
                #     |240 - 240| = 0 <= thresh -> lane KEPT
                # So even a 5-wall / 5-lane split is handled correctly.
                outlier_thresh = self._param_cache['scanline_outlier_px']
                if self._expected_left is not None and self._expected_right is not None:
                    anchor_x = float(self._expected_left + self._expected_right) / 2.0
                else:
                    # Cold-start: no history yet, fall back to frame median
                    anchor_x = float(np.median([pt[0] for pt in center_pts]))
                filtered_weights = [
                    wt if abs(pt[0] - anchor_x) <= outlier_thresh else 0.0
                    for pt, wt in zip(center_pts, scan_weights)
                ]
                total_weight = sum(filtered_weights)
                if total_weight > 0:
                    avg_center_x = sum(
                        pt[0] * wt for pt, wt in zip(center_pts, filtered_weights)
                    ) / total_weight
                else:
                    # Every scanline was an outlier vs expected_center — this
                    # can happen on a full lane loss or a very wide swing.
                    # Fall back to the frame median approach so we don't feed
                    # an empty measurement.
                    fallback_median = float(np.median([pt[0] for pt in center_pts]))
                    fallback_weights = [
                        wt if abs(pt[0] - fallback_median) <= outlier_thresh else 0.0
                        for pt, wt in zip(center_pts, scan_weights)
                    ]
                    total_weight = sum(fallback_weights)
                    if total_weight > 0:
                        avg_center_x = sum(
                            pt[0] * wt for pt, wt in zip(center_pts, fallback_weights)
                        ) / total_weight
                    else:
                        avg_center_x = sum(pt[0] for pt in center_pts) / len(center_pts)
                raw_error = float(
                    np.clip((avg_center_x - image_center) / image_center, -1.0, 1.0)
                )
                measurement_available = True
                self.frames_lost = 0
                self.current_hold_frames = self._param_cache['hold_error_frames']
                self.lane_lost_pub.publish(Bool(data=False))
            else:
                self.frames_lost += 1
                if self.frames_lost >= self._param_cache['hold_error_frames']:
                    self.lane_lost_pub.publish(Bool(data=True))
                    self._expected_left = None
                    self._expected_right = None
                raw_error = 0.0

            # ── 7. Filtering: Kalman or EMA ─────────────────────────────────
            if self._param_cache['kalman_enabled']:
                # Kalman predict step (always runs)
                self._kalman.predict(dt)

                # FIX-4: Soft per-frame velocity cap.
                # Without this, a brief wrong-direction detection builds up
                # |v| > 0.5 which then fights valid measurements for several
                # frames, producing prolonged oscillation. Decaying at 0.92/frame
                # when |v| > 0.30 limits the maximum Kalman coast speed without
                # affecting normal slow-turning behaviour (|v| < 0.30).
                if abs(self._kalman.velocity) > 0.30:
                    self._kalman.decay_velocity(0.92)

                if measurement_available:
                    # Velocity direction guard: if the Kalman filter has
                    # accumulated a velocity in the OPPOSITE direction to the
                    # new valid measurement, kill that velocity before the
                    # update. Without this, stale coast (e.g. v=-0.76 from a
                    # left-drift phase) fights new correct right-side detections
                    # for several frames, producing the wrong steering output
                    # even when scanlines are clearly showing the lane.
                    vel = self._kalman.velocity
                    if abs(vel) > 0.05 and (vel * raw_error) < 0:
                        self._kalman.x[1] = 0.0

                    # Deadband: only update if error exceeds threshold.
                    # When within dead zone, SKIP the update entirely so the
                    # Kalman filter coasts on its prediction. Feeding 0.0 is
                    # a false measurement that biases the filter toward center.
                    if abs(raw_error) >= self._param_cache['dead_zone']:
                        self._kalman.update(raw_error)
                    # else: let predict() carry the state forward (no update)
                    self.current_hold_frames = self._param_cache['hold_error_frames']
                else:
                    # Lane is lost this frame. Coasting on a stale velocity
                    # estimate indefinitely is what produced the false
                    # "CENTERED" reading with zero scanline locks — decay the
                    # velocity so the prediction settles rather than drifting
                    # on outdated motion, and count down hold frames so HOLD
                    # status is honest instead of being stuck at its last value.
                    self._kalman.decay_velocity(0.85)
                    if self.current_hold_frames > 0:
                        self.current_hold_frames -= 1
                    if self.frames_lost >= self._param_cache['hold_error_frames']:
                        # Fully lost beyond the hold window: fade the position
                        # estimate toward 0 too, so a long-lost lane doesn't
                        # keep reporting a confident (and likely stale/wrong)
                        # steering direction forever.
                        self._kalman.x[0] *= self._param_cache['error_decay_rate']

                self.filtered_error = self._kalman.position
                self.lane_error = self.filtered_error

                if measurement_available:
                    self.last_valid_error = self.lane_error

            else:
                # Legacy EMA path (backward compatible)
                if measurement_available:
                    if abs(raw_error) < self._param_cache['dead_zone']:
                        raw_error = 0.0
                    alpha = self._param_cache['smoothing_alpha']
                    self.filtered_error = alpha * raw_error + (1.0 - alpha) * self.filtered_error
                    self.last_valid_error = self.filtered_error

                elif self.current_hold_frames > 0:
                    self.last_valid_error *= self._param_cache['error_decay_rate']
                    self.filtered_error = self.last_valid_error
                    self.current_hold_frames -= 1

                else:
                    self.filtered_error *= 0.95  # gentle fade to zero

                self.lane_error = self.filtered_error

            # ── 8. Publish ──────────────────────────────────────────────────
            self.error_pub.publish(Float32(data=self.lane_error))

            # ── Check lane width validity against nominal bounds ─────────────
            avg_width = sum(self.last_lane_widths.values()) / len(self.last_lane_widths) if len(self.last_lane_widths) > 0 else 0
            w_min = int(self._param_cache['nominal_lane_width_min'])
            w_max = int(self._param_cache['nominal_lane_width_max'])
            saw_invalid_width = False
            if valid_count > 0 and len(self.last_lane_widths) > 0:
                if w_min > 0 and avg_width < w_min:
                    saw_invalid_width = True
                elif w_max > 0 and avg_width > w_max:
                    saw_invalid_width = True

            if saw_invalid_width:
                self.invalid_width_consecutive = min(10, self.invalid_width_consecutive + 1)
            else:
                self.invalid_width_consecutive = max(0, self.invalid_width_consecutive - 1)

            lane_width_invalid = (self.invalid_width_consecutive >= 5)
            self.lane_width_invalid_pub.publish(Bool(data=lane_width_invalid))

            # ── 9. Debug visualisation ──────────────────────────────────────
            if self._param_cache['show_debug']:
                # Show the warped (IPM) view if enabled, otherwise raw
                debug = road.copy()
                crop_top = 0  # debug view is already cropped

                # Draw scanline detection points
                for lp, rp, cp in zip(left_pts, right_pts, center_pts):
                    ly = lp[1]
                    ry = rp[1]
                    cy = cp[1]

                    # Left line point (blue)
                    cv2.circle(debug, (lp[0], ly), 4, (255, 130, 130), -1)
                    # Right line point (pink)
                    cv2.circle(debug, (rp[0], ry), 4, (130, 130, 255), -1)
                    # Center point (green)
                    cv2.circle(debug, (cp[0], cy), 5, (0, 255, 0), -1)
                    # Scanline visualization
                    cv2.line(debug, (lp[0], ly), (rp[0], ry), (50, 50, 50), 1)

                # Draw center reference line
                cv2.line(debug, (w // 2, 0), (w // 2, crop_h), (0, 0, 255), 1)

                # Status text
                def put_text(img, text, pos, scale, color, thick=2):
                    cv2.putText(img, text, pos, cv2.FONT_HERSHEY_SIMPLEX, scale, (0, 0, 0), thick + 2)
                    cv2.putText(img, text, pos, cv2.FONT_HERSHEY_SIMPLEX, scale, color, thick)

                if abs(self.lane_error) < 0.05:
                    direction, t_color = 'CENTERED', (0, 255, 0)
                elif self.lane_error > 0:
                    # Positive error -> positive angular_z -> robot physically steers RIGHT
                    direction, t_color = 'STEER RIGHT', (0, 165, 255)
                else:
                    # Negative error -> negative angular_z -> robot physically steers LEFT
                    direction, t_color = 'STEER LEFT', (0, 165, 255)

                steer_deg = abs(self.lane_error) * 50.0
                put_text(debug, f'{direction} ({steer_deg:.0f} deg)', (10, 20), 0.55, t_color)

                status_str = (
                    f'LOCK({valid_count}/{self._param_cache["n_scanlines"]})'
                    if valid_count >= conf_min
                    else (f'HOLD({self._param_cache["hold_error_frames"] - self.frames_lost}f)'
                          if self.frames_lost < self._param_cache['hold_error_frames']
                          else f'LOST({self.frames_lost}f)')
                )
                ipm_str = 'IPM' if self._param_cache['ipm_enabled'] else 'RAW'
                kf_str = 'KF' if self._param_cache['kalman_enabled'] else 'EMA'
                r_int_str = f'R_INT={int(self.road_intensity_memory)}' if self.road_intensity_memory is not None else ''
                put_text(debug, f'{status_str} [{ipm_str}|{kf_str}] {r_int_str}', (10, 42), 0.45, (0, 255, 255))

                if len(self.last_lane_widths) > 0:
                    avg_w = sum(self.last_lane_widths.values()) / len(self.last_lane_widths)
                    lane_w_cm = avg_w * 40.0 / (w * 0.4)
                    put_text(debug, f'W={lane_w_cm:.0f}cm', (10, 60), 0.45, (0, 255, 255))

                # Kalman velocity indicator
                if self._param_cache['kalman_enabled']:
                    vel = self._kalman.velocity
                    put_text(debug, f'v={vel:.3f}', (10, 78), 0.4, (200, 200, 0))

                # Compose into full-frame debug image for dashboard
                debug_full = bgr.copy()
                debug_full[h - crop_h:, :] = debug
                # Draw crop boundary (fixed position)
                cv2.line(debug_full, (0, h - crop_h), (w, h - crop_h), (255, 0, 255), 1)

                self.debug_pub.publish(self.bridge.cv2_to_imgmsg(debug_full, encoding='bgr8'))

            if self._param_cache['print_debug']:
                now_mono = time.monotonic()
                if now_mono - self._last_debug_print >= self._param_cache['debug_print_rate']:
                    status = ('CENTER' if abs(self.lane_error) < 0.05
                              else ('TURN RIGHT' if self.lane_error < 0 else 'TURN LEFT'))
                    kf_str = f'kv={self._kalman.velocity:.3f}' if self._param_cache['kalman_enabled'] else ''
                    print(
                        f'\r[LF] Err:{self.lane_error:.2f} | {status} | '
                        f'valid={valid_count}/{self._param_cache["n_scanlines"]} | {kf_str}',
                        end=''
                    )
                    self._last_debug_print = now_mono

        except Exception as e:
            self.get_logger().error(f'Error processing image: {e}', throttle_duration_sec=1.0)


def main(args=None):
    rclpy.init(args=args)
    node = LineFollowerCamera()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
