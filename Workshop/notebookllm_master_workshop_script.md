# RISA-bot Competition Workshop — Master Source Document for NotebookLM

> **INSTRUCTIONS FOR INSTRUCTORS:** Upload this single, comprehensive Markdown document as a source inside Google NotebookLM. Once uploaded, copy the **Master Slide Generation Prompt** from the next section and paste it into the NotebookLM chat box to instantly generate the entire slide deck outline or slides for Day 1 and Day 2, meeting all timing and curriculum requirements.

---

## Part 1: NotebookLM Master Slide Generation Prompt

*Copy and paste the text block below into the NotebookLM chat to generate the workshop slides:*

```text
CONTEXT AND INSTRUCTION FOR SLIDE GENERATION:

You are helping create instructor presentation slides for a 2-day robotics competition workshop on RISA-bot — a ROS 2 demo robot that proves a competition-ready autonomous robot is achievable on accessible hardware (RDK X5, standard camera, and LiDAR).

INSTRUCTOR ROLE:
We are the developers of RISA-bot. Our goal is to explain how RISA-bot solves each competition challenge and guide participants through hands-on testing on the physical lanes.

PARTICIPANTS:
- 21 participants, divided into 7 groups of 3 (each group has their own RISA-bot).
- Already completed basic Linux and ROS 2 setup.

SLIDE RULES — Apply to every slide deck section you generate:
1. Dark background style (technical/robotics focus).
2. Maximum of 5 bullet points per slide (instructor talks around them).
3. One key concept per slide. Do not merge unrelated ideas.
4. Code snippets and terminal commands must be placed on their own slide or inside clearly separated code boxes.
5. Use [DIAGRAM: description] notation where a visual diagram or graph would help.
6. Every teaching block MUST end with a "🔧 TRY IT / RUN IT" slide listing the exact commands and steps for hands-on time.
7. Do not include generic quiz slides, discussion prompts, or "check your understanding" slides. Keep it focused on the codebase, CLI commands, and physical testing.

Based on the uploaded source, please generate the complete slide outline for the following blocks, matching the timing and curriculum of Day 1 and Day 2:

- Day 1 Blocks:
  1. Introduction to ROS and Linux Recap (9:30 AM - 10:00 AM)
  2. Challenge Breakdown & Setup NoMachine/SSH (10:00 AM - 10:30 AM)
  3. Module: Lane Follower (10:30 AM - 11:30 AM)
  4. Module: Tunnel Navigation (11:30 AM - 12:30 PM)
  5. Practical Session: Lane Following & Tunnel (2:00 PM - 5:00 PM)

- Day 2 Blocks:
  6. Module: Image Processing and AI Pipeline (9:00 AM - 10:00 AM)
  7. Practical Session: AI Tuning & Trigger (10:00 AM - 12:00 PM)
  8. Module: Parking (2:00 PM - 3:00 PM)
  9. Practical Session: Free Testing (3:00 PM - 5:00 PM)

For each block, output a slide-by-slide structure. Make sure to include the exact terminal commands and parameter setting commands from the source document.
```

---

## Part 2: Day 1 Workshop Modules

### Module A: Introduction to ROS & Linux Recap
**Time:** 9:30 AM - 10:00 AM | **Location:** At Stations (All 7 groups simultaneously)

#### 1. Core Concepts
* **ROS 2 Communication Pipeline:** Nodes communicate by publishing and subscribing to **topics**.
  * **Publisher:** Sends message data to a specific topic (e.g., the camera node publishes raw images).
  * **Subscriber:** Listens for message data on a specific topic (e.g., the lane follower node listens for camera images).
  * **Twist Message (`geometry_msgs/msg/Twist`):** The standard message type for sending velocity commands (`cmd_vel`), containing linear velocity `x` (forward/backward) and angular velocity `z` (steering rate).
* **RISA-bot Hardware & Sensors:**
  * **Brain:** Cytron RDK X5 developer board.
  * **Perception:** Orbbec Astra Mini camera (RGB/Depth) + YDLIDAR Tmini Plus LiDAR (laser range finding).
  * **Inertial Sensors:** IMU (attitude data: roll, pitch, yaw) integrated on the Rosmaster main board.
  * **Controller:** Gamepad/Joystick remote control.
  * **Actuators:** DC encoder motors + servo motor for steering.

#### 2. Key Commands & Terminal Operations
* **Connecting to the Robot:** SSH is the primary terminal connection.
  ```bash
  ssh sunrise@<robot_ip>
  # Password: password is hidden. Type "risabot" or "sunrise" as configured.
  ```
* **Workspace Setup:**
  ```bash
  cd ~/risabotcar_ws && source install/setup.bash
  ```
* **Essential ROS 2 CLI Operations:**
  ```bash
  ros2 topic list                           # List all active topics
  ros2 topic echo /lane_error               # Listen to a topic's output in real time
  ros2 topic hz /scan                       # Check publishing frequency of LiDAR
  ros2 node list                            # List all running nodes
  ros2 param get /auto_driver forward_speed # Get current value of a parameter
  ```
* **Build Aliases (Set up on the robot):**
  * `cb`: Builds workspace (`colcon build --symlink-install`).
  * `sos`: Sources the workspace (`source install/setup.bash`).

#### 3. 🔧 TRY IT: Basic Connection & Monitoring
Participants must open two separate terminal connections via SSH and run:
```bash
# Terminal 1: Launch the basic workspace packages
ros2 launch risabot_automode bringup.launch.py

# Terminal 2: Monitor and read parameter values
ros2 topic list
ros2 node list
ros2 topic echo /lane_error
ros2 param get /auto_driver forward_speed
```

---

### Module B: Challenge Breakdown & Setup NoMachine/SSH
**Time:** 10:00 AM - 10:30 AM | **Location:** At Stations (All 7 groups simultaneously)

#### 1. Course Layout and Dimensions
* **Course Specifications:** A 6.4m × 4m tracks setup. The robot starts at the bottom-right and travels counter-clockwise.
* **Lap 1 Challenges (Standard Sequence):**
  1. **Obstruction:** 0.8m × 0.4m block placed in the bottom-center lane. Dodged using LiDAR-based timed maneuver.
  2. **Roundabout:** Bottom-left circle. Traversed using camera-based lane following.
  3. **Tunnel:** Far-left corridor. Dark environment, requires LiDAR wall following.
  4. **Boom Gate 1 / 2:** Closed/Open check using LiDAR narrow arc cluster detection.
  5. **Hill:** Top-center ramp. Climbed using lane following, detected by IMU pitch boost.
  6. **Bumper:** Top-right physical speed bumps. Cleared by maintaining sufficient speed.
  7. **Traffic Light:** Right side, before start. Detected using HSV camera filtering.
* **Lap 2 Challenges (Parking Route):**
  * The roundabout exit changes (Boom Gate 1 closes), redirecting the robot to the inner parking area containing:
    8. **Parallel Parking:** Inner top-left. Uses odometry + LiDAR-based open-loop record-and-playback.
    9. **Perpendicular Parking:** Inner top-center. Uses odometry + LiDAR distance check.

#### 2. Environment Setup
* **NoMachine Remote Desktop:** Used to view GUI applications (like camera debug windows) directly on the robot.
  1. Open NoMachine on your laptop.
  2. Connect to the robot IP (`192.168.x.x`) on Port `4000`.
  3. Login with username `sunrise` and password `sunrise` (or `risabot`).
* **Visualizing inputs using rqt:**
  ```bash
  ros2 run rqt_image_view rqt_image_view
  ```

#### 3. 🔧 TRY IT: NoMachine & Remote Camera View
Participants setup their remote desktop and run:
```bash
# Verify NoMachine connection is active
# In the terminal, check inputs:
ls /dev/input/js*
jstest /dev/input/js0
```

---

### Module C: Lane Follower
**Time:** 10:30 AM - 11:30 AM | **Location:** At Stations + Lane 1 (Rotational pairs)

#### 1. Core Architecture & Image Pipeline
The camera captures frames at 30 FPS. The [line_follower_camera.py](file:///c:/Users/Lenovo/Downloads/Kerja/RISA-bot-1/src/risabot_automode/risabot_automode/line_follower_camera.py) node processes it through the following steps:
1. **Resize:** Standardizes input to 320x240 pixels to minimize CPU overhead.
2. **Crop:** Cuts off the upper part of the image using `crop_ratio_base` to filter out background ceiling/wall noise and focus on the road surface.
3. **Contrast Boost (CLAHE):** Enhances contrast to prevent false detections caused by uneven overhead lights.
4. **Binary Thresholding:** Converts frame to black/white using `white_threshold` (with `invert_binary=true`, pixels below the threshold represent the dark lane/line boundaries).
5. **Morphological Filtering:** Applies Open (removes isolated noise dots) and Close (bridges gaps in detected lines) operations.
6. **Multi-Scanline Detection:** Scans 8 horizontal lines across the cropped frame to detect left (blue dots) and right (pink dots) lane edges.
7. **Kalman Filtering:** Removes transient frame-to-frame jitter.
8. **Error Calculation:** Publishes `/lane_error` ranging from -1.0 (hard left deviation) to +1.0 (hard right deviation).

#### 2. PID Steering Equation
The [auto_driver.py](file:///c:/Users/Lenovo/Downloads/Kerja/RISA-bot-1/src/risabot_automode/risabot_automode/auto_driver.py) node reads `/lane_error` and calculates the required motor steering command:

$$\text{Steering} = (K_p \times \text{error}) + (K_i \times \sum \text{error}) + (K_d \times \frac{d(\text{error})}{dt})$$

* **$K_p$ (pid_kp):** Proportional gain. Adjusts correction strength relative to current error. Too high causes oscillations.
* **$K_d$ (pid_kd):** Derivative gain. Damps steering inputs to prevent overshoot. Too high causes sluggish, jerky movement.
* **$K_i$ (pid_ki):** Integral gain. Corrects constant steering offset/drift over time. Keep very low.
* **Adaptive Speed:** Robot automatically slows down during sharp turns to maintain lane lock:
  $$\text{Speed} = \max(\text{min\_turn\_speed}, \text{forward\_speed} - (\text{speed\_error\_scale} \times |\text{error}|))$$

#### 3. Live Dashboard Debugging
Open the Web Dashboard at `http://<robot_ip>:8080` in your web browser:
* **Lane Lines Tab:** View camera overlay showing left edge (blue), right edge (pink), center line (green), and crop boundary (purple).
* **Parameters Drawer:** Side slide-out panel to view and modify ROS 2 parameters on the fly without resetting nodes.
* **💾 Save Button:** Saves current running parameters permanently back into the robot's `params.yaml` file.

#### 4. Parameter Reference & Tuning
* **Tuning Command Cheat Sheet:**
  ```bash
  ros2 param set /line_follower_camera white_threshold 180
  ros2 param set /line_follower_camera crop_ratio_base 0.55
  ros2 param set /auto_driver pid_kp 0.8
  ros2 param set /auto_driver pid_kd 0.20
  ros2 param set /auto_driver forward_speed 0.15
  ```
* **Symptom → Fix Tuning Table:**

| Observed Behavior | Probable Cause | Corrective Action |
|---|---|---|
| Shakes/oscillates left-right on straights | Proportional gain $K_p$ too high | Lower `/auto_driver pid_kp` (try 0.4–0.5) |
| Over-steers and wobbles after exiting a turn | Damping $K_d$ too low | Increase `/auto_driver pid_kd` (try 0.3) |
| Drifts off to one side on straight track | System alignment bias | Increase `/auto_driver pid_ki` (try 0.02) |
| Cuts inside corners and hits borders | Looking too far ahead | Decrease `/line_follower_camera crop_ratio_base` (try 0.3) |
| Fails to detect lines (No dots visible on dashboard) | Detection threshold too high | Lower `/line_follower_camera white_threshold` (try 150) |
| Floor textures detected as lane lines | Detection threshold too low | Increase `/line_follower_camera white_threshold` (try 220) |

#### 5. 🔧 TRY IT: Lane Following Calibration
1. Place the robot on a straight segment of Lane 1.
2. Open the dashboard `http://<robot_ip>:8080` and select the **Lane Lines** overlay.
3. Echo the error signal:
   ```bash
   ros2 topic echo /lane_error
   ```
4. Slide the robot manually: left displacement should show negative error, right displacement positive.
5. Set initial safe values:
   ```bash
   ros2 param set /auto_driver forward_speed 0.10
   ros2 param set /auto_driver pid_kp 0.5
   ros2 param set /auto_driver pid_kd 0.2
   ```
6. Press the **Start** button on the joystick to activate auto mode and verify. Adjust parameters until stable, then click **💾 Save**.

---

### Module D: Tunnel Navigation
**Time:** 11:30 AM - 12:30 PM | **Location:** At Stations + Lane 1 (Rotational pairs)

#### 1. Core LiDAR Concepts & Wall Following Algorithm
* **Why LiDAR?** Tunnels are dark; cameras fail due to low contrast and shadows. LiDAR uses laser rangefinding to detect walls regardless of light intensity.
* **Laser Scan Data (`sensor_msgs/msg/LaserScan`):** A list of distances at specific angles.
* **Processing Steps in [tunnel_wall_follower.py](file:///c:/Users/Lenovo/Downloads/Kerja/RISA-bot-1/src/risabot_automode/risabot_automode/tunnel_wall_follower.py):**
  1. **Coordinate Conversion:** Transforms polar coordinates (angle, range) from `/scan` into Cartesian (x, y) coordinates relative to the robot.
  2. **Wall Classification:** Filters points based on angle sectors:
     * **Left Wall:** 15° to 120°
     * **Right Wall:** -120° to -15°
  3. **Binning:** Sorts points by forward depth to calculate average wall distances.
  4. **Error Terms:**
     * **Lateral Error:** Difference between left wall distance and right wall distance ($\text{error} = \text{left\_dist} - \text{right\_dist}$).
     * **Heading Error:** Orientation relative to the walls to anticipate curves ahead.
  5. **Smoothing:** Applies Exponential Moving Average (EMA) filter to smooth command outputs.
* **Auto-Switch Hysteresis:**
  * To prevent flickering transitions, both walls must be detected for **3 consecutive frames** to switch from `LANE_FOLLOW` to `TUNNEL` mode.
  * When walls disappear, the system must detect them missing for **3 consecutive frames** to switch back to `LANE_FOLLOW`.

#### 2. Parameter Reference & Tuning
* **Tuning Parameters:**
  * `kp`: Centering strength. Higher values make it stay in the middle, but too high causes wall oscillation.
  * `kd`: Damping. Helps stabilize the robot.
  * `min_wall_points`: Minimum laser hits needed to confirm a wall exists (default: 5).
  * `target_center_dist`: Offset parameter if the robot consistently hugs one wall.
* **Symptom → Fix Tuning Table:**

| Observed Behavior | Probable Cause | Corrective Action |
|---|---|---|
| Bounces back and forth between walls | Centering gain too high | Lower `/tunnel_wall_follower kp` (try 3.0), raise `kd` (try 0.8) |
| Rides too close to the left/right wall | Calibration offset | Adjust `/tunnel_wall_follower target_center_dist` by $\pm 0.02$ |
| Flickers in and out of tunnel mode at entrance | Laser points count low | Lower `/tunnel_wall_follower min_wall_points` to 3 |
| Over-corrects on curves | Sluggish heading response | Raise `kp_heading` to 1.5 |

#### 3. 🔧 TRY IT: Run the Tunnel
1. Place the robot in the entry zone of Lane 1's tunnel.
2. In a terminal, monitor the diagnostic topic:
   ```bash
   ros2 topic echo /tunnel_debug
   ```
3. Watch the dashboard sensor panel. It should display **IN TUNNEL** when pushed inside.
4. Test auto-mode switching by running the full lane:
   ```bash
   ros2 param set /tunnel_wall_follower forward_speed 0.10
   ros2 param set /tunnel_wall_follower kp 4.0
   ros2 param set /tunnel_wall_follower kd 0.6
   ```
5. Press **Start** on the joystick. The robot should follow the lane, auto-switch to tunnel mode inside, and switch back to camera tracking upon exit.

---

### Practical Session: Lane Following & Tunnel
**Time:** 2:00 PM - 5:00 PM | **Location:** Lane 1 (Rotational Groups)

#### 1. Group Rotation Schedule
Groups rotate in pairs on Lane 1. While waiting, groups analyze data, change configurations in their parameters drawer, or charge batteries.

* **Slot A (2:00 PM - 2:40 PM):** Groups 1 & 2 on Lane 1.
* **Slot B (2:40 PM - 3:20 PM):** Groups 3 & 4 on Lane 1.
* **Slot C (3:20 PM - 4:00 PM):** Groups 5 & 6 on Lane 1.
* **Slot D (4:00 PM - 4:40 PM):** Group 7 on Lane 1 (plus open re-testing for anyone else).
* **Final Optimization (4:40 PM - 5:00 PM):** General open track testing and parameter locks.

#### 2. Code Testing Checklist for Physical Verification
- [ ] Connect laptop to robot via NoMachine and open terminal windows.
- [ ] Verify battery voltage is above 11.5V (DC motor speeds drift when battery drops).
- [ ] Launch: `ros2 launch risabot_automode bringup.launch.py`.
- [ ] Walk the course in manual mode, ensuring `/lane_error` behaves properly.
- [ ] Confirm `white_threshold` filters out floor glare under active room lighting.
- [ ] Check `/tunnel_debug` outputs coordinates when placing obstacles next to the robot.
- [ ] Perform a full autonomous run from the starting line, through the tunnel, to the exit.
- [ ] Save parameters using the Web Dashboard **Save** button.

---
---

## Part 3: Day 2 Workshop Modules

### Module E: Image Processing and AI Pipeline
**Time:** 9:00 AM - 10:00 AM | **Location:** At Stations (All 7 groups simultaneously)

#### 1. Edge AI and Hardware Acceleration
* **Brain Processing Unit (BPU):** A dedicated neural network accelerator on the RDK X5 rated at **10 TOPS**.
* **Performance Gain:** Running a YOLOv5s model on CPU yields only ~1–2 FPS, consuming almost all CPU cycles. Running the same model on the BPU executes at **30+ FPS** at negligible CPU load, freeing processing headroom for motor control, path planning, and LiDAR.
* **INT8 Quantization:** The BPU only accepts compiled `.bin` models. Compilation converts floating-point weights (FP32) into 8-bit integers (INT8), reducing model size by 4x and speeding up inference.

#### 2. YOLOv5 Dataset & Compilation Pipeline
```
Roboflow (Dataset & Labels) 
  → Train YOLOv5s (Google Colab GPU, Opset 11 ONNX) 
  → Quantize & Compile (Docker Toolchain on Windows) 
  → Run verify_bpu.py (Robot BPU)
```
1. **Roboflow Dataset Collection:** Collect images using the robot's camera to match the target environment's perspective. Include a split of 80% training / 20% validation.
2. **YOLOv5 Training:** Performed on Google Colab using a T4 GPU. The model is exported to **ONNX opset 11** format (maximum opset supported by the BPU compiler).
3. **BPU Compilation via Docker:** Horizon's `hb_mapper` compiler reads `best.onnx` and a calibration dataset (50 raw CHW uint8 `.bin` images) to compile a quantized `.bin` model file.
4. **Patching Resize Nodes:** Standard ONNX exports contain attributes (like `antialias` or `allowzero`) unsupported by the BPU compiler. The `patch_onnx_resize.py` script replaces these incompatible nodes.

#### 3. BPU Runtime Inference Pipeline
The [signage_detector.py](file:///c:/Users/Lenovo/Downloads/Kerja/RISA-bot-1/src/risabot_automode/risabot_automode/signage_detector.py) node executes the following pipeline:
1. **Preprocessing:** Converts incoming camera frames from BGR format to **NV12** (YUV420sp), the native format expected by the BPU input engine.
2. **BPU Forward Pass:** Feeds NV12 data into the BPU hardware using the `pyeasy_dnn` library.
3. **Postprocessing (Non-Maximum Suppression - NMS):** Runs on the CPU to filter out redundant, overlapping bounding boxes, outputting detection boxes with confidence scores.

#### 4. Gated Triggers & Computer Vision Boom Gate Detector
* **AI Trigger Points & Priming Window:** To prevent false positives (e.g., detecting a parking sign on the other side of the room), detection nodes use a **Priming Window**. The node only listens to the BPU output when the state machine arms the detector at specific locations.
* **Gated Trigger Code Structure:**
  ```python
  # Gated trigger pattern inside signage_detector.py
  def image_callback(self, msg):
      if not self.active_state in ['PARKING_ARMED', 'TRAFFIC_LIGHT_ARMED']:
          return # Gated: Do not spend CPU/BPU cycles if not in the target zone
      
      # Execute BPU forward pass...
  ```
* **Boom Gate CV Detection:** LiDAR checks a narrow forward arc ($\pm 20^\circ$) within 0.1m to 0.8m. If range variance is low (indicating a flat horizontal bar), the gate is registered as CLOSED. The output is filtered through a 3-frame hysteresis gate.

---

### Practical Session: AI Tuning & Trigger
**Time:** 10:00 AM - 12:00 PM | **Location:** Lane 2 + At Stations

#### 1. BPU Model Verification
Before deploying to the active robot loop, verify the BPU compiler output:
* **Static Verification:** Checks if the BPU hardware can load the `.bin` model and perform a forward pass.
  ```bash
  cd ~/risabotcar_ws
  python3 tools/bpu_model/verify_bpu.py
  # Should report: "Verification Successful! BPU model is fully functional."
  ```
* **Live Camera Verification:** Subscribes to the camera feed and prints real-time BPU output scores.
  ```bash
  # Terminal 1: Launch camera
  ros2 launch astra_camera astra_mini.launch.py
  # Terminal 2: Run diagnostic
  python3 tools/bpu_model/verify_live.py
  ```

#### 2. Live Parameter Tuning
Use the Web Dashboard parameters drawer to tune BPU thresholds:
* `conf_threshold` (default: 0.40): Minimum confidence required to output a detection box. Lower to increase detection range; raise to eliminate false positives.
* `min_parking_sign_width` (default: 80 px): Filters out distant signboards to avoid premature parking maneuvers.

#### 3. 🔧 RUN IT: Verify and Tune Detections
1. Run the static verification script on the robot:
   ```bash
   python3 ~/risabotcar_ws/tools/bpu_model/verify_bpu.py
   ```
2. Verify live camera inference. Hold the parking signboard 60 cm in front of the camera:
   ```bash
   python3 ~/risabotcar_ws/tools/bpu_model/verify_live.py
   # Observe the detected Class ID (Class 1 = parking_sign).
   ```
3. Tune parameter thresholds to match room lighting:
   ```bash
   ros2 param set /signage_detector conf_threshold 0.35
   ros2 param set /signage_detector min_parking_sign_width 90
   ```

---

### Module F: Parking
**Time:** 2:00 PM - 3:00 PM | **Location:** Track 3 (Rotational pairs)

#### 1. Why Reactive Sensors Fail in Precision Parking
* Cameras suffer from severe perspective distortion (perspective warp) when the robot gets extremely close to parking lines.
* LiDAR beams hit angles that cause specular reflections or miss slots entirely due to beam spacing.
* **Solution:** **Record & Playback (Open-Loop Trajectory).** The robot records joystick commands at 20 Hz, then replays the motor and servo command sequence relative to a known start point.

#### 2. System Architecture
* **signage_detector:** YOLOv5s BPU node detects the parking signboard.
* **auto_driver:** Listens to `/parking_sign_detected` on Lap 2, stops the robot, and sends a transition trigger.
* **parking_controller:** Receives the start trigger, halts the robot for a settling period, and executes the replaying loop.

#### 3. Gamepad Button Mapping for Recording
* **Button A:** Toggle Record/Stop. Starts or stops recording joystick inputs.
* **Button B:** Saves the recorded buffer to `~/recorded_movement.json`.
* **Button X:** Plays back the currently loaded recording buffer.
* **D-Pad Left/Right:** Cycles through saved recordings.

#### 4. Trigger State Machine
The parking process transitions through these states:
1. `LANE_FOLLOW`: Normal camera-based driving (Lap 2 active).
2. `PARKING_SETTLE`: BPU detects the parking signboard. The robot stops and stands still for 2.0s (`parking_idle_duration`) to damp momentum and align the starting position.
3. `REPLAYING`: Executes the open-loop trajectory from the buffer.
4. `FINISHED`: Playback ends, motors turn off, and the robot enters a locked state.

#### 5. Advanced Tuning & Troubleshooting
* **Battery Level Drift:** Open-loop playback depends on battery voltage. If the battery is low, motors spin slower, causing the robot to undershoot. **Always charge the battery fully before competition runs.**
* **Wheel Slip:** Acceleration spikes during playback cause wheel spin, introducing path error. Drive smoothly during recording.
* **Idle Duration:** Adjust `/auto_driver parking_idle_duration` (default: 2.0s) to ensure the robot is completely stationary before playback begins.

---

### Practical Session: Free Testing
**Time:** 3:00 PM - 5:00 PM | **Location:** Track 3 + Lane 1 + Lane 2 (All setups open)

#### 1. Step-by-Step Recording & Playback Calibration
1. Align the robot at the starting position next to the parking slot.
2. Press **Button A** on the controller (or run the CLI record command). The terminal displays:
   ```text
   🔴 RECORDING started
   ```
3. Drive slowly and smoothly into the parking slot using the joystick.
4. Press **Button A** again to stop.
5. Press **Button B** to save the recording.
6. Reset the robot to the starting line.
7. Press **Button X** to play back and verify accuracy. Iterate until 3 consecutive plays land cleanly in the slot.

#### 2. Running the Autonomous Sequence
1. Set the lap tracker to Lap 2:
   ```bash
   ros2 param set /auto_driver current_lap 2
   ```
2. Place the robot at the roundabout entrance.
3. Enable auto mode. The robot should:
   * Exit the roundabout into the parking lane.
   * Stop once the camera sees the parking sign.
   * Settle for 2 seconds.
   * Auto-execute the recorded parking trajectory.

---
---

## Part 4: Complete Code Testing Index

Use these commands to test each hardware component and node in isolation:

### 1. Hardware Verification
```bash
# Verify joystick connection
ls -la /dev/input/js*
# Run visual joystick axis test
jstest /dev/input/js0

# Run motor sanity check (wheels rotate forward for 2 seconds)
python3 ~/risabotcar_ws/tools/test_motors.py
```

### 2. Node Testing in Isolation
```bash
# Force the state machine into specific modes for testing:
ros2 topic pub --once /set_challenge std_msgs/String "data: LANE_FOLLOW"
ros2 topic pub --once /set_challenge std_msgs/String "data: TUNNEL"
ros2 topic pub --once /set_challenge std_msgs/String "data: TRAFFIC_LIGHT"
ros2 topic pub --once /set_challenge std_msgs/String "data: OBSTRUCTION"

# Monitor sensor topics:
ros2 topic echo /lane_error
ros2 topic echo /traffic_light_state
ros2 topic echo /boom_gate_open
ros2 topic echo /tunnel_detected
ros2 topic echo /parking_complete
```

### 3. Quick-Copy Tuning Parameters
```bash
# Lane Following:
ros2 param set /auto_driver forward_speed 0.15
ros2 param set /auto_driver pid_kp 0.8
ros2 param set /auto_driver pid_kd 0.20
ros2 param set /line_follower_camera white_threshold 200
ros2 param set /line_follower_camera crop_ratio_base 0.55

# Tunnel:
ros2 param set /tunnel_wall_follower kp 1.2
ros2 param set /tunnel_wall_follower kd 0.3
ros2 param set /tunnel_wall_follower target_center_dist 0.00

# Obstacle Dodge:
ros2 param set /obstruction_avoidance detect_dist 0.50
ros2 param set /obstruction_avoidance steer_angular 0.6
```
