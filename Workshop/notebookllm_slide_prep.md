# NotebookLM Slide Generation — RISA-bot Workshop

---

## Step 1: Upload These Sources to NotebookLM

Upload files **in this order** (most important first). All files are in your RISA-bot repo.

| Priority | File | Path in repo | Why |
|----------|------|--------------|-----|
| ⭐ 1 | workshop_plan.md | `Workshop/workshop_plan.md` | Master schedule + full block content |
| ⭐ 2 | ARCHITECTURE.md | `ARCHITECTURE.md` | Node graph + system overview |
| ⭐ 3 | challenges_breakdown.md | `Guide/challenges_breakdown.md` | Per-challenge code logic |
| ⭐ 4 | tuning_guide.md | `Guide/tuning_guide.md` | Full tuning reference |
| 5 | 04-lane-follower.md | `Workshop/04-lane-follower.md` | Lane detection deep-dive |
| 6 | 05-tunnel-navigation.md | `Workshop/05-tunnel-navigation.md` | Tunnel wall follower deep-dive |
| 7 | 06-autonomous-parking.md | `Workshop/06-autonomous-parking.md` | Record & playback parking |
| 8 | 02-dashboard-and-sensors.md | `Workshop/02-dashboard-and-sensors.md` | Dashboard walkthrough |
| 9 | 03-putting-it-together.md | `Workshop/03-putting-it-together.md` | Full system integration |
| 10 | 07-computer-vision.md | `Workshop/07-computer-vision.md` | Traffic light + signage detection |
| 11 | commands_reference.md | `Guide/commands_reference.md` | All ROS CLI commands |

> Upload all 11 files. The first 4 are critical — the rest add depth for specific sessions.

---

## Step 2: Set the Master Context (Paste This First)

Before generating any slides, paste this into NotebookLM chat:

---

```
CONTEXT FOR ALL SLIDE GENERATION:

You are helping create instructor presentation slides for a 2-day robotics competition workshop on RISA-bot — a ROS 2 demo robot that proves a competition-ready autonomous robot is achievable.

INSTRUCTOR ROLE:
We are the developers of RISA-bot. Participants already know the competition. Our job is to explain how RISA-bot solves each competition challenge and let them try it hands-on.

PARTICIPANTS:
- 21 people, 7 groups of 3
- Already completed Linux + ROS 2 basics (Workshop 00 and 01)
- Each group has their own RISA-bot robot

TEACHING METHOD:
Every block follows: Instructor teaches + demonstrates (10–20 min) → Participants try while supervised (15–35 min)

SLIDE RULES — apply to every deck you generate:
1. Dark background preferred (technical audience)
2. Maximum 5 bullet points per slide — instructor talks around them
3. One concept per slide. Do not combine unrelated ideas.
4. Code snippets go on their own slide or in a clearly separated box
5. Use [DIAGRAM: description] notation where a visual diagram would help
6. Every deck ends with a "🔧 TRY IT" slide listing exactly what participants do
7. Do not add quiz slides, discussion slides, or "check your understanding" slides
8. Slide count guideline: ~1 slide per 2 minutes of teaching content

SESSION STRUCTURE PER DECK:
- Slide 1: Block title + time + "All groups" or "Rotate pairs on [lane/track]"
- Slides 2–N: Teaching content
- Last slide: 🔧 TRY IT — exact commands and steps for hands-on time
```

---

## Step 3: Per-Session Prompts

Use one prompt per block. Copy, paste, send — then download or copy the output.

---

### DAY 1

---

#### Block 1 — ROS & Linux Recap
```
Generate a slide deck for Block 1 of the RISA-bot workshop.

Block 1: ROS & Linux Recap
Time: 10:00–10:35 (35 min) | All 7 groups at their station

Teaching content to cover:
- SSH into robot: ssh sunrise@<robot_ip>
- Sourcing the workspace: cd ~/risabotcar_ws && source install/setup.bash
- Key ROS 2 commands: ros2 topic list, ros2 topic echo, ros2 node list, ros2 param get, ros2 param set
- Launching the full system: ros2 launch risabot_automode bringup.launch.py
- Build aliases: cb = rebuild, sos = re-source

TRY section: participants SSH in and run each command in a second terminal while the system is running. Commands to include: topic list, echo /lane_error, node list, param get /auto_driver forward_speed

Format: 6–8 slides. Include a code slide for each command group.
```

---

#### Block 2 — RISA-bot Overview & Workshop Goals
```
Generate a slide deck for Block 2 of the RISA-bot workshop.

Block 2: RISA-bot Overview & Workshop Goals
Time: 10:35–10:55 (20 min) | All 7 groups at their station

Teaching content to cover:
- Who we are: developers of RISA-bot, a demo robot proving competition-ready autonomy is achievable on RDK X5, standard camera and LiDAR
- What RISA-bot demonstrates: all competition challenges solved — lane following, tunnel, traffic light, hill, boom gate, parking — using a single state machine brain
- Why this workshop: show HOW it works and give hands-on experience with the same techniques
- The core pattern: one sensor + one algorithm per challenge, auto_driver switches automatically, all tunable at runtime without rebuilding
- What the 2 days cover: Day 1 (architecture, dashboard, lane detection, PID, tunnel), Day 2 (hill, bumper, traffic light, state machine, boom gate, parking, obstruction)

No TRY section for this block — it is fully instructor-led.

Format: 5–6 slides. Include a high-level architecture overview diagram description. Keep it concise and visual.
```

---

#### Block 3 — Architecture & Component Setup
```
Generate a slide deck for Block 3 of the RISA-bot workshop.

Block 3: Architecture & Component Setup
Time: 10:55–11:35 (40 min) | All 7 groups at their station

Teaching content to cover:
- The 3-layer structure: Sensors → Perception → Brain → Motors
- What each layer contains:
  - Sensors: Camera (Astra), LiDAR (YDLidar), Joystick, IMU
  - Perception: line_follower_camera, tunnel_wall_follower, traffic_light_detector, boom_gate_detector, obstacle_avoidance, signage_detector
  - Brain: auto_driver → cmd_safety_controller → servo_controller → Motors
- How to set up a component (the pattern used in bringup.launch.py):
  Step 1: Find the hardware SDK (e.g. src/YDLidar-SDK/, src/ros2_astra_camera/)
  Step 2: Include its launch file with IncludeLaunchDescription
  Step 3: Add your node with a Node(...) entry
  Step 4: Load settings from params.yaml using parameters=[params_file]
- Startup timing: 0s = hardware, 3s = perception nodes, 5s = auto_driver brain
- params.yaml: one file controls ALL tunable settings for every node

TRY section:
- cat the launch file and params.yaml on robot
- Find forward_speed, white_threshold, kp/kd for tunnel in params.yaml
- Change forward_speed live: ros2 param set /auto_driver forward_speed 0.12, then verify, then revert

Format: 8–10 slides. Include a diagram slide for the node graph. Include a code slide for the launch file pattern and one for params.yaml structure.
```

---

#### Block 4 — Dashboard Tour
```
Generate a slide deck for Block 4 of the RISA-bot workshop.

Block 4: Dashboard Tour
Time: 11:35–12:05 (30 min) | All 7 groups at their station

Teaching content to cover:
- Dashboard URL: http://<robot_ip>:8080
- Panel by panel tour:
  - State display: shows current state (MANUAL, LANE_FOLLOW, TUNNEL, etc.)
  - Camera debug tabs: Lane Lines / Traffic Light / Obstacle / Signage
  - Lane Lines overlay: blue = left edge, pink = right edge, green = center, purple = crop boundary
  - Sensor panel: green/red status for each sensor
  - LiDAR canvas: real-time laser dots
  - Odometry: distance and speed readout
  - Parameters drawer (slide-out): Get and Set any parameter live, no restart needed
  - Save button (💾): writes all current values back to params.yaml permanently

TRY section:
1. Switch through all camera debug tabs — observe each view
2. Open Parameters drawer → find forward_speed → change to 0.20 → Set → verify in terminal
3. Change white_threshold to 50 → watch Lane Lines tab (too sensitive)
4. Change white_threshold to 220 → watch Lane Lines tab (nothing detected)
5. Revert both values → click 💾 Save

Format: 7–9 slides. One slide per dashboard panel. Include screenshot placeholder annotations like [SCREENSHOT: Lane Lines debug view showing blue/pink/green dots].
```

---

#### Block 5 — Lane Detection: Image Pipeline
```
Generate a slide deck for Block 5 of the RISA-bot workshop.

Block 5: Lane Detection — Image Processing Pipeline
Time: 12:05–13:00 (55 min) | All 7 groups at their station

Teaching content to cover:
- The full camera pipeline (one slide per step):
  1. Resize to 320×240
  2. Crop bottom portion — controlled by crop_ratio_base
  3. CLAHE contrast enhancement — compensates uneven lighting
  4. Threshold to binary — controlled by white_threshold (with invert_binary=true, pixels BELOW threshold = lane)
  5. Morphological cleanup — removes noise, fills gaps
  6. Multi-scanline edge detection — finds left and right borders across 8 horizontal rows
  7. Kalman filter smoothing — removes jitter
  8. Publishes /lane_error — single value: -1.0 (hard left) to +1.0 (hard right)

- crop_ratio_base explained:
  Higher = robot looks further ahead (purple line lower)
  Lower = robot sees only what is right in front (purple line higher)
  Too low: cuts corners on curves
  Too high: picks up wall/ceiling noise

- white_threshold explained:
  Lower = more sensitive (everything looks like lane)
  Higher = stricter (only very dark areas count)
  Always tune this FIRST — clean detection is the foundation of everything

TRY section (on Lane 1 or Lane 2 — robot at station, dashboard Lane Lines tab open):
- Tune crop_ratio_base: try 0.3 then 0.7, find best value
  ros2 param set /line_follower_camera crop_ratio_base 0.3
- Tune white_threshold: try 50 then 220, find best value
  ros2 param set /line_follower_camera white_threshold 50
- Watch /lane_error live:
  ros2 topic echo /lane_error
- Write down best values. Save via 💾.

Format: 10–12 slides. One slide per pipeline step with a [DIAGRAM] annotation. Two dedicated parameter explanation slides. End with TRY IT slide listing exact commands.
```

---

#### Block 6 — PID Steering
```
Generate a slide deck for Block 6 of the RISA-bot workshop.

Block 6: PID Steering — How the Robot Turns
Time: 14:30–15:10 (40 min) | Lane 1 — rotate pairs of groups

Teaching content to cover:
- The steering equation: steering = (Kp × error) + (Ki × total_past_error) + (Kd × rate_of_change)
- Explanation of each term in plain language:
  - pid_kp: main steering strength. Too low = barely turns. Too high = oscillates.
  - pid_kd: damping — prevents overshooting. Too low = wobbles after turns. Too high = sluggish.
  - pid_ki: corrects persistent drift to one side. Keep small (0.01–0.02).
- Adaptive speed: robot automatically slows in sharp turns using min_turn_speed
  speed_multiplier = max(min_turn_speed, 1.0 - speed_error_scale × |error|)
- Safe starting values: forward_speed=0.10, pid_kp=0.5, pid_kd=0.2, pid_ki=0.01
- Symptom → Fix table:
  Oscillates left-right: lower pid_kp to 0.4, raise pid_kd to 0.3
  Not turning enough on curves: raise pid_kp to 0.8
  Drifts to one side: raise pid_ki to 0.02
  Cuts corners: raise crop_ratio_base to 0.5
  Working — want more speed: increase forward_speed by 0.02 increments

TRY section (on Lane 1, groups rotate in pairs):
- Set starting params via CLI or dashboard
- Enable auto mode (Start button on joystick)
- Observe behaviour, apply symptom→fix table
- Increase forward_speed gradually once steering is stable
- Save via 💾 when stable

Rotation note on slide: Groups 1,2 → Groups 3,4 → Groups 5,6 → Group 7

Format: 8–10 slides. Include a dedicated symptom/fix table slide. Include a code slide with starting values.
```

---

#### Block 7 — Tunnel Navigation
```
Generate a slide deck for Block 7 of the RISA-bot workshop.

Block 7: Tunnel Navigation — LiDAR Wall Following
Time: 15:10–16:10 (60 min) | Lane 1 — rotate pairs of groups

Teaching content to cover:
- Why LiDAR for tunnels: camera needs visible lane lines — fails in darkness. LiDAR fires lasers that work in any lighting.
- The algorithm pipeline:
  1. LiDAR scan → convert polar (angle, distance) to Cartesian (x, y)
  2. Classify points: left wall = 15° to 120°, right wall = -120° to -15°
  3. Bin wall points by forward distance
  4. Compute centerline: midpoint between left and right at each depth
  5. Two PD error signals: lateral error (how far off-center) and heading error (which way tunnel curves)
  6. EMA smoothing → publish /tunnel_cmd_vel
- Why two error signals are better than one: lateral corrects position, heading anticipates curves before they happen
- Auto-switching (hysteresis):
  Both walls detected for 3 consecutive frames → TUNNEL mode (uses /tunnel_cmd_vel)
  Walls absent for 3 frames → back to LANE_FOLLOW (uses /lane_error)
  3-frame requirement prevents flickering at tunnel entrance/exit
- Key parameters: kp (5.0), kd (0.5), kp_heading (1.0), forward_speed (0.12), min_wall_points (5)
- Tuning symptom → fix:
  Oscillating between walls: lower kp to 3.0, raise kd to 0.8
  Drifting to one side: adjust target_center_dist ± 0.02
  Not detecting walls: lower min_wall_points to 3
  Too fast: lower forward_speed to 0.10

TRY section (on Lane 1 tunnel, groups rotate in pairs):
Step 1 — Verify detection:
  ros2 topic echo /tunnel_debug   (l = left dist, r = right dist, lat = lateral error)
  Watch dashboard Sensor panel → should show IN TUNNEL
Step 2 — Drive through:
  Enable auto mode → drives into tunnel → auto-switches → exits back to lane following
  Apply symptom/fix table as needed
Step 3 — Observe the switch (two terminals):
  ros2 topic echo /lane_error        (active outside tunnel)
  ros2 topic echo /tunnel_cmd_vel    (active inside tunnel)
Save via 💾 when clean.

Format: 10–12 slides. Include a diagram slide for the angle classification (left/right wall sectors). Include a mode-switching diagram slide.
```

---

#### Block 8 — Full Lane 1 Tuning Run
```
Generate a slide deck for Block 8 of the RISA-bot workshop.

Block 8: Full Lane 1 Tuning Run
Time: 16:10–17:00 (50 min) | Lane 1 — rotate pairs of groups

Teaching content to cover:
- The tuning order — must always follow this sequence:
  1. white_threshold → clean detection first
  2. crop_ratio_base → correct crop region
  3. pid_kp / pid_kd → stable steering (no oscillation)
  4. tunnel kp / kd → stable wall following
  5. forward_speed → increase LAST, only when steering is stable
- Why order matters: each step depends on the previous one being stable
- The 8 most common parameter commands (cheat sheet):
  ros2 param set /auto_driver forward_speed 0.15
  ros2 param set /auto_driver pid_kp 0.8
  ros2 param set /auto_driver pid_kd 0.20
  ros2 param set /auto_driver min_turn_speed 0.4
  ros2 param set /line_follower_camera white_threshold 100
  ros2 param set /line_follower_camera crop_ratio_base 0.55
  ros2 param set /tunnel_wall_follower kp 5.0
  ros2 param set /tunnel_wall_follower kd 0.5
- Instructor supervision guide (what to look for):
  Leaves lane on curves → crop_ratio_base too low or pid_kp too low
  Oscillates on straights → pid_kp too high or pid_kd too low
  Tunnel detection flickers → lower min_wall_points
  Drifts in tunnel → adjust target_center_dist

TRY section (full Lane 1 end-to-end runs, groups rotate in pairs):
- Run robot full lane → tunnel → exit back to lane
- Change ONE parameter between each run
- Save via 💾 once a clean run is achieved
- Rotation: Groups 1,2 → Groups 3,4 → Groups 5,6,7

Format: 6–8 slides. Include a cheat sheet code slide. Include a supervisor diagnosis table slide. End with TRY IT slide.
```

---

### DAY 2

---

#### Block 9 — Warm-Up: Re-Test Lane 1
```
Generate a slide deck for Block 9 of the RISA-bot workshop.

Block 9: Warm-Up — Re-Test Lane 1
Time: 10:00–10:20 (20 min) | Lane 1 — rotate pairs

Teaching content to cover:
- Parameters load from params.yaml on launch — yesterday's saved values should be intact
- Always verify before assuming: check key params after launch
- Lighting changes day to day → white_threshold may need adjusting even if params are saved
- This teaches a critical competition-day lesson: always verify detection at a new venue

TRY section:
- Launch system, verify params:
  ros2 param get /auto_driver pid_kp
  ros2 param get /line_follower_camera white_threshold
- Run one quick lane+tunnel pass
- If detection looks wrong: re-tune white_threshold first before anything else

Format: 4–5 slides. Keep brief — this is a warm-up block.
```

---

#### Block 10 — Hill & Bumper
```
Generate a slide deck for Block 10 of the RISA-bot workshop.

Block 10: Hill & Bumper
Time: 10:20–10:55 (35 min) | Lane 2 — rotate pairs

Teaching content to cover:
- Key insight: Hill and Bumper require NO new code. The existing lane follower handles them automatically.
- Hill behaviour:
  Camera still sees lane lines on the ramp surface → lane following continues
  IMU measures pitch angle → when pitch exceeds hill_pitch_threshold (default 12°) → HILL state
  In HILL state: speed boosted to hill_drive_speed (0.35 m/s), steering scaled toward straight (hill_steer_scale = 0.0)
  After the crest, pitch drops → auto-returns to LANE_FOLLOW
- Bumper behaviour:
  Physical bump that the robot drives over
  No detection, no state change needed
  Only concern: enough forward_speed to clear it without stalling
- Parameters:
  hill_pitch_threshold: 12.0 (degrees) — trigger angle
  hill_drive_speed: 0.35 (m/s) — climbing speed
- Design principle this demonstrates: reuse what you already have — don't over-engineer

TRY section (Lane 2, rotate pairs):
- Enable auto mode → drive toward hill
- Watch pitch: ros2 topic echo /imu/pitch
- Watch dashboard state change to HILL
- If stalls on hill: raise hill_drive_speed to 0.40
- If triggers too early: raise hill_pitch_threshold to 15.0
- If triggers too late: lower to 10.0
- Drive over bumper — should work with no changes

Format: 7–8 slides. Include a diagram of HILL state transition. Emphasise the "no new code" design principle.
```

---

#### Block 11 — Traffic Light Detection
```
Generate a slide deck for Block 11 of the RISA-bot workshop.

Block 11: Traffic Light Detection
Time: 10:55–11:45 (50 min) | Lane 2 — rotate pairs

Teaching content to cover:
- Algorithm:
  Camera frame → convert to HSV color space → filter for Red/Yellow/Green hue ranges → count pixels per color → publish /traffic_light_state
- HSV color space explained briefly:
  H (Hue) = the color, 0–180 in OpenCV
  S (Saturation) = how vivid the color is
  V (Value) = how bright it is
  Red wraps around 0° so it needs two hue ranges
- Approximate hue ranges: Red = 0–10 + 170–180, Yellow = 20–35, Green = 40–85
- In auto_driver: red/yellow → robot stops. Green → robot goes.
- CRITICAL WARNING: HSV thresholds are extremely sensitive to lighting. Values that work in one room fail in another. Always re-tune at the competition venue on the day.
- Key parameters: sat_min, val_min (lower = detects more), min_pixel_count (noise filter), required_confidence (frames to confirm)

TRY section (Lane 2, rotate pairs):
Step 1 — Isolated test with colored cards:
  Force state: ros2 topic pub --once /set_challenge std_msgs/String "data: TRAFFIC_LIGHT"
  Monitor: ros2 topic echo /traffic_light_state
  Hold red card → should read "red"
  Hold green card → should read "green"
  Hold yellow card → should read "yellow"
Step 2 — Fix if not detecting:
  ros2 param set /traffic_light_detector sat_min 50
  ros2 param set /traffic_light_detector val_min 50
Step 3 — Test integrated on Lane 2 (robot drives, stops on red, goes on green)
Save via 💾 when working.

Format: 9–11 slides. Include an HSV color wheel diagram description. Make the WARNING about lighting very prominent (red text / warning box).
```

---

#### Block 12 — State Machine & Forced State Testing
```
Generate a slide deck for Block 12 of the RISA-bot workshop.

Block 12: State Machine — The Robot's Brain
Time: 11:45–12:20 (35 min) | At station — all 7 groups simultaneously

Teaching content to cover:
- The state machine concept: auto_driver monitors all sensors and picks the highest-priority active state
- Priority table:
  Priority 1: MANUAL (joystick Start button)
  Priority 4: OBSTRUCTION (LiDAR detects lateral obstacle)
  Priority 7: TUNNEL (walls on both sides for 3 frames)
  Priority 9: TRAFFIC_LIGHT (red/yellow detected when armed)
  Priority 9.5: HILL (IMU pitch exceeds threshold)
  Priority 11: LANE_FOLLOW (default — always active)
- Lap tracking: current_lap = 1 or 2. Some challenges only arm on specific laps.
- Distance/time transitions — control when state machine auto-advances:
  t_roundabout_sec: time in roundabout
  dist_boom_gate_1_pass: distance after boom gate 1
- The most important competition-day debugging tool — force any state:
  ros2 topic pub --once /set_challenge std_msgs/String "data: TUNNEL"
  ros2 topic pub --once /set_challenge std_msgs/String "data: TRAFFIC_LIGHT"
  ros2 topic pub --once /set_challenge std_msgs/String "data: OBSTRUCTION"
  ros2 topic pub --once /set_challenge std_msgs/String "data: LANE_FOLLOW"
  Use this to test any challenge in isolation without running the full course

TRY section (at station, all 7 groups simultaneously):
- Force each state one by one
- For each state: observe dashboard state display and what robot does
- Try TUNNEL → see LiDAR take over
- Try TRAFFIC_LIGHT → robot stops
- Try LANE_FOLLOW → returns to camera

Format: 8–9 slides. Include a priority table slide. Include a flow diagram description for state switching. End with a prominent "competition day debugging" slide.
```

---

#### Block 13 — Boom Gate & Roundabout
```
Generate a slide deck for Block 13 of the RISA-bot workshop.

Block 13: Boom Gate & Roundabout
Time: 12:20–13:00 (40 min) | Track 3 — rotate pairs

Teaching content to cover:
- Boom Gate algorithm:
  LiDAR checks narrow forward arc (±20°, range 0.1–0.8m)
  If dense cluster of points at similar distances (low variance) → horizontal bar detected = CLOSED
  Must see OPEN for 3 consecutive frames before publishing True (hysteresis, same pattern as tunnel)
  Two gates: Gate 1 (open Lap 1, closed Lap 2), Gate 2 (random)
  Parameters: min_gate_points (5), distance_variance_max (0.05)
- Roundabout:
  Uses normal lane following — roundabout has painted lane lines
  auto_driver enters ROUNDABOUT state after obstruction section
  t_roundabout_sec timer controls how long robot follows before exiting
  On Lap 2 with Gate 1 closed → robot takes parking path instead

TRY section (Track 3, rotate pairs):
Boom gate test:
  ros2 topic pub --once /set_challenge std_msgs/String "data: BOOM_GATE_2"
  ros2 topic echo /boom_gate_open
  Hold horizontal stick in front → should read False (closed)
  Remove → should read True (open)
  If not detecting: ros2 param set /boom_gate_detector min_gate_points 3
Roundabout test:
  Place robot at roundabout entrance → enable auto mode → follows lane through
  Adjust t_roundabout_sec if exits too early or too late

Format: 7–8 slides. Include a diagram description showing the LiDAR forward arc detection zone.
```

---

#### Block 14 — Record & Playback — Parking
```
Generate a slide deck for Block 14 of the RISA-bot workshop.

Block 14: Record & Playback — Parking
Time: 14:30–15:25 (55 min) | Track 3 — rotate pairs

Teaching content to cover:
- Why record & playback: reactive sensors are unreliable for precise parking. Open-loop recording at 20Hz is repeatable when conditions are consistent.
- The recording interface (joystick buttons):
  Button A = Start recording (clears buffer)
  Button A again = Stop recording
  Button B = Save to ~/recorded_movement.json
  Button X = Play back recording
- Same commands via terminal:
  ros2 topic pub --once /record_playback_cmd std_msgs/String "{data: 'record'}"
  ros2 topic pub --once /record_playback_cmd std_msgs/String "{data: 'save'}"
  ros2 topic pub --once /record_playback_cmd std_msgs/String "{data: 'playback'}"
- Accuracy factors — all critical:
  Battery level: low battery = slower playback than recorded → charge fully
  Surface: must record on the same floor type as competition
  Input quality: slow smooth joystick = clean recording = clean playback
  parking_idle_duration: settling time before playback starts (default 2.0s)
    ros2 param set /auto_driver parking_idle_duration 2.5
- Signage trigger flow (auto mode Lap 2):
  signage_detector sees parking sign → PARKING_IDLE (stop + wait) → PARKING_PLAYBACK → FINISHED

TRY section (Track 3 parking slot, rotate pairs):
Step 1 — Record:
  Position robot at starting point
  Press Button A → RECORDING started
  Drive slowly and smoothly into slot
  Press Button A → RECORDING stopped
  Press Button B → Saved
Step 2 — Playback test:
  Return to exact start position
  Press Button X → robot replays
  Not accurate? Re-record. Iterate until 3 consecutive plays land in slot.
Step 3 — Test signage trigger (if time allows):
  ros2 param set /auto_driver current_lap 2
  Enable auto mode → robot drives → sees sign → parks

Format: 10–12 slides. Include a flow diagram slide for the signage trigger chain. Make accuracy factors prominent — especially battery warning.
```

---

#### Block 15 — Obstruction Avoidance
```
Generate a slide deck for Block 15 of the RISA-bot workshop.

Block 15: Obstruction Avoidance
Time: 15:25–16:00 (35 min) | Track 3 — rotate pairs

Teaching content to cover:
- The detect → timed maneuver → resume pattern:
  LiDAR detects object in lane closer than detect_dist
  Check which side (left or right) has more clearance
  Phase 1: Steer away from obstacle (steer_away_duration seconds)
  Phase 2: Drive straight alongside obstacle (pass_duration seconds)
  Phase 3: Steer back into lane (steer_back_duration seconds)
  Set active = False → auto_driver resumes lane following
- All timing is open-loop (same principle as parking recording)
- Key parameters:
  detect_dist: 0.50 (how far ahead to detect)
  steer_angular: 0.6 (how hard to steer away)
  pass_duration: 2.0 (time alongside obstacle)
  steer_back_duration: 1.5 (time returning to lane)
- Symptom → fix table:
  Doesn't detect early enough: raise detect_dist to 0.65
  Clips obstacle while passing: raise pass_duration to 2.5
  Overshoots return to lane: lower steer_back_duration to 1.0
  Doesn't steer wide enough: raise steer_angular to 0.8

TRY section (Track 3, rotate pairs):
- Place obstacle block in lane
- Force state: ros2 topic pub --once /set_challenge std_msgs/String "data: OBSTRUCTION"
- Enable auto mode → robot approaches and dodges
- Apply symptom/fix table as needed
- Save via 💾 when dodge is clean

Format: 7–8 slides. Include a top-down diagram description of the 3-phase dodge maneuver.
```

---

#### Block 16 — Lane-by-Lane Testing Runs
```
Generate a slide deck for Block 16 of the RISA-bot workshop.

Block 16: Lane-by-Lane Testing Runs
Time: 16:00–16:50 (50 min) | All 3 setups open

Teaching content to cover (brief — this block is mostly hands-on):
- All 3 setups are now open simultaneously
- Goal: run each setup end-to-end, fix what breaks, save when clean
- One parameter change per run — never change multiple things at once
- Reminder of tuning order: detection → steering → speed

Group assignment for first rotation:
  Lane 1: Groups 1, 2, 3 → Lane follow + tunnel
  Lane 2: Groups 4, 5 → Lane follow + hill + bumper + traffic light
  Track 3: Groups 6, 7 → Roundabout + boom gate + parking

Second rotation (16:25 onward):
  Lane 1: Groups 3, 4
  Lane 2: Groups 1, 6
  Track 3: Groups 2, 5, 7

TRY section (main activity of the block):
- Start in auto mode each time
- Run → note where it fails → fix one param → re-run → verify → save when clean

Format: 4–5 slides only. One group assignment table slide. One tuning reminder slide. One TRY IT slide. Keep it brief.
```

---

#### Block 17 — Competition Prep & Wrap-Up
```
Generate a slide deck for Block 17 of the RISA-bot workshop.

Block 17: Competition Prep & Wrap-Up
Time: 16:50–17:00 (10 min) | All groups

Teaching content to cover — Competition Day Checklist (one item per slide or all on one checklist slide):
1. Re-tune white_threshold and HSV ranges at the venue — lighting is different everywhere
2. Charge batteries fully before recording and before every competition run
3. Save params before experimenting — use 💾 every time something works
4. Use /set_challenge to test each challenge individually before full runs
5. Keep forward_speed conservative — finishing matters more than speed
6. If detection breaks — fix white_threshold first before touching anything else
7. Re-record parking if the competition floor surface is different from practice
8. Always tune in order — detection → steering → speed

Final slide: reference materials in the repo
  Guide/tuning_guide.md — full symptom → fix reference
  Guide/commands_reference.md — all ROS commands
  Guide/challenges_breakdown.md — code-level explanation per challenge

Format: 3–4 slides maximum. One competition day checklist slide. One reference slide. Keep it punchy.
```

---

## Tips for Using NotebookLM

- **Generate one block at a time** — paste one prompt, get the outline, then move to next block
- **Ask for revisions** after each output: "Make slide 3 shorter" or "Add a diagram for the PID equation"
- **Export format**: Ask NotebookLM to output as a numbered slide outline, then paste into Google Slides or PowerPoint
- **If a block has too many slides**: ask "Condense this to [N] slides, keeping only the most essential points"
- **For code slides**: ask "Format the code slides as dark-background code blocks with minimal surrounding text"
