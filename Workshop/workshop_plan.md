# RISA-bot Competition Workshop — 2-Day Plan

---

## At a Glance

| | Detail |
|---|---|
| **Participants** | 21 people — 7 groups × 3 per group |
| **Duration** | 2 days × 5.5 hours (10:00–13:00, 14:30–17:00) |
| **Teaching Style** | Instructor teaches + demonstrates → groups try while supervised |
| **Prerequisite** | Workshop 00 (Linux) and 01 (ROS basics) completed |

---

## Test Setup Layout

```
LANE 1                    LANE 2                    TRACK 3
┌──────────────────┐      ┌──────────────────┐      ┌──────────────────┐
│  Lane Following  │      │  Lane Following  │      │  Roundabout      │
│  Tunnel          │      │  Hill            │      │  Boom Gate       │
│                  │      │  Bumper          │      │  Parking         │
│                  │      │  Traffic Light   │      │  Obstruction     │
└──────────────────┘      └──────────────────┘      └──────────────────┘
  Groups rotate in          Groups rotate in          Groups rotate in
  2-per-slot turns          2-per-slot turns          2-per-slot turns
```

---

## Group Rotation Rule

Whenever a block requires the **physical track**, groups rotate in pairs through the course section. While waiting, groups stay at their station — reviewing code, adjusting parameters on the dashboard, or observing the active group.

```
Slot A → Groups 1, 2 on track    (others at station)
Slot B → Groups 3, 4 on track    (others at station)
Slot C → Groups 5, 6 on track    (others at station)
Slot D → Group  7   on track     (others at station, re-test open)
```

> Blocks that do NOT need the physical track (recap, competition overview, architecture,
> dashboard, state machine theory) — ALL 7 groups work simultaneously at their station.

---
---

# DAY 1

## Day 1 — Schedule Overview

| Time | Block | Topic | Where | Groups |
|------|-------|-------|-------|--------|
| 10:00–10:35 | 1 | ROS & Linux Recap | At Station | All 7 |
| 10:35–10:55 | 2 | RISA-bot Overview & Workshop Goals | At Station | All 7 |
| 10:55–11:35 | 3 | Architecture & Component Setup | At Station | All 7 |
| 11:35–12:05 | 4 | Dashboard Tour | At Station | All 7 |
| 12:05–13:00 | 5 | Lane Detection (Image Pipeline) | At Station | All 7 |
| 13:00–14:30 | — | **LUNCH BREAK** | — | — |
| 14:30–15:10 | 6 | PID Steering | Lane 1 | Rotate pairs |
| 15:10–16:10 | 7 | Tunnel Navigation (LiDAR) | Lane 1 | Rotate pairs |
| 16:10–17:00 | 8 | Full Lane 1 Tuning Run | Lane 1 | Rotate pairs |

---

## Block 1 — ROS & Linux Recap
`10:00 – 10:35 | 35 min | All 7 groups at their station`

**Instructor teaches (15 min)**
- SSH into robot: `ssh sunrise@<robot_ip>`
- Source workspace: `cd ~/risabotcar_ws && source install/setup.bash`
- Key ROS commands they will use all day:
  ```bash
  ros2 topic list
  ros2 topic echo /lane_error
  ros2 node list
  ros2 param get /auto_driver forward_speed
  ros2 param set /auto_driver forward_speed 0.15
  ```
- Launch system: `ros2 launch risabot_automode bringup.launch.py`
- Build aliases: `cb` = rebuild · `sos` = re-source

**Groups try (20 min)**

Each group SSHs in and runs through the commands above. Instructor walks the room.

```bash
ros2 launch risabot_automode bringup.launch.py

# Second SSH terminal:
ros2 topic list
ros2 topic echo /lane_error
ros2 node list
ros2 param get /auto_driver forward_speed
```

---

## Block 2 — RISA-bot Overview & Workshop Goals
`10:35 – 10:55 | 20 min | All 7 groups at their station`

**Instructor teaches (20 min)**

Set the context before diving into code:

- **Who we are:** We are the developers of RISA-bot — a demo robot built to prove that a competition-ready autonomous robot is achievable with ROS 2 on accessible hardware (RDK X5, standard camera, LiDAR).
- **What RISA-bot demonstrates:** Every challenge in the competition has been solved. Lane following, tunnel, traffic light, hill, boom gate, parking — RISA-bot handles all of them using a combination of camera, LiDAR, and IMU with a single state machine brain.
- **Why this workshop exists:** To show you *how* it works and give you hands-on experience applying the same techniques to your own robot.

**What we cover in these 2 days:**

| Day | Focus | Test Setup |
|-----|-------|------------|
| Day 1 AM | ROS recap, architecture, dashboard, lane detection | At station |
| Day 1 PM | PID steering, tunnel wall following | Lane 1 |
| Day 2 AM | Hill & bumper, traffic light, state machine, boom gate | Lane 2 + Track 3 |
| Day 2 PM | Parking (record & playback), obstruction, full testing runs | Track 3 + All |

**How RISA-bot approaches the competition — the core pattern:**
- One sensor + one algorithm per challenge
- `auto_driver` (the brain) monitors all sensors and switches to the right algorithm automatically
- Every algorithm is tunable at runtime — no rebuilding needed
- Lane following is the foundation — it runs on most of the course and the other algorithms layer on top

---

## Block 3 — Architecture & Component Setup
`11:05 – 11:40 | 35 min | All 7 groups at their station`

**Instructor teaches (20 min)**

Show the node graph. Explain the 3-layer structure:
```
Sensors  →  Perception  →  Brain  →  Motors
```

**How to set up a component on your own robot** — the pattern used in `bringup.launch.py`:
1. Find the hardware SDK (`src/YDLidar-SDK/`, `src/ros2_astra_camera/`)
2. Include its launch file with `IncludeLaunchDescription`
3. Add your node with a `Node(...)` entry
4. Load settings from `params.yaml` with `parameters=[params_file]`

**Startup timing in `bringup.launch.py`:**

| Delay | What starts | Why |
|-------|-------------|-----|
| 0 s | Camera, LiDAR, joystick, servo, dashboard | Hardware first |
| 3 s | Line follower, tunnel, traffic light, obstacle | Sensors must be ready |
| 5 s | `auto_driver` (brain) | All perception must be running |

Show `params.yaml` — one file holds ALL tunable settings for every node.

**Groups try (15 min)**

```bash
# On robot — read the files
cat ~/risabotcar_ws/src/RISA-bot/src/risabot_automode/launch/bringup.launch.py
cat ~/risabotcar_ws/src/RISA-bot/src/risabot_automode/config/params.yaml
```

Find these in `params.yaml`: `forward_speed`, `white_threshold`, `kp` under tunnel. Then change one live:
```bash
ros2 param set /auto_driver forward_speed 0.12
ros2 param get /auto_driver forward_speed    # confirm
ros2 param set /auto_driver forward_speed 0.15    # revert
```

---

## Block 4 — Dashboard Tour
`11:40 – 12:10 | 30 min | All 7 groups at their station`

**Instructor teaches (12 min)**

Open `http://<robot_ip>:8080` on projector. Walk through every panel:

| Panel | What it shows |
|-------|--------------|
| State display | Current robot state (MANUAL, LANE_FOLLOW, TUNNEL…) |
| Camera debug tabs | Lane Lines / Traffic Light / Obstacle / Signage overlays |
| Lane Lines overlay | Blue = left edge · Pink = right edge · Green = center · Purple = crop boundary |
| Sensor panel | Green/red status per sensor |
| LiDAR canvas | Live laser dots |
| Odometry | Distance and speed |
| Parameters drawer | Slide-out panel — Get/Set any parameter live |
| 💾 Save button | Writes current values back to `params.yaml` |

**Groups try (18 min)**

Each group on their own dashboard:
1. Switch through all camera debug tabs
2. Open Parameters drawer → change `forward_speed` to `0.20` → Set → verify in terminal
3. Change `white_threshold` to `50` → watch Lane Lines tab (everything goes bright — too sensitive)
4. Change `white_threshold` to `220` → nothing detected (too strict)
5. Revert both values → click **💾 Save**

---

## Block 5 — Lane Detection: Image Pipeline
`12:10 – 13:00 | 50 min | All 7 groups at their station`

**Instructor teaches (20 min)**

The camera processing pipeline:
```
Camera frame
  → Resize to 320×240
  → Crop bottom portion           ← crop_ratio_base
  → CLAHE contrast boost          ← handles uneven lighting
  → Threshold to black/white      ← white_threshold
  → Morphological cleanup         ← removes noise, fills gaps
  → Multi-scanline edge finding   ← detects left + right borders
  → Kalman filter smoothing       ← removes jitter
  → Publish /lane_error           ← one number: –1.0 (left) to +1.0 (right)
```

**Two key parameters:**

`crop_ratio_base` (default 0.55)
- Higher → robot sees further ahead (purple line lower on screen)
- Lower → robot sees only what's right in front (purple line higher)
- Too low: cuts corners · Too high: picks up wall/ceiling noise

`white_threshold` (default 100) — with `invert_binary: true`, pixels BELOW this = lane
- Lower → more sensitive (everything looks like lane)
- Higher → stricter (only very dark areas count)
- **Tune this first.** Clean detection is the foundation of everything.

**Groups try (25 min)**

Dashboard → **Lane Lines** tab. Robot can be at the station — no track needed yet.

```bash
# Tune crop_ratio_base — watch the purple line move
ros2 param set /line_follower_camera crop_ratio_base 0.3
ros2 param set /line_follower_camera crop_ratio_base 0.7
# → Find value where blue/pink dots track both lane edges cleanly

# Tune white_threshold — watch dot coverage change
ros2 param set /line_follower_camera white_threshold 50
ros2 param set /line_follower_camera white_threshold 220
# → Find value where ONLY lane borders light up

# Watch the error signal live
ros2 topic echo /lane_error
# Slide robot left → negative. Right → positive. Center → near 0.
```

Each group writes down their best `crop_ratio_base` and `white_threshold`. Save via 💾.

---

## 🍽️ LUNCH BREAK — 13:00 to 14:30

**Instructor tasks during break:**
- Confirm tunnel walls are set up on Lane 1
- Charge any low-battery robots
- Note which groups had detection trouble — check on them first after lunch

---

## Block 6 — PID Steering
`14:30 – 15:10 | 40 min | Lane 1 — rotate groups in pairs`

**Instructor teaches (12 min) — all groups listen**

```
lane_error  →  PID controller  →  steering command (angular.z)

steering = (Kp × error) + (Ki × total_past_error) + (Kd × rate_of_change)
```

| Param | Role | Too low | Too high |
|-------|------|---------|----------|
| `pid_kp` | Main steering strength | Barely turns on curves | Oscillates left–right |
| `pid_kd` | Damping — stops overshoot | Wobbles after turns | Sluggish and jerky |
| `pid_ki` | Corrects persistent drift | Slow to fix drift | Unstable |

Speed adapts automatically in corners — robot slows when `|error|` is large.

Safe starting values:
```bash
ros2 param set /auto_driver forward_speed 0.10
ros2 param set /auto_driver pid_kp 0.5
ros2 param set /auto_driver pid_kd 0.2
ros2 param set /auto_driver pid_ki 0.01
```

**Groups try (25 min) — Lane 1 rotation**

Groups rotate onto Lane 1 in pairs. Enable auto mode (Start button). Tune while running:

| What you see | What to change |
|-------------|----------------|
| Oscillates left–right | Lower `pid_kp` → 0.4, raise `pid_kd` → 0.3 |
| Not turning enough on curves | Raise `pid_kp` → 0.8 |
| Drifts to one side on straight | Raise `pid_ki` → 0.02 |
| Cuts corners | Raise `crop_ratio_base` → 0.5 |
| Working — want more speed | Increase `forward_speed` by 0.02 at a time |

**Rotation schedule:**

| Slot | Time | On Lane 1 | At station |
|------|------|-----------|------------|
| A | 14:42–14:55 | Groups 1, 2 | Groups 3, 4, 5, 6, 7 |
| B | 14:55–15:08 | Groups 3, 4 | All others |
| (wrap-up) | 15:08–15:10 | — | All save params via 💾 |

Groups 5, 6, 7 start their Lane 1 practice in Block 7 (Slot C onward).

---

## Block 7 — Tunnel Navigation
`15:10 – 16:10 | 60 min | Lane 1 — rotate groups in pairs`

**Instructor teaches (15 min) — all groups listen**

Why LiDAR for tunnels: camera needs visible lane lines — those disappear in darkness. LiDAR fires laser beams that work in any lighting.

Algorithm:
```
LiDAR scan
  → Convert to x, y coordinates
  → Classify: left wall (15°–120°) vs right wall (–120° to –15°)
  → Bin points by forward distance
  → Find centerline (midpoint between left and right at each depth)
  → PD control on two errors:
      lateral error  — how far off-center right now
      heading error  — which way the tunnel curves ahead
  → EMA smoothing → publish /tunnel_cmd_vel
```

Auto-switching: both walls seen for **3 consecutive frames** → `TUNNEL` mode. Walls gone for 3 frames → back to `LANE_FOLLOW`. (Hysteresis — prevents flickering.)

| Param | Default | Effect |
|-------|---------|--------|
| `kp` | 5.0 | Lateral centering strength |
| `kd` | 0.5 | Lateral damping |
| `kp_heading` | 1.0 | Curve anticipation |
| `forward_speed` | 0.12 | Speed in tunnel |
| `min_wall_points` | 5 | Points needed per wall |

**Groups try (40 min) — Lane 1 rotation with tunnel**

Each pair spends ~15 min on Lane 1 doing the full lane → tunnel → exit run. Remaining groups continue PID tuning on open floor or observe.

**Rotation schedule:**

| Slot | Time | On Lane 1 (tunnel run) | At station |
|------|------|------------------------|------------|
| A | 15:25–15:40 | Groups 1, 2 | All others |
| B | 15:40–15:55 | Groups 3, 4 | All others |
| C | 15:55–16:08 | Groups 5, 6 | All others |
| D | (carry to Block 8) | Group 7 | — |

While on Lane 1, groups verify detection first:
```bash
ros2 topic echo /tunnel_debug
# l = left dist · r = right dist · lat = lateral error · w = angular output
```
Then enable auto mode and drive through. Tune as needed:
```bash
# Oscillating in tunnel:
ros2 param set /tunnel_wall_follower kp 3.0
ros2 param set /tunnel_wall_follower kd 0.8
# Drifting to one side:
ros2 param set /tunnel_wall_follower target_center_dist 0.02
# Not detecting walls:
ros2 param set /tunnel_wall_follower min_wall_points 3
```

Observe the mode switch (two terminals):
```bash
ros2 topic echo /lane_error       # active outside tunnel
ros2 topic echo /tunnel_cmd_vel   # active inside tunnel
```

Save via 💾 when clean.

---

## Block 8 — Full Lane 1 Tuning Run
`16:10 – 17:00 | 50 min | Lane 1 — rotate groups in pairs`

**Instructor teaches (10 min) — all groups listen**

**Always tune in this order — never skip ahead:**
```
1. white_threshold    → clean detection first
2. crop_ratio_base    → right crop region
3. pid_kp / pid_kd    → stable steering
4. tunnel kp / kd     → stable wall following
5. forward_speed      → increase LAST, only when steering is stable
```

Quick cheat sheet:
```bash
ros2 param set /auto_driver forward_speed 0.15
ros2 param set /auto_driver pid_kp 0.8
ros2 param set /auto_driver pid_kd 0.20
ros2 param set /auto_driver min_turn_speed 0.4
ros2 param set /line_follower_camera white_threshold 100
ros2 param set /line_follower_camera crop_ratio_base 0.55
ros2 param set /tunnel_wall_follower kp 5.0
ros2 param set /tunnel_wall_follower kd 0.5
```

**Groups try (35 min) — full Lane 1 runs, rotate in pairs**

Goal: complete clean end-to-end run — lane section → tunnel → exit back to lane. Fix one parameter between each run.

| Slot | Time | On Lane 1 | At station |
|------|------|-----------|------------|
| A | 16:20–16:32 | Groups 1, 2 | All others |
| B | 16:32–16:44 | Groups 3, 4 | All others |
| C | 16:44–16:56 | Groups 5, 6, 7 | All others |

**Save all final params via 💾 before 17:00.**

Instructor quick-diagnose guide while supervising:

| Symptom | Likely cause |
|---------|-------------|
| Leaves lane on curves | `crop_ratio_base` too low or `pid_kp` too low |
| Oscillates on straights | `pid_kp` too high or `pid_kd` too low |
| Tunnel detection flickers | Lower `min_wall_points` or raise `tunnel_hysteresis_frames` |
| Robot drifts in tunnel | Adjust `target_center_dist` ± 0.02 |

Brief recap at 16:57 — preview what Day 2 covers.

---
---

# DAY 2

## Day 2 — Schedule Overview

| Time | Block | Topic | Where | Groups |
|------|-------|-------|-------|--------|
| 10:00–10:20 | 9 | Warm-Up: Re-Test Lane 1 | Lane 1 | All 7 (pairs) |
| 10:20–10:55 | 10 | Hill & Bumper | Lane 2 | Rotate pairs |
| 10:55–11:45 | 11 | Traffic Light | Lane 2 | Rotate pairs |
| 11:45–12:20 | 12 | State Machine & Forced States | At Station | All 7 |
| 12:20–13:00 | 13 | Boom Gate & Roundabout | Track 3 | Rotate pairs |
| 13:00–14:30 | — | **LUNCH BREAK** | — | — |
| 14:30–15:25 | 14 | Record & Playback — Parking | Track 3 | Rotate pairs |
| 15:25–16:00 | 15 | Obstruction Avoidance | Track 3 | Rotate pairs |
| 16:00–16:50 | 16 | Lane-by-Lane Testing Runs | All 3 | Split + rotate |
| 16:50–17:00 | 17 | Competition Prep & Wrap-Up | — | All 7 |

---

## Block 9 — Warm-Up: Re-Test Lane 1
`10:00 – 10:20 | 20 min | Lane 1 — rotate pairs`

**Instructor (3 min):** Params load from `params.yaml` on launch. Quick verify that yesterday's work is intact.

**Groups try (17 min):**
```bash
ros2 launch risabot_automode bringup.launch.py
ros2 param get /auto_driver pid_kp
ros2 param get /line_follower_camera white_threshold
```
Run one lane+tunnel pass. If lighting changed overnight, re-tune `white_threshold` before moving on — this teaches an important competition-day lesson.

| Slot | Time | On Lane 1 | At station |
|------|------|-----------|------------|
| A | 10:03–10:10 | Groups 1, 2, 3 | Groups 4, 5, 6, 7 |
| B | 10:10–10:18 | Groups 4, 5, 6, 7 | Groups 1, 2, 3 |

---

## Block 10 — Hill & Bumper
`10:20 – 10:55 | 35 min | Lane 2 — rotate pairs`

**Instructor teaches (12 min) — all groups listen**

**Hill:** Camera still sees lane lines on the ramp → lane following continues. The IMU measures pitch angle. When pitch exceeds `hill_pitch_threshold` (default 12°), `auto_driver` enters `HILL` state → boosts speed to `hill_drive_speed` (0.35 m/s) → drives straighter (`hill_steer_scale = 0.0`). After the crest, pitch drops → returns to `LANE_FOLLOW`.

**Bumper:** Robot drives over it. No detection, no state change. Lane following handles it. Only concern: enough speed not to stall.

```bash
ros2 param set /auto_driver hill_pitch_threshold 12.0   # degrees
ros2 param set /auto_driver hill_drive_speed 0.35       # m/s climbing speed
```

**Groups try (20 min) — Lane 2 rotation**

| Slot | Time | On Lane 2 | At station |
|------|------|-----------|------------|
| A | 10:32–10:43 | Groups 1, 2 | All others |
| B | 10:43–10:54 | Groups 3, 4 | All others |

Groups 5, 6, 7 move to Lane 2 at the start of Block 11.

On Lane 2, enable auto mode → let robot approach hill:
```bash
ros2 topic echo /imu/pitch    # watch angle
```
- Stalls on hill → raise `hill_drive_speed` to 0.40
- Hill mode triggers too early → raise `hill_pitch_threshold` to 15.0
- Hill mode triggers too late → lower to 10.0

---

## Block 11 — Traffic Light Detection
`10:55 – 11:45 | 50 min | Lane 2 — rotate pairs`

**Instructor teaches (15 min) — all groups listen**

```
Camera frame
  → Convert to HSV color space
  → Filter for Red hue ranges  (two ranges — wraps around 0°)
  → Filter for Yellow hue      (~20–35)
  → Filter for Green hue       (~40–85)
  → Count pixels per color
  → Publish /traffic_light_state  ("red" / "yellow" / "green" / "unknown")
```

> **Warning:** HSV thresholds are extremely sensitive to lighting.
> Always re-tune at the competition venue on the day.

When active in `auto_driver`: Red/Yellow → robot stops. Green → robot goes.

Key parameters:
```bash
ros2 param set /traffic_light_detector sat_min 80         # minimum saturation
ros2 param set /traffic_light_detector val_min 80         # minimum brightness
ros2 param set /traffic_light_detector min_pixel_count 50 # noise filter
ros2 param set /traffic_light_detector required_confidence 3  # frames to confirm
```

**Groups try (30 min) — Lane 2 rotation**

| Slot | Time | On Lane 2 | At station |
|------|------|-----------|------------|
| A | 11:10–11:22 | Groups 1, 2 | All others |
| B | 11:22–11:34 | Groups 3, 4 | All others |
| C | 11:34–11:44 | Groups 5, 6, 7 | All others |

Step 1 — Isolated test using colored cards:
```bash
ros2 topic pub --once /set_challenge std_msgs/String "data: TRAFFIC_LIGHT"
ros2 topic echo /traffic_light_state
```
Hold red card → should read `"red"`. Green → `"green"`. Yellow → `"yellow"`.

Step 2 — Fix if not detecting:
```bash
ros2 param set /traffic_light_detector sat_min 50
ros2 param set /traffic_light_detector val_min 50
# False positives:
ros2 param set /traffic_light_detector min_pixel_count 100
```

Step 3 — Integrated test on Lane 2: robot drives → stops on red → goes on green.

Save via 💾 when working.

---

## Block 12 — State Machine & Testing Challenges in Isolation
`11:45 – 12:20 | 35 min | At Station — all 7 groups simultaneously`

**Instructor teaches (12 min)**

Priority table — the brain picks the highest active priority:

| Priority | State | What triggers it |
|----------|-------|-----------------|
| 1 | MANUAL | Joystick Start button |
| 4 | OBSTRUCTION | LiDAR detects lateral obstacle |
| 7 | TUNNEL | Walls on both sides for 3 frames |
| 9 | TRAFFIC_LIGHT | Red/yellow detected (when armed) |
| 9.5 | HILL | IMU pitch exceeds threshold |
| 11 | LANE_FOLLOW | Default state — always active |

Lap tracking: `current_lap` 1 or 2. Some challenges only arm on a specific lap.

Distance/time transitions — when the state machine auto-advances:
```bash
ros2 param set /auto_driver t_roundabout_sec 8.0
ros2 param set /auto_driver dist_boom_gate_1_pass 0.5
```

**The most important competition-day debugging tool:**
```bash
ros2 topic pub --once /set_challenge std_msgs/String "data: TUNNEL"
ros2 topic pub --once /set_challenge std_msgs/String "data: TRAFFIC_LIGHT"
ros2 topic pub --once /set_challenge std_msgs/String "data: OBSTRUCTION"
ros2 topic pub --once /set_challenge std_msgs/String "data: LANE_FOLLOW"
```
Force any state directly to test that challenge in isolation without running the full course.

**Groups try (20 min) — at station, all 7 simultaneously**

All groups force each state and observe the dashboard:
```bash
ros2 topic pub --once /set_challenge std_msgs/String "data: TUNNEL"
# → Dashboard shows TUNNEL, robot uses LiDAR

ros2 topic pub --once /set_challenge std_msgs/String "data: TRAFFIC_LIGHT"
# → Robot stops, waits for green

ros2 topic pub --once /set_challenge std_msgs/String "data: HILL"
# → Robot boosts speed

ros2 topic pub --once /set_challenge std_msgs/String "data: LANE_FOLLOW"
# → Returns to camera lane following
```

---

## Block 13 — Boom Gate & Roundabout
`12:20 – 13:00 | 40 min | Track 3 — rotate pairs`

**Instructor teaches (12 min) — all groups listen**

**Boom Gate:**
- LiDAR checks a narrow forward arc (±20°, range 0.1–0.8 m)
- Dense cluster of points at similar distances (low variance) = horizontal bar = CLOSED
- Hysteresis: must see OPEN for 3 frames before publishing `True`
- Two gates: Gate 1 (open Lap 1, closed Lap 2), Gate 2 (random)

```bash
ros2 param set /boom_gate_detector min_gate_points 5
ros2 param set /boom_gate_detector distance_variance_max 0.05
```

**Roundabout:**
- Normal lane following — roundabout has painted lines
- `ROUNDABOUT` state uses `t_roundabout_sec` timer to know when to exit
- On Lap 2, Gate 1 is closed → robot takes parking path instead

**Groups try (25 min) — Track 3 rotation**

| Slot | Time | On Track 3 | At station |
|------|------|-----------|------------|
| A | 12:32–12:43 | Groups 1, 2 | All others |
| B | 12:43–12:54 | Groups 3, 4 | All others |

Groups 5, 6, 7 move to Track 3 at the start of Block 14.

Boom gate test:
```bash
ros2 topic pub --once /set_challenge std_msgs/String "data: BOOM_GATE_2"
ros2 topic echo /boom_gate_open
```
Hold stick horizontally in front → `False` (closed). Remove → `True` (open).

Roundabout: Place robot at entrance → auto mode → drives through. Adjust `t_roundabout_sec` if exits too early/late.

---

## 🍽️ LUNCH BREAK — 13:00 to 14:30

**Instructor tasks during break:**
- Set up parking slot on Track 3 if not already done
- Charge ALL robots fully — critical for recording accuracy
- Print tuning cheat sheet for any group that doesn't have one

---

## Block 14 — Record & Playback — Parking
`14:30 – 15:25 | 55 min | Track 3 — rotate pairs`

**Instructor teaches (15 min) — all groups listen**

Why record & playback: reactive sensors are unreliable for precise parking. Open-loop recording at 20 Hz is repeatable when conditions are consistent.

**The interface:**

| Button | Action |
|--------|--------|
| Button A | Start recording |
| Button A again | Stop recording |
| Button B | Save to `~/recorded_movement.json` |
| Button X | Play back recording |

Same commands via terminal:
```bash
ros2 topic pub --once /record_playback_cmd std_msgs/String "{data: 'record'}"
ros2 topic pub --once /record_playback_cmd std_msgs/String "{data: 'stop'}"
ros2 topic pub --once /record_playback_cmd std_msgs/String "{data: 'save'}"
ros2 topic pub --once /record_playback_cmd std_msgs/String "{data: 'playback'}"
```

**What affects accuracy:**
- 🔋 Battery level — low battery = slower playback than recorded. **Charge fully.**
- 🏗️ Surface — must be the same surface type as competition
- 🎮 Input quality — slow, smooth joystick = cleaner recording
- ⏱️ `parking_idle_duration` — settling time before playback starts (default 2.0 s):
  ```bash
  ros2 param set /auto_driver parking_idle_duration 2.5
  ```

**Groups try (35 min) — Track 3 rotation**

| Slot | Time | On Track 3 | At station |
|------|------|-----------|------------|
| A | 14:45–14:57 | Groups 1, 2 | All others |
| B | 14:57–15:09 | Groups 3, 4 | All others |
| C | 15:09–15:21 | Groups 5, 6, 7 | All others |

On Track 3, each group:

1. Position robot next to parking slot
2. Press **Button A** → terminal: `🔴 RECORDING started`
3. Drive slowly and smoothly into the slot
4. Press **Button A** → `⏹ RECORDING stopped`
5. Press **Button B** → `Saved X movement samples`
6. Return to starting position
7. Press **Button X** → watch robot replay
8. Not accurate? Re-record. Iterate until 3 consecutive plays land in slot.

---

## Block 15 — Obstruction Avoidance
`15:25 – 16:00 | 35 min | Track 3 — rotate pairs`

**Instructor teaches (12 min) — all groups listen**

The detect → timed maneuver → resume pattern:
```
LiDAR detects object in lane < detect_dist
  → Check: left or right has more clearance?
  → Phase 1: Steer away          (steer_away_duration)
  → Phase 2: Drive alongside     (pass_duration)
  → Phase 3: Steer back          (steer_back_duration)
  → Resume lane following
```

```bash
ros2 param set /obstruction_avoidance detect_dist 0.50
ros2 param set /obstruction_avoidance steer_angular 0.6
ros2 param set /obstruction_avoidance pass_duration 2.0
ros2 param set /obstruction_avoidance steer_back_duration 1.5
```

**Groups try (20 min) — Track 3 rotation**

| Slot | Time | On Track 3 | At station |
|------|------|-----------|------------|
| A | 15:37–15:48 | Groups 1, 2, 3 | All others |
| B | 15:48–15:58 | Groups 4, 5, 6, 7 | All others |

Place obstacle block in lane. Force state and enable auto:
```bash
ros2 topic pub --once /set_challenge std_msgs/String "data: OBSTRUCTION"
```

| Problem | Fix |
|---------|-----|
| Doesn't detect early enough | Raise `detect_dist` → 0.65 |
| Clips obstacle while passing | Raise `pass_duration` → 2.5 |
| Overshoots back to lane | Lower `steer_back_duration` → 1.0 |
| Doesn't steer wide enough | Raise `steer_angular` → 0.8 |

Save via 💾 when clean.

---

## Block 16 — Lane-by-Lane Testing Runs
`16:00 – 16:50 | 50 min | All 3 setups open`

**Instructor (5 min):** All setups are now open. Groups spread across all 3 and run end-to-end. Fix what breaks. Save when clean.

**Group assignment — initial split:**

| Setup | Groups | Focus |
|-------|--------|-------|
| Lane 1 | Groups 1, 2, 3 | Lane follow → tunnel → exit |
| Lane 2 | Groups 4, 5 | Lane follow → hill → bumper → traffic light |
| Track 3 | Groups 6, 7 | Roundabout → boom gate → parking playback |

**16:00–16:25 (25 min): First rotation**

Each group runs their assigned setup. Notes:
- Start in auto mode each time
- One parameter change per run
- Save when a run is clean

**16:25–16:48 (23 min): Second rotation**

Groups swap to the next setup (if time and resources allow):

| Setup | Groups |
|-------|--------|
| Lane 1 | Groups 3, 4 |
| Lane 2 | Groups 1, 6 |
| Track 3 | Groups 2, 5, 7 |

Instructor rotates between setups actively — this is the most hands-on supervision block.

---

## Block 17 — Competition Prep & Wrap-Up
`16:50 – 17:00 | 10 min | All groups`

**Instructor (10 min) — display on projector:**

**Competition Day Checklist:**

| # | What to do |
|---|-----------|
| 1 | Re-tune `white_threshold` and HSV ranges at the venue — lighting is different everywhere |
| 2 | Charge batteries fully before recording and before every competition run |
| 3 | Save params before experimenting — use 💾 button every time something works |
| 4 | Use `/set_challenge` to test each challenge individually before full runs |
| 5 | Keep `forward_speed` conservative — finishing matters more than speed |
| 6 | If detection breaks — fix `white_threshold` before touching anything else |
| 7 | Re-record parking if the competition floor surface is different from practice |
| 8 | Always tune in order — detection → steering → speed |

**Reference guides (in the repo):**
- `Guide/tuning_guide.md` — full symptom → fix reference
- `Guide/commands_reference.md` — all ROS topics and commands
- `Guide/challenges_breakdown.md` — code-level explanation of each challenge

---

## Quick Reference — Key Parameters

| Parameter | Node | Default | What it does |
|-----------|------|---------|-------------|
| `forward_speed` | auto_driver | 0.15 | Base driving speed (m/s) |
| `pid_kp` | auto_driver | 0.8 | Steering strength |
| `pid_kd` | auto_driver | 0.20 | Steering damping |
| `pid_ki` | auto_driver | 0.01 | Drift correction |
| `white_threshold` | line_follower_camera | 100 | Lane detection sensitivity |
| `crop_ratio_base` | line_follower_camera | 0.55 | How far ahead robot looks |
| `kp` | tunnel_wall_follower | 5.0 | Tunnel centering strength |
| `kd` | tunnel_wall_follower | 0.5 | Tunnel damping |
| `forward_speed` | tunnel_wall_follower | 0.12 | Speed inside tunnel |
| `hill_pitch_threshold` | auto_driver | 12.0 | Degrees of incline to trigger hill mode |
| `hill_drive_speed` | auto_driver | 0.35 | Climbing speed |
| `detect_dist` | obstruction_avoidance | 0.50 | How far ahead to detect obstacle |
| `parking_idle_duration` | auto_driver | 2.0 | Settle time before parking playback |

---

## Pre-Workshop Checklist

- [ ] All 7 robots on latest branch, `tools/install.sh` completed
- [ ] All 7 robots connected to workshop WiFi — IP on sticky note on each robot
- [ ] Batteries fully charged + spares on hand
- [ ] Joystick controllers charged and paired (one per group)
- [ ] Dashboard accessible from each group's laptop (`http://<ip>:8080`)
- [ ] **Lane 1:** lane track + tunnel walls assembled
- [ ] **Lane 2:** lane track + hill ramp + bumper + traffic light assembled
- [ ] **Track 3:** roundabout + boom gate + parking slot + obstacle block assembled
- [ ] Tuning cheat sheet printed — one per group (7 copies)
- [ ] Colored cards (red, green, yellow) for traffic light testing — one set per group
