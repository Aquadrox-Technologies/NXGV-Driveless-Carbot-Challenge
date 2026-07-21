# RISA-bot Workshop — Day 1 Cheat Sheet & Presentation Flow

This cheat sheet lists the relevant ROS 2 commands, parameter ranges, and symptom-fix matrices for Day 1 of the RISA-bot Competition Workshop. It is organized chronologically according to the Day 1 schedule (Blocks 1–8).

---

## 1. Environment & Setup Reference

Always pay attention to where a command should be run:
* **`[LAPTOP TERMINAL]`**: Executed directly on your personal computer.
* **`[ROBOT SSH]`**: Executed in a terminal connected to the robot after logging in via SSH.
* **`[LAPTOP BROWSER]`**: Executed in your laptop's web browser.

### Host vs. Robot Actions

| Context | Action | Command / Description |
|---|---|---|
| **`[LAPTOP TERMINAL]`** | SSH Connection | `ssh sunrise@<robot_ip>`<br>*(Login credentials: username `sunrise`, default password `sunrise` or `risabot`)* |
| **`[LAPTOP BROWSER]`** | Access Web Dashboard | `http://<robot_ip>:8080`<br>*(Web interface to adjust parameters and monitor topics live)* |
| **`[ROBOT SSH]`** | Source Workspace | `cd ~/risabotcar_ws && source install/setup.bash`<br>*(Or use the alias shortcut: `sos`)* |
| **`[ROBOT SSH]`** | Launch Workspace | `ros2 launch risabot_automode bringup.launch.py`<br>*(Launches sensors, perception, and auto-driver brain)* |
| **`[ROBOT SSH]`** | Rebuild Workspace | `cb`<br>*(Alias shortcut for: `colcon build --symlink-install`)* |

---

## 2. Essential ROS 2 CLI Reference

Run these commands inside a secondary **`[ROBOT SSH]`** terminal window to monitor system state and verify topics:

* **List active topics:**
  ```bash
  ros2 topic list
  ```
* **List running nodes:**
  ```bash
  ros2 node list
  ```
* **Echo camera lane error (-1.0 to 1.0) in real-time:**
  ```bash
  ros2 topic echo /lane_error
  ```
* **Verify LiDAR frequency (should be ~8-12 Hz):**
  ```bash
  ros2 topic hz /scan
  ```
* **Get a parameter value:**
  ```bash
  ros2 param get /auto_driver forward_speed
  ```
* **Set a parameter value live:**
  ```bash
  ros2 param set /auto_driver forward_speed 0.12
  ```
* **Force the state machine state for isolated testing:**
  ```bash
  ros2 topic pub --once /set_challenge std_msgs/String "data: TUNNEL"
  ros2 topic pub --once /set_challenge std_msgs/String "data: LANE_FOLLOW"
  ros2 topic pub --once /set_challenge std_msgs/String "data: OBSTRUCTION"
  ```

---

## 3. Parameter Tuning Reference

### Step 1: Lane Follower (Camera Image Pipeline)

| Parameter | Node | Default | Range | Description |
|---|---|---|---|---|
| `white_threshold` | `/line_follower_camera` | `200` | `150–240` | Binary conversion threshold. Lower = more sensitive; Higher = stricter |
| `crop_ratio_base` | `/line_follower_camera` | `0.4` | `0.2–0.6` | Crops upper portion. Higher = looks further ahead; Lower = looks in front |
| `pid_kp` | `/auto_driver` | `0.8` | `0.3–1.5` | Proportional steering strength. Adjusts correction relative to error |
| `pid_kd` | `/auto_driver` | `0.2` | `0.05–0.5` | Derivative steering damping. Prevents oscillations/overshooting |
| `pid_ki` | `/auto_driver` | `0.01` | `0.0–0.05` | Integral steering drift correction. Keep low to prevent winding |
| `forward_speed` | `/auto_driver` | `0.15` | `0.08–0.25` | Base driving speed (m/s) in straight lanes |

#### Symptom-Fix Matrix: Lane Follower
* **Robot oscillates/shakes left-right on straights:** Proportional steering gain too high.
  👉 *Lower `pid_kp` (try `0.4`–`0.5`)*
* **Robot over-steers and wobbles after curves:** Derivative damping gain too low.
  👉 *Increase `pid_kd` (try `0.3`)*
* **Robot cuts corners or hits lane borders:** Looking too far ahead.
  👉 *Decrease `crop_ratio_base` (try `0.3`)*
* **Robot drifts to one side on straight tracks:** System mechanical bias.
  👉 *Increase `pid_ki` (try `0.02`)*
* **Fails to detect lines (no dots on dashboard):** Detection threshold too strict.
  👉 *Lower `white_threshold` (try `150`–`180`)*
* **Floor textures detected as lane lines:** Detection threshold too sensitive.
  👉 *Increase `white_threshold` (try `220`)*

### Step 2: Tunnel Wall Following (LiDAR)

| Parameter | Node | Default | Range | Description |
|---|---|---|---|---|
| `kp` | `/tunnel_wall_follower` | `1.2` | `0.5–5.0` | Centering strength. Too high causes wall bouncing |
| `kd` | `/tunnel_wall_follower` | `0.3` | `0.1–1.0` | Damping. Stabilizes centering corrections |
| `kp_heading` | `/tunnel_wall_follower` | `1.0` | `0.5–2.0` | Heading alignment gain. Helps anticipate tunnel curves |
| `min_wall_points` | `/tunnel_wall_follower` | `5` | `2–10` | Laser points needed to confirm a wall exists |
| `target_center_dist` | `/tunnel_wall_follower` | `0.0` | `-0.1 – 0.1` | Offset adjustment if robot hugs one wall |

#### Symptom-Fix Matrix: Tunnel
* **Robot oscillates back and forth in tunnel:** Centering gain too high or damping too low.
  👉 *Lower `kp` (try `3.0`), raise `kd` (try `0.8`)*
* **Robot rides too close to one wall:** Calibration/offset error.
  👉 *Adjust `target_center_dist` by `+/- 0.02`*
* **Flickers in/out of tunnel mode at entrance:** Too few laser scan points matched.
  👉 *Lower `min_wall_points` to `3`*

---

## 4. Day 1 Chronological Presentation Flow

This is the order of command usage during the entire Day 1 presentation.

### Block 1 — ROS & Linux Recap (10:00–10:35)
*Establish basic connection to the robot, verify system workspace status, and launch packages.*
1. **`[LAPTOP TERMINAL]`** SSH into the robot:
   ```bash
   ssh sunrise@<robot_ip>
   ```
2. **`[ROBOT SSH]`** Source the workspace:
   ```bash
   cd ~/risabotcar_ws && source install/setup.bash
   ```
3. **`[ROBOT SSH]`** Launch the system:
   ```bash
   ros2 launch risabot_automode bringup.launch.py
   ```
4. **`[ROBOT SSH]`** (In a second terminal window) Verify nodes, topics, and parameters:
   ```bash
   ros2 topic list
   ros2 node list
   ros2 topic echo /lane_error
   ros2 param get /auto_driver forward_speed
   ```

### Block 2 — RISA-bot Overview & Goals (10:35–10:55)
*Instructor-led slides covering the course layout, node graph architecture, and Day 1/2 schedules. No hands-on coding.*

### Block 3 — Architecture & Component Setup (10:55–11:35)
*Examine the launch scripts and configuration parameters on the robot. Perform live parameter testing.*
1. **`[ROBOT SSH]`** Inspect the launcher Python script:
   ```bash
   cat ~/risabotcar_ws/src/RISA-bot/src/risabot_automode/launch/bringup.launch.py
   ```
2. **`[ROBOT SSH]`** Read the configuration parameters file:
   ```bash
   cat ~/risabotcar_ws/src/RISA-bot/src/risabot_automode/config/params.yaml
   ```
3. **`[ROBOT SSH]`** Change the forward speed parameter live and verify:
   ```bash
   ros2 param set /auto_driver forward_speed 0.12
   ros2 param get /auto_driver forward_speed
   ```
4. **`[ROBOT SSH]`** Revert the speed to default:
   ```bash
   ros2 param set /auto_driver forward_speed 0.15
   ```

### Block 4 — Dashboard Tour (11:35–12:05)
*Explore the graphical web dashboard to see real-time data overlays and drawer configurations.*
1. **`[LAPTOP BROWSER]`** Open your browser and navigate to:
   ```text
   http://<robot_ip>:8080
   ```
2. **`[LAPTOP BROWSER]`** Switch through camera tabs (`Lane Lines`, `Traffic Light`, etc.) and open the **Parameters drawer**.
3. **`[ROBOT SSH]`** Verify that changes made on the dashboard take effect on the robot:
   ```bash
   ros2 param get /auto_driver forward_speed
   ```
4. **`[LAPTOP BROWSER]`** Try setting `white_threshold` to `50` (highly sensitive) and `220` (unresponsive) in the drawer to see how detection is affected, then revert to functional default and click **💾 Save**.

### Block 5 — Lane Detection: Image Pipeline (12:05–13:00)
*Tune binary threshold and cropping parameters to isolate the white lane lines.*
1. **`[ROBOT SSH]`** Shift the crop window up/down:
   ```bash
   ros2 param set /line_follower_camera crop_ratio_base 0.3
   ros2 param set /line_follower_camera crop_ratio_base 0.7
   ```
2. **`[ROBOT SSH]`** Change threshold parameters:
   ```bash
   ros2 param set /line_follower_camera white_threshold 50
   ros2 param set /line_follower_camera white_threshold 220
   ```
3. **`[ROBOT SSH]`** Stream the error signal live while sliding the robot manually left and right:
   ```bash
   ros2 topic echo /lane_error
   ```

### Block 6 — PID Steering Tuning (14:30–15:10)
*Tune the steering control loops on the physical Lane 1 track curves.*
1. **`[ROBOT SSH]`** Set safe starting parameters:
   ```bash
   ros2 param set /auto_driver forward_speed 0.10
   ros2 param set /auto_driver pid_kp 0.5
   ros2 param set /auto_driver pid_kd 0.2
   ros2 param set /auto_driver pid_ki 0.01
   ```
2. **`[ROBOT SSH]`** Press the **Start** button on the gamepad to run auto mode.
3. **`[ROBOT SSH]`** Dynamically tune gains as it drives (refer to Step 1 matrix). For example, if it oscillates:
   ```bash
   ros2 param set /auto_driver pid_kd 0.3
   ```
4. **`[LAPTOP BROWSER]`** Click **Save** on the Web Dashboard once steering is stable.

### Block 7 — Tunnel Navigation (15:10–16:10)
*Verify LiDAR tracking and test auto-mode switches at the tunnel entrance and exit.*
1. **`[ROBOT SSH]`** Echo the `/tunnel_debug` topic to check wall coordinate distances:
   ```bash
   ros2 topic echo /tunnel_debug
   ```
2. **`[ROBOT SSH]`** Set tunnel wall following parameters:
   ```bash
   ros2 param set /tunnel_wall_follower forward_speed 0.10
   ros2 param set /tunnel_wall_follower kp 4.0
   ros2 param set /tunnel_wall_follower kd 0.6
   ```
3. **`[ROBOT SSH]`** Run the robot and open separate terminals to observe state transitions:
   - Terminal A: `ros2 topic echo /lane_error` *(active outside tunnel)*
   - Terminal B: `ros2 topic echo /tunnel_cmd_vel` *(active inside tunnel)*
4. **`[LAPTOP BROWSER]`** Click **Save** on the Web Dashboard.

### Block 8 — Full Lane 1 Tuning Run (16:10–17:00)
*Perform end-to-end runs and establish final parameter locks.*
1. **`[ROBOT SSH]`** Copy-paste the finalized baseline cheat sheet parameters:
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
2. **`[ROBOT SSH]`** Start the robot at the starting line. Run autonomously through the lane and tunnel.
3. **`[LAPTOP BROWSER]`** Click **Save** on the Web Dashboard to write everything permanently back to the robot's `params.yaml` file.

---

### Day 1 Tuning Sequence Rule (Never Skip!)
When diagnosing or tuning a robot on the track, always adjust in this order:
1. **`white_threshold`** (Clean binary detection overlay)
2. **`crop_ratio_base`** (Crop window alignment)
3. **`pid_kp / pid_kd`** (Stable steering correction)
4. **`tunnel kp / kd`** (Stable LiDAR centering)
5. **`forward_speed`** (Increase base driving speed *last*, only when steering is stable)
