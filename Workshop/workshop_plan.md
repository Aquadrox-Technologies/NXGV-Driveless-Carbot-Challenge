# 🤖 RISA-bot Competition Workshop — 2-Day Instructor Plan

> **Teaching Method:** Instructor teaches and demonstrates → Participants try it → Instructor supervises  
> **Prerequisite:** Participants have completed Workshop 00 (Linux) and 01 (ROS basics)  
> **Platform:** RISA-bot (ROS 2 Humble, RDK X5, Astra Camera, YDLiDAR)

---

## Testing Field Layout

```
LANE 1                   LANE 2                   TRACK 3
┌───────────────┐        ┌───────────────┐        ┌──────────────┐
│  Lane Follow  │        │  Lane Follow  │        │  Roundabout  │
│  + Tunnel     │        │  + Hill       │        │  + Boom Gate │
│               │        │  + Bumper     │        │  + Parking   │
│               │        │  + Traffic    │        │  + Obstruct. │
│               │        │    Light      │        │              │
└───────────────┘        └───────────────┘        └──────────────┘
```

---

## 🗓️ DAY 1

### Block 1 — Recap: ROS & Linux Basics
`🕙 10:00 – 10:35 (35 min)`

**TEACH (15 min)**

Recap from Workshop 00 & 01. Cover only what's needed for today:

- SSH into robot: `ssh sunrise@<robot_ip>`
- Workspace and sourcing:
  ```bash
  cd ~/risabotcar_ws
  source install/setup.bash
  ```
- Essential ROS commands they'll use all day:
  ```bash
  ros2 topic list              # see all active topics
  ros2 topic echo /lane_error  # read a topic live
  ros2 node list               # see all running nodes
  ros2 param set /node param value   # change a parameter live
  ros2 param get /node param         # read a parameter value
  ```
- Launch the system: `ros2 launch risabot_automode bringup.launch.py`
- Build aliases: `cb` = rebuild, `sos` = re-source

**TRY (20 min)**

Participants SSH into their robot and run through the commands above themselves. Instructor walks around confirming each team is connected and can see topic output.

```bash
# Participants run these one by one:
ros2 launch risabot_automode bringup.launch.py

# In a second SSH terminal:
ros2 topic list
ros2 topic echo /lane_error
ros2 node list
ros2 param get /auto_driver forward_speed
```

---

### Block 2 — Competition Overview
`🕙 10:35 – 11:05 (30 min)`

**TEACH (20 min)**

Show [competition_layout_overview.jpeg](file:///c:/Users/Lenovo/Downloads/Kerja/RISA-bot-1/Guide/competition_layout_overview.jpeg). Walk through all 9 challenges in sequence and explain the sensor + approach for each:

| # | Challenge | Sensor | Approach | Test Setup |
|---|-----------|--------|----------|------------|
| 1 | Obstruction | LiDAR | Timed dodge maneuver | Track 3 |
| 2 | Roundabout | Camera | Lane following through curves | Track 3 |
| 3 | Tunnel | LiDAR | Wall following (centerline PD) | Lane 1 |
| 4 | Boom Gate | LiDAR | Point cluster detection | Track 3 |
| 5 | Hill | Camera + IMU | Lane follow + speed boost | Lane 2 |
| 6 | Bumper | Camera | Lane follow — no special code | Lane 2 |
| 7 | Traffic Light | Camera | HSV color thresholding | Lane 2 |
| 8 | Parallel Park | Odometry | Recorded trajectory playback | Track 3 |
| 9 | Perp Park | Odometry | Recorded trajectory playback | Track 3 |

Key points to communicate:
- Every challenge maps to one sensor and one algorithm
- Lane following is the **foundation** — used on most challenges
- The robot's brain (`auto_driver`) switches between algorithms automatically using a priority-based state machine
- This workshop focuses on understanding those algorithms well enough to tune them for competition conditions

**TRY (10 min)**

Participants open [challenges_breakdown.md](file:///c:/Users/Lenovo/Downloads/Kerja/RISA-bot-1/Guide/challenges_breakdown.md) on their laptops and read through the challenge descriptions while the system is running.

---

### Block 3 — Architecture: How RISA-bot is Built
`🕙 11:05 – 11:40 (35 min)`

**TEACH (20 min)**

Show the node graph from [ARCHITECTURE.md](file:///c:/Users/Lenovo/Downloads/Kerja/RISA-bot-1/ARCHITECTURE.md). Explain the 3-layer structure:

```
Sensors (Camera, LiDAR, Joystick)
    ↓
Perception (lane follower, tunnel, traffic light, etc.)
    ↓
Brain (auto_driver → cmd_safety_controller → servo_controller → Motors)
```

**How to include a component in your robot** — show the pattern in [bringup.launch.py](file:///c:/Users/Lenovo/Downloads/Kerja/RISA-bot-1/src/risabot_automode/launch/bringup.launch.py):
1. Find the hardware SDK (already included in `src/` — e.g. `YDLidar-SDK`, `ros2_astra_camera`)
2. Include its launch file using `IncludeLaunchDescription`
3. Add your own nodes using the `Node(...)` entry
4. Load settings from `params.yaml` using `parameters=[params_file]`

Show the 3-tier startup timing in `bringup.launch.py`:
- **0s** — Hardware: camera, LiDAR, joystick, servo controller, dashboard
- **3s** — Perception: line follower, tunnel, traffic light, obstacle detection
- **5s** — Brain: `auto_driver` (waits for all perception nodes to be ready)

Show [params.yaml](file:///c:/Users/Lenovo/Downloads/Kerja/RISA-bot-1/src/risabot_automode/config/params.yaml) — one file that holds ALL tunable settings for every node. Changing a value here and rebuilding (or using `ros2 param set` at runtime) updates that node's behaviour.

**TRY (15 min)**

Participants open both files on their laptops alongside the running system:

```bash
# On robot — show the launch file
cat ~/risabotcar_ws/src/RISA-bot/src/risabot_automode/launch/bringup.launch.py

# Show the params file
cat ~/risabotcar_ws/src/RISA-bot/src/risabot_automode/config/params.yaml
```

They find these specific values in `params.yaml`:
- `forward_speed` under `auto_driver`
- `white_threshold` under `line_follower_camera`
- `kp` and `kd` under `tunnel_wall_follower`

Then try changing one via CLI:
```bash
ros2 param set /auto_driver forward_speed 0.12
ros2 param get /auto_driver forward_speed   # confirm it changed
ros2 param set /auto_driver forward_speed 0.15   # revert
```

---

### Block 4 — Dashboard: Monitoring & Tuning Interface
`🕙 11:40 – 12:10 (30 min)`

**TEACH (12 min)**

Open `http://<robot_ip>:8080` on projector. Walk through each panel:

- **State display** — current robot state (MANUAL, LANE_FOLLOW, TUNNEL, etc.)
- **Camera debug tabs** — switch between: Lane Lines / Traffic Light / Obstacle / Signage
  - Lane Lines: blue dots = left edge, pink dots = right edge, green dots = center, purple line = crop boundary
- **Sensor panel** — green/red indicators for each sensor
- **LiDAR canvas** — real-time laser dots
- **Odometry** — distance and speed
- **Parameters drawer** (slide-out on the right):
  - Get — read current value
  - Set — change a value live (takes effect immediately, no restart needed)
  - **💾 Save Current as Default** — writes all current values back to `params.yaml`

**TRY (18 min)**

Participants on their own dashboards:

1. Switch to **Lane Lines** debug tab — observe what the robot sees
2. Open Parameters drawer → find `forward_speed` → change to `0.20` → Set
3. Verify: `ros2 param get /auto_driver forward_speed` in terminal
4. Change `white_threshold` to `50` → watch Lane Lines tab (everything becomes "lane" — too sensitive)
5. Change `white_threshold` to `220` → nothing detected (too strict)
6. Revert both to defaults, click **💾 Save**

Instructor walks around confirming each team can use the drawer and see changes reflected.

---

### Block 5 — Lane Detection: How the Robot Sees the Lane
`🕙 12:10 – 1:00 (50 min)`

**TEACH (20 min)**

Open [line_follower_camera.py](file:///c:/Users/Lenovo/Downloads/Kerja/RISA-bot-1/src/risabot_automode/risabot_automode/line_follower_camera.py) and [04-lane-follower.md](file:///c:/Users/Lenovo/Downloads/Kerja/RISA-bot-1/Workshop/04-lane-follower.md) on projector. Walk through the processing pipeline step by step:

```
Camera frame
  → Resize to 320×240
  → Crop bottom portion          ← controlled by crop_ratio_base
  → CLAHE contrast enhancement   ← compensates uneven lighting
  → Threshold to binary          ← controlled by white_threshold
  → Morphological cleanup        ← removes noise, fills gaps
  → Multi-scanline detection     ← finds left + right edges
  → Kalman filter smoothing      ← removes jitter
  → Publish /lane_error          ← single number: -1.0 (left) to +1.0 (right)
```

Explain the two key parameters in detail:

**`crop_ratio_base`** (default 0.55):
- Controls how much of the bottom of the image is used as the "road region"
- Higher = robot looks further ahead (more road visible, purple line lower on screen)
- Lower = robot looks at what's immediately in front (purple line higher)
- Too low: robot cuts corners on curves (reacts too late)
- Too high: picks up background noise (walls, ceiling)

**`white_threshold`** (default 100):
- Brightness cutoff for lane detection. With `invert_binary: true`, pixels BELOW this value = lane
- Lower value = more sensitive (picks up more as "lane")
- Higher value = stricter (only very dark regions count as lane)
- Tune this FIRST — clean detection is the foundation of everything

**TRY (25 min) — on Lane 1 or Lane 2**

Dashboard → switch to **Lane Lines** debug tab. Participants tune while watching the overlay update live:

```bash
# Tune crop_ratio_base — watch purple line move
ros2 param set /line_follower_camera crop_ratio_base 0.3   # line moves up (less road)
ros2 param set /line_follower_camera crop_ratio_base 0.7   # line moves down (more road)
# Find the value where blue/pink dots cleanly track both lane edges

# Tune white_threshold — watch dot coverage
ros2 param set /line_follower_camera white_threshold 50    # too sensitive
ros2 param set /line_follower_camera white_threshold 220   # too strict
# Find the value where ONLY the lane borders light up

# Observe the error live
ros2 topic echo /lane_error
# Slide robot left → negative values. Right → positive. Center → near 0.
```

Participants write down their best values for `crop_ratio_base` and `white_threshold`.

Instructor supervises — look for: blue/pink dots tracking cleanly with no false detections on the floor.

**Save values via dashboard 💾 when detection looks clean.**

---

### 🍽️ LUNCH BREAK: 1:00 – 2:30

> [!IMPORTANT]
> **Instructor tasks:**
> - Confirm tunnel is set up on Lane 1
> - Charge any low robots
> - Note which teams had detection issues — support them first after break

---

### Block 6 — PID Steering: How the Robot Turns
`🕙 2:30 – 3:10 (40 min)`

**TEACH (12 min)**

Explain PID using the lane error signal as input:

```
lane_error  →  PID controller  →  angular.z (steering command)

steering = (Kp × error) + (Ki × accumulated_error) + (Kd × rate_of_change)
```

| Term | Parameter | Role | Too low | Too high |
|------|-----------|------|---------|----------|
| P | `pid_kp` | Main steering strength | Barely turns on curves | Oscillates left-right |
| I | `pid_ki` | Fixes persistent drift to one side | Slow drift correction | Overshoots, unstable |
| D | `pid_kd` | Damping — prevents overshooting | Oscillates after turns | Sluggish, jerky |

Adaptive speed — robot automatically slows in sharp turns:
```python
speed_multiplier = max(min_turn_speed, 1.0 - speed_error_scale × |error|)
```
So at full error (`1.0`), speed drops to `min_turn_speed` fraction. At no error (`0.0`), full `forward_speed`.

Starting values to use:
```bash
ros2 param set /auto_driver forward_speed 0.10   # conservative start
ros2 param set /auto_driver pid_kp 0.5
ros2 param set /auto_driver pid_kd 0.2
ros2 param set /auto_driver pid_ki 0.01
```

**TRY (25 min) — on Lane 1**

Place robot on lane. Enable auto mode (Start button on joystick). Instructor guides tuning:

```bash
# Start here:
ros2 param set /auto_driver forward_speed 0.10
ros2 param set /auto_driver pid_kp 0.5
ros2 param set /auto_driver pid_kd 0.2

# If oscillating on straights → lower kp, raise kd:
ros2 param set /auto_driver pid_kp 0.4
ros2 param set /auto_driver pid_kd 0.3

# If not turning enough on curves → raise kp:
ros2 param set /auto_driver pid_kp 0.8

# If drifting to one side on straight → small ki:
ros2 param set /auto_driver pid_ki 0.02

# If cutting corners → raise crop_ratio_base:
ros2 param set /line_follower_camera crop_ratio_base 0.5

# Once stable → increase speed gradually:
ros2 param set /auto_driver forward_speed 0.13
ros2 param set /auto_driver forward_speed 0.15
```

Instructor walks around supervising. Watch the dashboard debug view — use the `/lane_error` echo to diagnose.

**Save via 💾 when stable on Lane 1 straights and curves.**

---

### Block 7 — Tunnel Navigation: LiDAR Wall Following
`🕙 3:10 – 4:10 (60 min)`

**TEACH (15 min)**

Why LiDAR for tunnels — camera fails in darkness, LiDAR doesn't need light.

Walk through [tunnel_wall_follower.py](file:///c:/Users/Lenovo/Downloads/Kerja/RISA-bot-1/src/risabot_automode/risabot_automode/tunnel_wall_follower.py) and [05-tunnel-navigation.md](file:///c:/Users/Lenovo/Downloads/Kerja/RISA-bot-1/Workshop/05-tunnel-navigation.md):

```
LiDAR scan
  → Convert polar (angle, dist) to Cartesian (x, y)
  → Classify: left wall (15°–120°) vs right wall (-120° to -15°)
  → Bin wall points by forward distance
  → Compute centerline: midpoint between left and right at each distance
  → PD control: lateral error + heading error → angular velocity
  → EMA smoothing → publish /tunnel_cmd_vel
```

Two error signals (better than one):
- **Lateral error** — how far off-center the robot is right now
- **Heading error** — which direction the tunnel is curving (anticipates turns early)

Auto-switching logic in `auto_driver`:
- Both walls detected for **3 consecutive frames** → enters `TUNNEL` state → uses `/tunnel_cmd_vel`
- Walls absent for 3 frames → back to `LANE_FOLLOW` → uses `/lane_error`
- This 3-frame requirement (hysteresis) prevents flickering at tunnel entrance/exit

Key tuning parameters:
| Parameter | Default | Effect |
|-----------|---------|--------|
| `kp` | 5.0 | Lateral centering strength |
| `kd` | 0.5 | Lateral damping |
| `kp_heading` | 1.0 | Curve anticipation |
| `forward_speed` | 0.12 | Speed inside tunnel |
| `min_wall_points` | 5 | Points required to detect a wall |

**TRY (40 min) — on Lane 1 (tunnel section)**

Step 1 — Verify detection (10 min):
```bash
# Echo the tunnel debug output
ros2 topic echo /tunnel_debug
# l = left distance, r = right distance, lat = lateral error, w = angular output
```
Participants place robot inside the tunnel → confirm `l` and `r` values appear → watch dashboard Sensor panel show `IN TUNNEL`.

Step 2 — Drive through tunnel (20 min):

Enable auto mode → robot approaches lane section → enters tunnel → drives through → exits back to lane following. Observe state changes on dashboard.

```bash
# If oscillating between walls:
ros2 param set /tunnel_wall_follower kp 3.0
ros2 param set /tunnel_wall_follower kd 0.8

# If drifting to one side:
ros2 param set /tunnel_wall_follower target_center_dist 0.02   # adjust ±

# If not detecting tunnel at all:
ros2 param set /tunnel_wall_follower min_wall_points 3

# If too fast:
ros2 param set /tunnel_wall_follower forward_speed 0.10
```

Step 3 — Observe the mode switch (10 min):
```bash
# Two terminals side by side:
ros2 topic echo /lane_error       # active outside tunnel
ros2 topic echo /tunnel_cmd_vel   # active inside tunnel
```
Drive robot in and out of tunnel — participants see which topic becomes active at each point.

**Save via 💾 when tunnel run is clean.**

---

### Block 8 — Full Lane 1 Tuning Run
`🕙 4:10 – 5:00 (50 min)`

**TEACH (10 min)**

Tuning order — always follow this sequence:

```
1. white_threshold        → clean lane detection first
2. crop_ratio_base        → correct crop region for this lane
3. pid_kp / pid_kd        → stable steering (no oscillation)
4. tunnel kp / kd         → stable wall following
5. forward_speed          → increase LAST, only when steering is stable
```

Print and distribute the cheat sheet from [tuning_guide.md](file:///c:/Users/Lenovo/Downloads/Kerja/RISA-bot-1/Guide/tuning_guide.md):

```bash
# 8 most common params:
ros2 param set /auto_driver forward_speed 0.15
ros2 param set /auto_driver pid_kp 0.8
ros2 param set /auto_driver pid_kd 0.20
ros2 param set /auto_driver min_turn_speed 0.4
ros2 param set /line_follower_camera white_threshold 100
ros2 param set /line_follower_camera crop_ratio_base 0.55
ros2 param set /tunnel_wall_follower kp 5.0
ros2 param set /tunnel_wall_follower kd 0.5
```

**TRY (35 min) — Lane 1 full runs**

Each team runs the full Lane 1 end-to-end repeatedly:
- Lane section → tunnel → lane section
- Adjust one parameter at a time between runs
- Instructor supervises, diagnoses using dashboard debug view, helps struggling teams

Instructor notes to self while supervising:
- If robot leaves the lane on curves → `crop_ratio_base` too low or `pid_kp` too low
- If robot oscillates → `pid_kp` too high or `pid_kd` too low
- If tunnel detection flickers → `min_wall_points` or `tunnel_hysteresis_frames`
- If robot drifts in tunnel → `target_center_dist` adjustment

**Save final params via 💾 at end of session.**

Recap (5 min): Recap what was covered today — detection, PID, tunnel — and preview Day 2.

---

## 🗓️ DAY 2

### Block 9 — Warm-Up: Re-Test Lane 1
`🕙 10:00 – 10:20 (20 min)`

**TEACH (3 min)**

Briefly explain: params are loaded from `params.yaml` on launch. Verify yesterday's work is intact.

**TRY (17 min)**

Each team launches and runs a quick Lane 1 test:
```bash
ros2 launch risabot_automode bringup.launch.py
# Verify params loaded:
ros2 param get /auto_driver pid_kp
ros2 param get /line_follower_camera white_threshold
```

If detection changed (different lighting today), re-tune `white_threshold` first. Run one lane+tunnel pass — confirm it still works before continuing.

---

### Block 10 — Hill & Bumper (Lane 2)
`🕙 10:20 – 10:55 (35 min)`

**TEACH (12 min)**

Hill and bumper require no new code — the existing lane follower handles them automatically.

**Hill:**
- The camera still sees lane lines on the ramp surface → lane following continues
- The IMU measures pitch angle. When pitch exceeds `hill_pitch_threshold` (default 12°), `auto_driver` enters `HILL` state
- In HILL state: speed is boosted to `hill_drive_speed` (default 0.35 m/s), steering is scaled to drive straighter (`hill_steer_scale = 0.0` = ignore lane error, drive straight up)
- After cresting the hill, pitch drops → returns to LANE_FOLLOW

**Bumper:**
- Just a physical bump the robot drives over. No detection, no state change. Lane following handles it. Only concern: enough speed to clear it without stalling.

Parameters to know:
```bash
ros2 param set /auto_driver hill_pitch_threshold 12.0  # degrees — trigger angle
ros2 param set /auto_driver hill_drive_speed 0.35      # m/s — climbing speed
```

**TRY (20 min) — on Lane 2**

Run robot on Lane 2 in auto mode. Let it approach the hill:

```bash
# Watch IMU pitch and state on dashboard
ros2 topic echo /imu/pitch
```

- If stalls on hill: increase `hill_drive_speed` to 0.40
- If triggers hill mode too early: increase `hill_pitch_threshold` to 15.0
- If triggers too late: decrease to 10.0
- Drive over bumper — should be seamless with existing settings

Instructor supervises. Note if any robot needs mechanical check (loose wires from vibration).

---

### Block 11 — Traffic Light Detection (Lane 2)
`🕙 10:55 – 11:45 (50 min)`

**TEACH (15 min)**

How it works — [traffic_light_detector.py](file:///c:/Users/Lenovo/Downloads/Kerja/RISA-bot-1/src/risabot_automode/risabot_automode/traffic_light_detector.py):

```
Camera frame
  → Convert to HSV color space
  → Apply color masks (Red, Yellow, Green hue ranges)
  → Find circular blobs matching each color
  → Count pixels per color
  → Publish /traffic_light_state ("red" / "yellow" / "green" / "unknown")
```

HSV explained briefly:
- **H** (Hue) = the color (0–180 in OpenCV, wraps around)
- **S** (Saturation) = how vivid
- **V** (Value) = how bright
- Red wraps around 0° so it needs two ranges (`red_h_low1/high1` and `red_h_low2/high2`)

> [!WARNING]
> HSV thresholds are extremely sensitive to lighting. The values in `params.yaml` are a starting point — **always re-tune at the competition venue.**

In `auto_driver`: when `TRAFFIC_LIGHT` state is active, red or yellow → robot stops, green → robot moves.

Key parameters:
```bash
ros2 param set /traffic_light_detector sat_min 80        # minimum saturation
ros2 param set /traffic_light_detector val_min 80        # minimum brightness
ros2 param set /traffic_light_detector min_pixel_count 50  # noise filter
ros2 param set /traffic_light_detector required_confidence 3  # frames before acting
```

**TRY (30 min) — on Lane 2**

Step 1 — Test detection in isolation:
```bash
# Force traffic light state
ros2 topic pub --once /set_challenge std_msgs/String "data: TRAFFIC_LIGHT"

# Watch the state
ros2 topic echo /traffic_light_state
```

Hold colored cards in front of the camera:
- Red card → should read `"red"`
- Green card → should read `"green"`
- Yellow card → should read `"yellow"`

Tune if needed:
```bash
# Not detecting anything:
ros2 param set /traffic_light_detector sat_min 50
ros2 param set /traffic_light_detector val_min 50

# False positives (detecting wrong objects):
ros2 param set /traffic_light_detector min_pixel_count 100

# Slow to respond:
ros2 param set /traffic_light_detector required_confidence 2
```

Step 2 — Test integrated on Lane 2:
- Robot drives lane → approaches traffic light position → stops on red → resumes on green
- Dashboard shows state switch: `LANE_FOLLOW` → `TRAFFIC_LIGHT` → `LANE_FOLLOW`

**Save via 💾 when working.**

---

### Block 12 — State Machine: Testing Challenges in Isolation
`🕙 11:45 – 12:20 (35 min)`

**TEACH (12 min)**

Show the state machine priority table from [ARCHITECTURE.md](file:///c:/Users/Lenovo/Downloads/Kerja/RISA-bot-1/ARCHITECTURE.md):

| Priority | State | Triggered by |
|----------|-------|--------------|
| 1 | MANUAL | Joystick Start button |
| 4 | OBSTRUCTION | LiDAR detects lateral obstacle |
| 7 | TUNNEL | Walls on both sides detected |
| 9 | TRAFFIC_LIGHT | Red/yellow detected (when armed) |
| 9.5 | HILL | IMU pitch exceeds threshold |
| 11 | LANE_FOLLOW | Default |

Lap tracking: `current_lap` = 1 or 2. Some challenges only activate on specific laps (e.g. parking on Lap 2).

Distance-based transitions — these control WHEN the state advances:
```bash
ros2 param set /auto_driver t_roundabout_sec 8.0      # time in roundabout
ros2 param set /auto_driver dist_roundabout 2.0       # distance to exit roundabout
ros2 param set /auto_driver dist_boom_gate_1_pass 0.5 # distance after boom gate 1
```

**The most important tool for testing: force any state directly**
```bash
ros2 topic pub --once /set_challenge std_msgs/String "data: TUNNEL"
ros2 topic pub --once /set_challenge std_msgs/String "data: TRAFFIC_LIGHT"
ros2 topic pub --once /set_challenge std_msgs/String "data: OBSTRUCTION"
ros2 topic pub --once /set_challenge std_msgs/String "data: LANE_FOLLOW"
```
Use this on competition day to test individual challenges without running the full course.

**TRY (20 min)**

Participants force each state and observe dashboard:

```bash
# Force each state, observe dashboard state display and robot behaviour
ros2 topic pub --once /set_challenge std_msgs/String "data: TUNNEL"
# → State shows TUNNEL, robot uses LiDAR

ros2 topic pub --once /set_challenge std_msgs/String "data: TRAFFIC_LIGHT"
# → State shows TRAFFIC_LIGHT, robot stops

ros2 topic pub --once /set_challenge std_msgs/String "data: HILL"
# → State shows HILL, robot boosts speed

ros2 topic pub --once /set_challenge std_msgs/String "data: LANE_FOLLOW"
# → Returns to camera lane following
```

---

### Block 13 — Boom Gate & Roundabout (Track 3)
`🕙 12:20 – 1:00 (40 min)`

**TEACH (12 min)**

**Boom Gate** — [boom_gate_detector.py](file:///c:/Users/Lenovo/Downloads/Kerja/RISA-bot-1/src/risabot_automode/risabot_automode/boom_gate_detector.py):
- LiDAR looks at a narrow forward arc (±20°, 0.1–0.8m range)
- If a dense cluster of points appears at similar distances (low distance variance) → horizontal bar = gate CLOSED
- Hysteresis: must see OPEN for 3 consecutive frames before publishing `True`
- Two gates on the course: Gate 1 (always open Lap 1, closed Lap 2), Gate 2 (random)

**Roundabout:**
- Uses normal lane following — the roundabout has painted lines
- `auto_driver` enters `ROUNDABOUT` state after obstruction clears
- `t_roundabout_sec` controls how long to follow before exiting

```bash
# Key boom gate params:
ros2 param set /boom_gate_detector min_gate_points 5       # points needed to detect bar
ros2 param set /boom_gate_detector distance_variance_max 0.05  # how "flat" the bar must be
```

**TRY (25 min) — on Track 3**

Boom gate test:
```bash
ros2 topic pub --once /set_challenge std_msgs/String "data: BOOM_GATE_2"
ros2 topic echo /boom_gate_open
```
- Hold a horizontal stick/ruler in front of robot → should read `False` (closed)
- Remove → should read `True` (open)
- Tune `min_gate_points` and `distance_variance_max` as needed

Roundabout test on Track 3:
- Place robot at roundabout entrance → auto mode → follows lane through roundabout
- Adjust `t_roundabout_sec` if it exits the roundabout too early or too late

---

### 🍽️ LUNCH BREAK: 1:00 – 2:30

> [!IMPORTANT]
> **Instructor tasks:**
> - Set up parking slot on Track 3
> - Charge all robots FULLY — critical for recording accuracy
> - Print tuning cheat sheet for each team if not already done

---

### Block 14 — Record & Playback: Parking
`🕙 2:30 – 3:25 (55 min)`

**TEACH (15 min)**

Reference [06-autonomous-parking.md](file:///c:/Users/Lenovo/Downloads/Kerja/RISA-bot-1/Workshop/06-autonomous-parking.md).

Why record & playback — reactive sensors are unreliable for precise parking. Open-loop recording at 20Hz is repeatable when conditions are consistent.

The interface:
| Button | Command | Action |
|--------|---------|--------|
| Button A | `record` | Start recording (clears buffer, records at 20Hz) |
| Button A again | `stop` | Stop recording |
| Button B | `save` | Write to `~/recorded_movement.json` |
| Button X | `playback` | Replay saved recording |

Can also publish directly:
```bash
ros2 topic pub --once /record_playback_cmd std_msgs/String "{data: 'record'}"
ros2 topic pub --once /record_playback_cmd std_msgs/String "{data: 'stop'}"
ros2 topic pub --once /record_playback_cmd std_msgs/String "{data: 'save'}"
ros2 topic pub --once /record_playback_cmd std_msgs/String "{data: 'playback'}"
```

**What affects recording accuracy:**
- 🔋 **Battery level** — open-loop is voltage-sensitive. A low battery plays back slower than it recorded. **Charge fully.**
- 🏗️ **Surface** — record on the SAME floor type as competition
- 🎮 **Input quality** — slow, smooth joystick movements = clean recording = clean playback
- ⏱️ **`parking_idle_duration`** — time robot waits (default 2.0s) before starting playback, letting it fully stop:
  ```bash
  ros2 param set /auto_driver parking_idle_duration 2.5
  ```

Signage trigger flow (how it works in auto mode on Lap 2):
```
signage_detector detects parking sign
  → auto_driver: PARKING_IDLE (stop + wait parking_idle_duration)
  → auto_driver: PARKING_PLAYBACK (publishes "playback" command)
  → servo_controller: executes recorded movement
  → auto_driver: FINISHED
```

**TRY (35 min) — on Track 3 parking slot**

Step 1 — Record (15 min):
1. Position robot at the correct starting point relative to slot
2. Press **Button A** → terminal shows `🔴 RECORDING started`
3. Drive slowly and smoothly into the slot using joystick
4. Press **Button A** → `⏹ RECORDING stopped`
5. Press **Button B** → `Saved X movement samples to ~/recorded_movement.json`

Step 2 — Playback test (15 min):
1. Return robot to exact starting position
2. Press **Button X** → robot replays
3. Evaluate: did it park cleanly?
4. If drifts at start: increase `parking_idle_duration` to 2.5 or 3.0
5. If trajectory is wrong: re-record with smoother movements
6. Repeat until 3 consecutive playbacks land in the slot

Step 3 (if time allows) — Test signage trigger:
```bash
ros2 param set /auto_driver current_lap 2
# Enable auto mode → robot drives → sees sign → PARKING_IDLE → playback
```

---

### Block 15 — Obstruction Avoidance (Track 3)
`🕙 3:25 – 4:00 (35 min)`

**TEACH (12 min)**

Reference [challenges_breakdown.md](file:///c:/Users/Lenovo/Downloads/Kerja/RISA-bot-1/Guide/challenges_breakdown.md) Section 2.

The detect → timed maneuver → resume pattern:

```
LiDAR detects object in lane < detect_dist
  → Check left vs right clearance
  → Phase 1: Steer away (steer_away_duration seconds)
  → Phase 2: Drive straight alongside obstacle (pass_duration seconds)
  → Phase 3: Steer back into lane (steer_back_duration seconds)
  → Set active=False → auto_driver resumes lane following
```

All timing is open-loop — same principle as parking recording.

Key parameters:
```bash
ros2 param set /obstruction_avoidance detect_dist 0.50       # how far ahead to detect
ros2 param set /obstruction_avoidance steer_angular 0.6      # how hard to steer away
ros2 param set /obstruction_avoidance pass_duration 2.0      # time alongside obstacle
ros2 param set /obstruction_avoidance steer_back_duration 1.5  # time returning to lane
```

**TRY (20 min) — on Track 3**

Place obstacle block in the lane:
```bash
ros2 topic pub --once /set_challenge std_msgs/String "data: OBSTRUCTION"
```
Enable auto mode → robot approaches → dodges:

| Problem | Fix |
|---------|-----|
| Doesn't detect early enough | Increase `detect_dist` to 0.65 |
| Clips obstacle while passing | Increase `pass_duration` to 2.5 |
| Overshoots return to lane | Decrease `steer_back_duration` to 1.0 |
| Doesn't steer far enough | Increase `steer_angular` to 0.8 |

**Save via 💾 when dodge is clean.**

---

### Block 16 — Lane-by-Lane Testing Runs
`🕙 4:00 – 4:50 (50 min)`

**TEACH (5 min)**

Each setup is tested end-to-end. The goal is to identify any remaining issues and fix them. Between each run, adjust one parameter at a time. Save when stable.

**TRY — Rotation through all 3 setups (45 min)**

Teams rotate through each setup. Recommended allocation:

| Rotation | Duration | Setup | What to test |
|----------|----------|-------|-------------|
| Round 1 | 15 min | **Lane 1** | Full run: lane follow → tunnel → lane follow exit |
| Round 2 | 15 min | **Lane 2** | Full run: lane follow → hill → bumper → traffic light stop/go |
| Round 3 | 15 min | **Track 3** | Roundabout → boom gate detect → parking playback |

For each run:
- Start in auto mode
- Let it run, note where it fails
- Fix the parameter
- Re-run to verify
- Save when clean

Instructor rotates between teams actively during this block — this is the most hands-on supervision session of the workshop.

---

### Block 17 — Wrap-Up & Competition Preparation
`🕙 4:50 – 5:00 (10 min)`

**TEACH (10 min)**

Competition day checklist — display on projector:

| # | Action |
|---|--------|
| 1 | **Re-tune `white_threshold` and HSV ranges at the venue** — lighting changes everything |
| 2 | **Charge batteries fully** before recording and before competition runs |
| 3 | **Save params before experimenting** — use 💾 button every time you find a working config |
| 4 | **Use `/set_challenge` to test individual challenges** before running the full course |
| 5 | **Keep `forward_speed` conservative** — finishing the course matters more than speed |
| 6 | **If detection breaks** — fix `white_threshold` first before touching anything else |
| 7 | **Re-record parking** if the competition surface differs from your practice surface |
| 8 | **Tune in order** — detection → steering → speed. Never skip ahead |

Point participants to the reference materials for continued study:
- [tuning_guide.md](file:///c:/Users/Lenovo/Downloads/Kerja/RISA-bot-1/Guide/tuning_guide.md) — full symptom → fix reference
- [commands_reference.md](file:///c:/Users/Lenovo/Downloads/Kerja/RISA-bot-1/Guide/commands_reference.md) — all ROS topics and commands
- [challenges_breakdown.md](file:///c:/Users/Lenovo/Downloads/Kerja/RISA-bot-1/Guide/challenges_breakdown.md) — code-level explanation of each challenge

---

## ⏱️ Time Budget

### Day 1

| Block | Time | Duration | Topic | Teach | Try |
|-------|------|----------|-------|-------|-----|
| 1 | 10:00–10:35 | 35 min | ROS + Linux recap | 15 min | 20 min |
| 2 | 10:35–11:05 | 30 min | Competition overview | 20 min | 10 min |
| 3 | 11:05–11:40 | 35 min | Architecture + setup pattern | 20 min | 15 min |
| 4 | 11:40–12:10 | 30 min | Dashboard | 12 min | 18 min |
| 5 | 12:10–1:00 | 50 min | Lane detection (image processing) | 20 min | 25 min + 5 save |
| — | 1:00–2:30 | 90 min | LUNCH | — | — |
| 6 | 2:30–3:10 | 40 min | PID steering (Lane 1) | 12 min | 25 min + 3 save |
| 7 | 3:10–4:10 | 60 min | Tunnel navigation (Lane 1) | 15 min | 40 min + 5 save |
| 8 | 4:10–5:00 | 50 min | Full Lane 1 tuning + recap | 10 min | 35 min + 5 recap |

### Day 2

| Block | Time | Duration | Topic | Teach | Try |
|-------|------|----------|-------|-------|-----|
| 9 | 10:00–10:20 | 20 min | Warm-up: re-test Lane 1 | 3 min | 17 min |
| 10 | 10:20–10:55 | 35 min | Hill + Bumper (Lane 2) | 12 min | 23 min |
| 11 | 10:55–11:45 | 50 min | Traffic light (Lane 2) | 15 min | 35 min |
| 12 | 11:45–12:20 | 35 min | State machine + forced states | 12 min | 20 min + 3 save |
| 13 | 12:20–1:00 | 40 min | Boom gate + roundabout (Track 3) | 12 min | 25 min + 3 save |
| — | 1:00–2:30 | 90 min | LUNCH | — | — |
| 14 | 2:30–3:25 | 55 min | Record & playback parking (Track 3) | 15 min | 35 min + 5 save |
| 15 | 3:25–4:00 | 35 min | Obstruction avoidance (Track 3) | 12 min | 20 min + 3 save |
| 16 | 4:00–4:50 | 50 min | Lane-by-lane testing runs (all 3) | 5 min | 45 min |
| 17 | 4:50–5:00 | 10 min | Competition prep + wrap-up | 10 min | — |

---

## 📊 Quick Reference — Key Files

| What | File |
|------|------|
| Competition challenges | [challenges_breakdown.md](file:///c:/Users/Lenovo/Downloads/Kerja/RISA-bot-1/Guide/challenges_breakdown.md) |
| Full tuning guide | [tuning_guide.md](file:///c:/Users/Lenovo/Downloads/Kerja/RISA-bot-1/Guide/tuning_guide.md) |
| All ROS commands | [commands_reference.md](file:///c:/Users/Lenovo/Downloads/Kerja/RISA-bot-1/Guide/commands_reference.md) |
| Architecture & node graph | [ARCHITECTURE.md](file:///c:/Users/Lenovo/Downloads/Kerja/RISA-bot-1/ARCHITECTURE.md) |
| All tunable parameters | [params.yaml](file:///c:/Users/Lenovo/Downloads/Kerja/RISA-bot-1/src/risabot_automode/config/params.yaml) |
| Launch file (full system) | [bringup.launch.py](file:///c:/Users/Lenovo/Downloads/Kerja/RISA-bot-1/src/risabot_automode/launch/bringup.launch.py) |
| Lane following code | [line_follower_camera.py](file:///c:/Users/Lenovo/Downloads/Kerja/RISA-bot-1/src/risabot_automode/risabot_automode/line_follower_camera.py) |
| Tunnel wall follower | [tunnel_wall_follower.py](file:///c:/Users/Lenovo/Downloads/Kerja/RISA-bot-1/src/risabot_automode/risabot_automode/tunnel_wall_follower.py) |
| State machine (brain) | [auto_driver.py](file:///c:/Users/Lenovo/Downloads/Kerja/RISA-bot-1/src/risabot_automode/risabot_automode/auto_driver.py) |

---

## 🧰 Pre-Workshop Checklist

- [ ] All robots on latest `main` branch, `tools/install.sh` completed
- [ ] All robots on workshop WiFi — IP addresses noted on each robot
- [ ] Batteries fully charged + spares available
- [ ] **Lane 1:** lane track + tunnel walls set up
- [ ] **Lane 2:** lane track + hill ramp + bumper + traffic light set up
- [ ] **Track 3:** roundabout + boom gate + parking slot + obstacle block set up
- [ ] Joystick controllers charged and paired to robots
- [ ] Dashboard accessible from participant laptops (`http://<ip>:8080`)
- [ ] Tuning cheat sheet printed — one per team
- [ ] Colored cards (red, green, yellow) for traffic light testing
