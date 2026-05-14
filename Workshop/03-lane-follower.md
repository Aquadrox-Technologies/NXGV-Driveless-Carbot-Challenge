# Module 3: Lane Following

## Learning Objectives

By the end of this module, you will:
- Understand the complete data flow from camera to motor in an autonomous lane follower
- Know how the RISA-bot detects lane boundaries using image processing
- Be able to launch the lane follower using the built-in launch file
- Observe the system live through the dashboard debug view
- Know where to look in the code and config file to tune the robot's behaviour

---

## 1. The Big Picture: From Camera to Wheels

Before we touch any code, let us trace what actually happens when the robot drives itself. Every step in the list below is a **separate ROS 2 node** that talks to the others over topics — exactly the architecture you built in Module 1.

```text
┌──────────────────┐
│  Astra Camera    │  publishes frames on /camera/color/image_raw
└────────┬─────────┘
         │ sensor_msgs/Image  (~30 Hz)
         ▼
┌──────────────────────┐
│ line_follower_camera │  reads the image, finds the lane, publishes the error
└────────┬─────────────┘
         │ std_msgs/Float32 on /lane_error  (-1.0 = hard left, 0.0 = centred, +1.0 = hard right)
         ▼
┌──────────────────┐
│   auto_driver    │  runs a PID controller, converts lane_error → Twist command
└────────┬─────────┘
         │ geometry_msgs/Twist on /cmd_vel_auto_raw
         ▼
┌────────────────────────┐
│ cmd_safety_controller  │  enforces speed limits and timeouts
└────────┬───────────────┘
         │ geometry_msgs/Twist on /cmd_vel_auto
         ▼
┌──────────────────┐
│ servo_controller │  translates Twist → PWM signals sent to the motors
└──────────────────┘
```

**Key insight:** Each node has one job. If anything goes wrong (camera disconnects, lane is lost) each node handles its own piece gracefully, and the system keeps running safely.

---

## 2. How the Robot "Sees" the Lane

Open `src/risabot_automode/risabot_automode/line_follower_camera.py` and follow along.

### Step 1 — Resize and crop

```python
# Always resize to exactly 320 × 240 regardless of camera resolution
bgr = cv2.resize(bgr, (320, 240))
h, w = 240, 320

# Only look at the BOTTOM 55% of the image — that's the road surface
crop_ratio = 0.55
crop_h = int(h * crop_ratio)   # = 132 pixels
road = bgr[h - crop_h:, :]     # crop = bottom 132 rows
```

**Why crop?** The top half of the image shows the distant background — walls, ceiling, other robots. None of that helps navigate. Ignoring it makes processing faster and more reliable.

```text
┌──────────────────────┐ ─── row 0
│                      │
│   Ignored (walls,    │  Top 45%
│   ceiling, etc.)     │
│                      │
├──────────────────────┤ ─── row 108  ← crop boundary (purple line on dashboard)
│                      │
│   Road surface       │  Bottom 55%  ← where all processing happens
│                      │
└──────────────────────┘ ─── row 240
```

### Step 2 — Enhance contrast (CLAHE)

```python
gray = cv2.cvtColor(road, cv2.COLOR_BGR2GRAY)
clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
gray = clahe.apply(gray)
```

**CLAHE** (Contrast Limited Adaptive Histogram Equalization) locally boosts contrast. This compensates for uneven lighting — a bright spot near one wall and a shadow near the other would otherwise make the threshold step unreliable.

### Step 3 — Threshold to find the lane

```python
blurred = cv2.GaussianBlur(gray, (5, 5), 0)
# invert_binary=True → pixels BELOW threshold become WHITE (our lane is dark)
_, binary = cv2.threshold(blurred, 100, 255, cv2.THRESH_BINARY_INV)
```

The RISA-bot track uses a **dark lane on a lighter floor**. Inverting the threshold makes the lane appear white in the binary image, which is what the next step expects.

> [!NOTE]
> If your track has **white tape lines on a dark floor**, change `invert_binary` to `false` in `config/params.yaml` and tune `white_threshold` upward (try 150–200).

### Step 4 — Morphological cleanup

```python
# Remove tiny noise blobs (open = erode then dilate)
kernel_open  = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
binary = cv2.morphologyEx(binary, cv2.MORPH_OPEN, kernel_open)

# Fill small gaps in lane lines (close = dilate then erode)
kernel_close = cv2.getStructuringElement(cv2.MORPH_RECT, (5, 5))
binary = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, kernel_close)
```

After thresholding, the binary image usually has small noisy blobs and tiny gaps in the lane line. These two morphological operations clean it up before we try to locate the lane edges.

### Step 5 — Multi-scanline detection

This is the core lane-finding algorithm, inspired by the **Cytron differential line following** technique.

```text
Binary image (road crop, 320 × 132):

  row 0  (far)   ──────────────────────────────────── scanline 8 (weight 1.0)
                    ◀── expected_left        expected_right ──▶
  ...
  row 66 (mid)   ──────────────────────────────────── scanline 4 (weight 1.5)
  ...
  row 131 (near) ──────────────────────────────────── scanline 1 (weight 2.0)
  
  For each scanline row, scan left-to-right to find white blobs.
  Match each blob to the nearest expected lane boundary.
  Compute lane centre = (left_x + right_x) / 2
```

The bottom scanlines (closer to the robot) are given **higher weight** because what's directly in front matters more than a far-away road section.

```python
# After all scanlines, compute weighted average centre
avg_center_x = sum(pt[0] * wt for pt, wt in zip(center_pts, scan_weights)) / total_weight

# Convert to error: 0 = centred, positive = lane shifted right, negative = lane shifted left
raw_error = (avg_center_x - image_center) / image_center  # range: -1.0 to +1.0
```

### Step 6 — Kalman filter smoothing

```python
# Predict: advance the estimate using last velocity
self._kalman.predict(dt)

# Update: correct with new measurement (if lane found)
if abs(raw_error) >= dead_zone:
    self._kalman.update(raw_error)

# Publish the filtered error
self.filtered_error = self._kalman.position
```

A **Kalman filter** tracks both the position (where the lane is) and velocity (how fast it is moving). This gives two benefits:
1. **Smoothing** — rapid noisy fluctuations are filtered out.
2. **Prediction** — if the camera briefly loses the lane in a shadow, the filter predicts where it should be based on recent movement. The robot keeps steering correctly instead of freezing.

### Step 7 — Publish

```python
self.error_pub.publish(Float32(data=self.lane_error))
```

One number — the filtered lane error — is published to `/lane_error`. That's all the `auto_driver` needs.

---

## 3. How the Robot Steers: PID Control

Open `src/risabot_automode/risabot_automode/auto_driver.py` and find the `_lane_follow_cmd` method.

The `auto_driver` reads `/lane_error` and computes a steering command using a **PID controller**:

```
Steering = Kp × error  +  Ki × ∫error dt  +  Kd × (d error / dt)
```

| Term | Name | Role |
|------|------|------|
| **Kp × error** | Proportional | Main steering force — larger error = harder turn |
| **Ki × ∫error** | Integral | Corrects long-term drift (e.g. if robot always veers right) |
| **Kd × Δerror** | Derivative | Dampens oscillation — slows the correction as it approaches centre |

It also applies **adaptive speed**: the robot slows down when the error is large (sharp turn) and speeds up when driving straight.

```python
speed_mult = max(min_turn_speed, 1.0 - speed_error_scale * abs(error))
linear_x   = forward_speed * speed_mult
```

The resulting `Twist` message passes through `cmd_safety_controller`, which clamps the values within safe hardware limits and stops everything if no command arrives for 350 ms.

---

## 4. Launching the Lane Follower

The RISA-bot includes a ready-made launch file that starts every required node in one command.

### Step 1 — Build the workspace

SSH into the robot and build:

```bash
cd ~/risabotcar_ws
colcon build --packages-select risabot_automode control_servo
source install/setup.bash
```

> [!NOTE]
> You only need to rebuild if source code changed. If you have not modified any files since the last build, skip `colcon build` and just source.

### Step 2 — Launch

```bash
ros2 launch risabot_automode lane_test.launch.py
```

This single command starts the following nodes, in order, with automatic delays so each node has time to initialize:

| Delay | Node | Purpose |
|-------|------|---------|
| 0 s | `astra_camera` | Camera driver — starts publishing frames |
| 0 s | `cmd_safety_controller` | Safety watchdog |
| 0 s | `joy_node` | Joystick (Start button = toggle auto mode) |
| 0 s | `servo_controller` | Motor and steering hardware bridge |
| 0 s | `dashboard` | Web UI at `http://<robot_ip>:8080` |
| 3 s | `line_follower_camera` | Waits 3 s for camera to fully start |
| 5 s | `auto_driver` | Waits 5 s for all perception nodes to be ready |

You will see a stream of log messages in the terminal. When you see lines like:

```
[line_follower_camera]: Line Follower Camera: Ready (MDPI-enhanced — IPM + Kalman + Cytron scanline)
[auto_driver]: Auto Driver Node Starting (Competition Mode)...
```

...the system is running.

### Step 3 — Verify topics are publishing

Open a **second SSH terminal** and check:

```bash
source ~/risabotcar_ws/install/setup.bash

# Lane error should be a steady stream of numbers
ros2 topic echo /lane_error

# Lane lost flag (True = robot cannot see the lane)
ros2 topic echo /lane_lost

# The final command being sent to the hardware
ros2 topic echo /cmd_vel_auto
```

---

## 5. Watching It Live on the Dashboard

1. Open a browser on your laptop and go to `http://192.168.x.x:8080`.
2. The dashboard will show a **debug camera view** in the top-left panel.

In the debug view you will see:

| Colour | Meaning |
|--------|---------|
| 🔵 Blue dots | Detected **left** lane boundary points (one per scanline) |
| 🔴 Pink/red dots | Detected **right** lane boundary points |
| 🟢 Green dots | Computed **lane centre** points |
| Grey horizontal lines | The 8 scanlines across the road crop |
| 🔴 Vertical red line | The **image centre** (where the robot needs to steer toward) |
| 🟣 Horizontal purple line | The **crop boundary** (top of the road region) |

The status text in the top-left of the debug image shows:
- `LOCK(6/8)` — 6 out of 8 scanlines successfully found the lane ✅
- `HOLD(12)` — lane temporarily lost, holding last heading for 12 more frames
- `LOST(5f)` — lane lost for 5 consecutive frames ⚠️
- `CENTERED`, `STEER LEFT`, or `STEER RIGHT` — current steering direction

---

## 6. Enabling Auto Mode

The robot **starts in manual mode** (joystick control). The joystick's **Start button** toggles between manual and autonomous mode.

> [!IMPORTANT]
> Always hold the joystick and be ready to press **Start** to switch back to manual if the robot starts to drift. Keep your hand on the joystick at all times during testing!

1. Place the robot on the track so the camera can see both lane boundaries.
2. Press **Start** on the joystick.
3. Watch the dashboard — the state display should change from `MANUAL` to `LANE_FOLLOW`.
4. The robot will start driving autonomously!
5. Press **Start** again to resume manual control at any time.

---

## 7. Understanding the Key Parameters

All tunable settings live in one file: `config/params.yaml`. Here are the most important ones for lane following.

### Line Follower Camera

```yaml
line_follower_camera:
  ros__parameters:
    white_threshold: 100       # Pixel brightness cutoff for lane detection
    invert_binary: true        # true = dark lane on light floor
    n_scanlines: 8             # Number of horizontal scan rows
    min_valid_scanlines: 2     # Minimum rows needed to call it a "lane lock"
    crop_ratio_base: 0.55      # Fraction of image height used for road
    search_radius_px: 80       # How far (px) to search from last known position
    kalman_enabled: true       # Use Kalman filter for smoothing
    show_debug: true           # Publish debug image to dashboard
```

### Auto Driver (PID Steering)

```yaml
auto_driver:
  ros__parameters:
    forward_speed: 0.15        # m/s base speed (start here, increase slowly)
    pid_kp: 0.8                # Proportional gain — main steering strength
    pid_ki: 0.01               # Integral — fix steady drift
    pid_kd: 0.20               # Derivative — reduce oscillation
    speed_error_scale: 1.5     # How much to slow down in turns
    min_turn_speed: 0.4        # Minimum speed in a sharp turn (40% of forward_speed)
```

### Changing Parameters at Runtime (No Rebuild Needed!)

You can change parameters **while the robot is running** using the ROS 2 parameter CLI — very useful for tuning:

```bash
# Increase forward speed
ros2 param set /auto_driver forward_speed 0.20

# Make steering more aggressive
ros2 param set /auto_driver pid_kp 1.2

# Tune lane detection threshold
ros2 param set /line_follower_camera white_threshold 120
```

> [!TIP]
> Changes take effect immediately. You do **not** need to restart nodes or rebuild to test parameter changes at runtime.

---

## 8. Hands-On Exercise: Observe and Tune

### Exercise 1: Understand the Error Signal

1. Place the robot on the lane with the camera pointing straight ahead.
2. Open two terminals side-by-side.
3. In terminal 1, watch the lane error:
   ```bash
   ros2 topic echo /lane_error
   ```
4. Gently slide the robot slightly to the left of centre — the error value should go **negative**.
5. Slide it to the right — the error should go **positive**.
6. Centre it perfectly — the error should be very close to `0.0`.

**Question:** Why do you think the error is normalised to the range -1.0 to +1.0 instead of being measured in pixels?

### Exercise 2: Observe the Debug View

1. Launch the system: `ros2 launch risabot_automode lane_test.launch.py`
2. Open the dashboard in your browser.
3. Hold your hand over one side of the camera to block the lane line.
4. Observe the status text — it should change from `LOCK` → `HOLD` → eventually `LOST`.
5. Remove your hand — it should return to `LOCK` within a few frames.

### Exercise 3: Tune the Forward Speed

1. Start with the robot on a straight section of track.
2. Enable auto mode (press Start on joystick).
3. Increase the forward speed step by step:
   ```bash
   ros2 param set /auto_driver forward_speed 0.18
   ros2 param set /auto_driver forward_speed 0.22
   ```
4. Watch the dashboard. At what speed does the robot start to oscillate on straight sections?
5. Reduce `pid_kd` by 0.05 increments to dampen oscillation:
   ```bash
   ros2 param set /auto_driver pid_kd 0.15
   ```

**Challenge:** Find the fastest stable speed for your track without the robot leaving the lane!

---

## 9. Troubleshooting

| Symptom | Likely Cause | Fix |
|---------|-------------|-----|
| `/lane_error` not publishing | Camera not running | Check `ros2 topic hz /camera/color/image_raw` |
| `LOST` on dashboard constantly | Threshold wrong for track | Tune `white_threshold`, toggle `invert_binary` |
| Robot oscillates left-right | `pid_kp` too high | Reduce `pid_kp`, increase `pid_kd` |
| Robot drifts to one side on straight | Mechanical offset or low `pid_ki` | Increase `pid_ki` slightly (e.g. 0.02) |
| Robot stops when it should turn | `min_valid_scanlines` too high | Reduce to `1`, or check for shadows on track |
| Dashboard shows camera but no dots | Brightness/threshold mismatch | Toggle `invert_binary`, adjust `white_threshold` |

---

## 10. What You've Learned

In this module you traced the complete lane-following data flow:

```text
Camera → Image Processing → Lane Error → PID Controller → Motor Command → Wheels
```

You learned that:
- The camera image is **cropped, contrast-enhanced, and thresholded** to isolate the lane
- **Multiple horizontal scanlines** find the left and right lane boundaries
- A **Kalman filter** smooths the error and predicts through momentary lane loss
- A **PID controller** in `auto_driver` converts the error into a steering command
- A **safety controller** ensures the hardware is never over-commanded
- All parameters can be tuned live using `ros2 param set`

---

**Previous:** [Module 2 — Dashboard & Sensors](02-dashboard-and-sensors.md)
**Next:** [Module 4 — Obstacle Detection](05-obstacle-detection.md)
