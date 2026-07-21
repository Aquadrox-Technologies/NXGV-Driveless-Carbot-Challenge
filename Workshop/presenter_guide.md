# RISA-bot Workshop — Day 1 Presenter's Guide & Script

This guide provides a slide-by-slide script, presenter flow, and student-friendly explanations for Day 1 of the RISA-bot Competition Workshop. Use this as a guide to deliver the content, run live demonstrations, and help students calibrate their robots.

---

## 🎓 Core Technical Terms Explained for Students

When introducing these concepts, use these definitions and analogies to help students grasp the mathematics and engineering behind RISA-bot.

### 1. CLAHE (Contrast Limited Adaptive Histogram Equalization)
* **What it is**: An image processing technique that enhances image contrast locally in small sections rather than the whole image at once.
* **Student Definition**: "CLAHE is like a smart pair of sunglasses that automatically adjusts its tint depending on where you look. If you look at a bright sky, it dims just that spot; if you look down into a dark shadow, it brightens only the shadow so you can see clearly."
* **Why it's needed**: Traditional contrast boosters adjust the whole image. If a room has one bright overhead lamp and one dark shadow, a global adjustment washes out the bright area or turns the shadow pitch black. CLAHE divides the image into a grid (like a chessboard) and adjusts each tile independently.
* **The "Contrast Limited" part**: If a tile is flat (like a plain white wall), normal boosters amplify tiny camera noise into massive, ugly blotches. CLAHE limits the contrast boost in uniform areas to keep the image clean.
* **On RISA-bot**: It ensures the robot can see the lane lines even when transitioning from bright camera glare under spotlights into dark shadows on the floor.

### 2. PID Controller (Proportional-Integral-Derivative)
* **What it is**: A feedback loop mechanism that calculates how much to steer based on the distance from the center (the "error").
* **Student Definition**: "Think of driving a car on a highway. You want to stay in the center. A PID controller represents your brain making steering corrections using three perspectives: **The Present (P)**, **The Past (I)**, and **The Future (D)**."
  * **P (Proportional) – "The Present"**: How far off are you right now? If you are slightly off-center to the left, you turn the wheel slightly to the right. If you are way off, you turn the wheel hard. The correction is proportional to your current error. *Problem*: If you only use P, you will overshoot the center and oscillate back and forth forever.
  * **D (Derivative) – "The Future"**: How fast are you rushing back to the center? D acts as a damper (a shock absorber). If you are correcting too fast, D steers the wheel back toward the straight direction *before* you cross the center line, bringing you to a smooth halt.
  * **I (Integral) – "The Past"**: Are you drifting over time? If your wheels are misaligned and the car naturally pulls to the left, the error accumulates. The I term adds up all past errors and applies a steady, growing push to correct the alignment bias.
* **On RISA-bot**: It takes the lane position error from the camera and calculates exactly how many degrees to turn the steering servo to keep the robot centered.

### 3. Kalman Filter
* **What it is**: An algorithm that estimates the true position of something by combining noisy measurements with a physical prediction model.
* **Student Definition**: "Imagine walking in a dark room. You know your stride is exactly 0.8 meters, so you can count your steps to guess how far you've gone (this is your **prediction**). You also check a glitchy GPS tracker on your wrist that jumps around (this is your **measurement**). A Kalman filter mathematically combines both: it knows how reliable your step-counting is and how noisy the GPS is, and blends them to give you the most accurate guess of where you actually are."
* **On RISA-bot**: Raw lane detections from the camera jump slightly frame-to-frame due to floor glare. If the robot reacted to every tiny jump, it would shake violently. The Kalman filter predicts where the lane line *should* be based on the robot's movement and blends it with the camera's raw data to create smooth, steady path tracking.

### 4. Hysteresis
* **What it is**: A system behavior where the output depends not just on the current input, but also on its history. It creates a "buffer zone" to prevent rapid, unstable switching.
* **Student Definition**: "Think of a household air conditioner. If it turned on the exact millisecond the temperature hit 22.01°C, and turned off the moment it hit 21.99°C, it would click on and off every two seconds and break. Instead, it uses hysteresis: it turns on at 23°C and off at 21°C. That gap in between is the buffer zone."
* **On RISA-bot**: When entering a tunnel, the LiDAR sees walls. To prevent the robot from flickering rapidly between `LANE_FOLLOW` (camera) and `TUNNEL` (LiDAR) modes at the entrance, it must detect the walls for **3 consecutive frames** before switching. It must also lose the walls for **3 consecutive frames** before switching back to the camera.

### 5. EMA (Exponential Moving Average)
* **What it is**: A type of moving average that gives more weight to recent data points while slowly forgetting older ones.
* **Student Definition**: "Imagine describing your mood. Your mood today is mostly affected by what happened today (80% weight), but you still carry a little bit of how you felt yesterday (20% weight). Yesterday's feelings are still there, but fading. EMA filters out sudden, single bad events while keeping your response smooth and realistic."
* **On RISA-bot**: In the LiDAR wall follower, the calculated steering commands are smoothed using an EMA. This ensures that if the LiDAR hits a small gap in the wall, the steering wheel doesn't jerk suddenly, resulting in a smooth, continuous path.

### 6. HSV Color Space (Hue, Saturation, Value)
* **What it is**: An alternative color representation to RGB (Red, Green, Blue) that separates color type (Hue) from color purity (Saturation) and brightness (Value).
* **Student Definition**: "Imagine picking paint at a hardware store. RGB is like mixing light bulbs. HSV is how humans think: 
  * **Hue**: What is the actual color shade? (Red, Green, Yellow)
  * **Saturation**: How vivid or 'neon' is it, or is it faded and gray?
  * **Value**: How bright is the light shining on it?
* **On RISA-bot**: We use HSV to detect traffic lights. It allows us to lock onto the *Hue* of red or green and ignore changes in *Value* (brightness) caused by shadows or overhead spotlights in the room.

---

## 🗺️ Day 1 Presentation Flow & Slide Script

This section details the talking points, visuals, and actions for the presenter across all 64 slides of **NXGV DAY ONE.pptx**.

---

### 🏁 Part 1: Welcome & Introduction (Slides 1–5)

* **Visuals**: Title slide, Day 1 Schedule, Course layout, and RISA-bot chassis photos.
* **Key Topics**: Workshop objectives, track layouts, and logistics.

#### Slide 1: Cover Slide
* **Talking Points**: "Welcome everyone to Day 1 of the RISA-bot Competition Workshop! Over the next two days, we are going to dive deep into autonomous robotics. We designed RISA-bot to prove that you don't need million-dollar industrial setups to build a highly capable autonomous vehicle. With standard sensors—a camera, LiDAR, and IMU—and ROS 2, we can conquer every challenge on the track."

#### Slide 2: Meet the Instructors & Creators
* **Talking Points**: "We are the developers of RISA-bot. Our goal is not just to show you a finished robot, but to explain exactly *how* it works, show you the code, and give you hands-on experience calibrating the algorithms. By the end of this workshop, you will be the ones tuning these machines to run at maximum speed."

#### Slide 5: Hands-On Group Rotation Rules
* **Talking Points**: "We have 21 participants split into 7 groups of 3. When we do track testing, we will rotate in pairs of groups through the lanes: Slot A is Groups 1 and 2, Slot B is Groups 3 and 4, Slot C is Groups 5 and 6, and Slot D is Group 7. While you are on the track, you will be running the robot. While you are at your station, you will be analyzing data, preparing commands, or charging batteries."

---

### 💻 Part 2: Module A – ROS & Linux Recap (Slides 6–13)

* **Visuals**: Terminal command blocks, SSH connection steps, and ROS 2 node graphs.
* **Key Topics**: SSH, sourcing, ROS 2 CLI (`topic`, `node`, `param`), and system launch.

#### Slide 6: Module A Title – ROS & Linux Recap
* **Talking Points**: "Let's kick off Module A. Before we touch the robot's brain, we need to make sure we can communicate with it. We will quickly recap how to log in, run diagnostics, and control parameters from the terminal."

#### Slide 7: Connecting to the Robot (SSH)
* **Talking Points**: "To connect to your robot, you will use SSH. Open your terminal and run `ssh sunrise@<robot_ip>`. The IP address for your group's robot is written on the sticky note on your desk. The password is `sunrise` or `risabot` depending on your unit. SSH gives you a direct command-line interface into the robot's onboard computer, the RDK X5."

#### Slide 8: The Workspace & Sourcing
* **Talking Points**: "Once logged in, you must navigate to the workspace: `cd ~/risabotcar_ws`. In ROS 2, before you run any node or command, you must source the installation setup file. Run `source install/setup.bash`. To save time, we have set up terminal aliases: typing `sos` will source the workspace automatically, and `cb` will build it."

#### Slide 9: Launching the Full System
* **Talking Points**: "To start the entire RISA-bot software suite, we run a launch file. Run the command: `ros2 launch risabot_automode bringup.launch.py`. This starts the hardware drivers, the sensors, the camera pipeline, the LiDAR processor, and the brain node. Once running, do not close this terminal! Open a *second* terminal window and SSH in again to run commands."

#### Slide 10: ROS 2 CLI – Listing Topics & Nodes
* **Talking Points**: "In your second terminal, you can inspect the running system. Run `ros2 node list` to see all active nodes (the programs running on the robot). Run `ros2 topic list` to see all communication channels (topics) through which these nodes share data. You will see topics like `/scan` for LiDAR and `/lane_error` for the camera."

#### Slide 11: Listening to Topics (`topic echo`)
* **Talking Points**: "To see what data is passing through a topic in real-time, we use `topic echo`. Run `ros2 topic echo /lane_error`. You will see numbers printing out. If you move the robot left and right manually, you will watch this number change. This is the error signal we use for steering."

#### Slide 12: Inspecting and Modifying Parameters (`param`)
* **Talking Points**: "Parameters are settings you can change on the fly. To check a parameter value, use `ros2 param get /auto_driver forward_speed`. To change it, use `ros2 param set /auto_driver forward_speed 0.15`. This is incredibly powerful—you can speed up or slow down the robot without stopping the program or rebuilding code!"

#### Slide 13: 🔧 TRY IT: Connection & CLI Sanity Check
* **Talking Points**: "Now it's your turn. Spend the next 20 minutes connecting to your robot. Launch the bringup file in Terminal 1. In Terminal 2, list the nodes and topics, echo the `/lane_error` topic, and check the default `forward_speed` parameter. Let me know if you run into any connection issues!"

---

### 🌐 Part 3: Module B – Challenge Breakdown & SSH Setup (Slides 14–22)

* **Visuals**: Challenge sequence flowchart, Lap 1 vs Lap 2 routes, NoMachine UI.
* **Key Topics**: Competition rules, Remote Desktop (NoMachine), and camera verification (`rqt_image_view`).

#### Slide 14: Module B Title – Course Layout & Remote Desktop
* **Talking Points**: "In Module B, we will break down the competition challenges step-by-step and set up a graphical remote desktop so you can see what the robot's camera sees."

#### Slide 15: Lap 1 Challenge Sequence
* **Talking Points**: "On Lap 1, the robot must complete a set sequence. First, it detects and dodges an **Obstruction** block in the lane. Second, it traverses the **Roundabout**. Third, it enters the dark **Tunnel**. Fourth, it checks the **Boom Gate** (waits for it to open). Fifth, it climbs and descends the **Hill**. Sixth, it drives over the **Bumper** speed bump. Finally, it stops at the **Traffic Light** and waits for green before crossing the start/finish line."

#### Slide 16: Lap 2 Parking Sequence
* **Talking Points**: "On Lap 2, the exit of the roundabout changes because Boom Gate 1 closes, redirecting the robot to the inner track. Here, the robot must identify the parking sign and park autonomously inside the designated slot using a record-and-playback trajectory."

#### Slide 17: Setting up NoMachine (GUI Access)
* **Talking Points**: "Because the robot runs a Linux environment, we want to see graphical windows (like camera streams) on our laptops. We use NoMachine. Open NoMachine on your laptop, connect to your robot's IP on port 4000, and log in with username `sunrise` and password `sunrise` (or `risabot`). You will see the robot's desktop."

#### Slide 18: Visualizing Camera Feeds (`rqt_image_view`)
* **Talking Points**: "Once inside the NoMachine remote desktop, open a terminal on the robot and run `ros2 run rqt_image_view rqt_image_view`. This opens a window where you can select different camera topics. You can see the raw feed or the processed debug streams."

#### Slide 19: Joystick Controllers & Safety
* **Talking Points**: "Each group has a wireless gamepad. The gamepad is your safety switch.
  * **Start Button**: Enables autonomous mode.
  * **Back Button / Trigger**: Instantly halts the robot and returns to manual mode.
  * **Left Joystick**: Controls steering manually.
  * **Right Trigger**: Manual throttle."

#### Slide 20: Diagnostic Check command (`jstest`)
* **Talking Points**: "To verify your joystick is connected, check `/dev/input/js0`. You can run `jstest /dev/input/js0` in the terminal to see a visual layout of buttons and axes responding to your controller. Always check this if the robot doesn't respond to manual override."

#### Slide 21: 🔧 TRY IT: NoMachine & Camera Verification
* **Talking Points**: "For the next 15 minutes, log into NoMachine. Open `rqt_image_view` to verify you can see the camera stream, and run the `jstest` command to make sure your joystick is connected and sending signals."

#### Slide 22: Live Q&A and Debugging
* **Talking Points**: "Any questions about NoMachine or the course challenges before we start analyzing the codebase? (Address user questions)."

---

### 📷 Part 4: Module C – Lane Follower Image Pipeline (Slides 23–37)

* **Visuals**: OpenCV image pipeline flow, CLAHE comparison, cropping overlays, binary thresholding sliders.
* **Key Topics**: Resize, Crop, CLAHE, Binary Thresholding, Morphological Operations, Scanlines, Kalman Filter, and `/lane_error`.

#### Slide 23: Module C Title – Lane Follower: Image processing
* **Talking Points**: "Let's start Module C. This is the heart of the robot. We will cover the image processing pipeline that takes raw camera video and extracts the exact lane position."

#### Slide 24: The Image Pipeline Overview
* **Talking Points**: "The camera captures frames at 30 frames per second. Processing high-resolution images is slow and wastes battery. Our node `line_follower_camera.py` runs a 8-step pipeline: Resize, Crop, CLAHE contrast boost, Binary Threshold, Morphological cleanup, Multi-scanline edge finding, Kalman filtering, and Error calculation."

#### Slide 25: Step 1 & 2 – Resizing and Cropping
* **Talking Points**: "First, we shrink the image to 320x240 pixels. This reduces the processing workload by 4x. Second, we crop out the top half of the frame using `crop_ratio_base`. We don't care about the ceiling, walls, or spectators—we only want to look at the floor. The purple horizontal line on your dashboard shows where this crop starts."

#### Slide 26: Parameter Focus: `crop_ratio_base`
* **Talking Points**: "How do we adjust the crop?
  * **Higher value (e.g. 0.7)**: The robot looks further ahead (crops less). Useful for high speed, but might pick up wall/ceiling noise.
  * **Lower value (e.g. 0.3)**: The robot looks right in front of its wheels. Great for tight curves, but cuts corners if going too fast."

#### Slide 27: Step 3 – CLAHE (Contrast Booster)
* **Talking Points**: "Step 3 is CLAHE. *(Refer to explanation: Contrast Limited Adaptive Histogram Equalization)*. It splits the cropped frame into small grids and boosts contrast locally. This prevents the robot from losing the lane line when it drives under bright glare or into a dark shadow."

#### Slide 28: Step 4 – Binary Thresholding
* **Talking Points**: "Step 4 converts the image to binary (black and white). The parameter `white_threshold` determines the cutoff point. Since our lines are black on a white/light surface, we set `invert_binary` to true. This means pixels below the threshold (dark pixels) become white (value 255) in the processed image, representing the lane lines, and the rest becomes black (0)."

#### Slide 29: Parameter Focus: `white_threshold`
* **Talking Points**: "Tuning `white_threshold` is the most important step:
  * **Too low (e.g. 50)**: The robot is too sensitive. Reflections on the floor look like lane lines.
  * **Too high (e.g. 220)**: The robot is too strict. It won't see the lanes at all.
  * **Rule**: You must always calibrate this first when lighting conditions change."

#### Slide 30: Step 5 – Morphological Operations (Cleanup)
* **Talking Points**: "Step 5 cleans up noise. We use **Opening** (erases isolated tiny white specks) and **Closing** (bridges small gaps in the detected lines). This ensures the lines look solid and continuous before we detect the edges."

#### Slide 31: Title: MODULE C — Slide 31
* **Talking Points**: "This is the transition slide for the hands-on dashboard setup. Let's make sure our dashboards are open at `http://<robot_ip>:8080`. Under the **Lane Lines** tab, you will see all these image processing steps overlaid in real-time."

#### Slide 32: Step 6 – Multi-Scanline Edge Detection
* **Talking Points**: "Step 6 finds the line edges. The node draws 8 horizontal lines across the cropped image. It scans from the center outward on each line. The first dark pixel it hits on the left is marked as the Left Edge (blue dot). The first on the right is the Right Edge (pink dot). The center of these two is the Lane Center (green dot)."

#### Slide 33: Step 7 – Kalman Filtering (Smoothing Jitter)
* **Talking Points**: "Step 7 is the Kalman Filter. *(Refer to explanation: Kalman Filter)*. Sometimes a floor reflection or a glitch makes a dot jump to the side for a single frame. The Kalman filter predicts where the dot should be based on physics and ignores sudden, physically impossible jumps. This gives us smooth, jitter-free lines."

#### Slide 34: Step 8 – Error Output (`/lane_error`)
* **Talking Points**: "Step 8 is the final output. The node calculates how far off-center the green dots are relative to the middle of the camera. It publishes a single float on `/lane_error`:
  * **-1.0**: Hard left deviation (robot needs to steer hard right).
  * **+1.0**: Hard right deviation (robot needs to steer hard left).
  * **0.0**: Perfectly centered."

#### Slide 35: Live Dashboard Interface (Lane Lines view)
* **Talking Points**: "On the web dashboard, under the **Lane Lines** tab, look at the dots:
  * **Blue dots**: Left edge detection.
  * **Pink dots**: Right edge detection.
  * **Green dots**: Estimated centerline.
  * **Purple line**: Crop boundary.
  If the dots are jumping or missing, your threshold or crop parameters need tuning."

#### Slide 36: Parameter Live Updates & Saving (💾)
* **Talking Points**: "You can change parameters in the slide-out drawer on the dashboard. Adjust `white_threshold` or `crop_ratio_base` and watch the dots align immediately. When you are happy with the detection, click the **Save 💾** button. This writes the new values to `params.yaml` on the robot's hard drive so they load automatically next time."

#### Slide 37: 🔧 TRY IT: Calibrate Lane Detection
* **Talking Points**: "Let's calibrate. Keep your robot at your station. Open the dashboard. Manually slide the robot left and right over a lane line. Run `ros2 topic echo /lane_error` and verify that the values shift between negative and positive. Adjust your `white_threshold` until the blue and pink dots cleanly track the edges of the black tape without picking up floor glare."

---

### 🏎️ Part 5: Module C – PID Steering & Adaptive Speed (Slides 38–50)

* **Visuals**: PID steering math block, Kp/Ki/Kd sliders, steering behavior diagrams, and tuning table.
* **Key Topics**: PID steering, adaptive speed reduction, starting parameters, and symptom/fix diagnostics.

#### Slide 38: Module C Title – PID Steering: Control Loop
* **Talking Points**: "Now that our camera can calculate `/lane_error` cleanly, we need to convert that error into motor commands. This is where we implement the PID steering controller."

#### Slide 39: The Steering Control Equation
* **Talking Points**: "Our steering command is calculated using the PID steering formula: `steering = (Kp * error) + (Kd * rate_of_change) + (Ki * total_past_error)`. *(Refer to explanation: PID Controller)*. Let's look at how each of these gains behaves on the track."

#### Slide 40: Proportional Gain (`pid_kp`) – Present Error
* **Talking Points**: "The Proportional gain `pid_kp` is your primary turning force. 
  * If it's **too low**, the robot will turn too slowly and drive off the outer edge of sharp corners.
  * If it's **too high**, the robot will steer violently, shaking left and right even on straight lines."

#### Slide 41: Derivative Gain (`pid_kd`) – Damping
* **Talking Points**: "The Derivative gain `pid_kd` acts as your shock absorber. It dampens the steering when it sees the robot heading back to the center line quickly.
  * If it's **too low**, the robot will overshoot the center and wobble back and forth after exiting a curve.
  * If it's **too high**, the steering will feel sluggish and jerky."

#### Slide 42: Integral Gain (`pid_ki`) – Drift Correction
* **Talking Points**: "The Integral gain `pid_ki` corrects alignment drift. If your robot's steering servo is slightly off-center (so the wheels point 1 degree left when they should be straight), the robot will drift. `pid_ki` detects this constant error over time and pulls the robot back. Keep this value very small (0.01 to 0.02) to avoid making the system unstable."

#### Slide 43: Adaptive Speed in Curves
* **Talking Points**: "If you enter a sharp corner at full speed, the wheels will slip and the camera will lose the lane. To prevent this, RISA-bot uses adaptive speed. The robot slows down automatically when the lane error is large, using this formula: `speed = max(min_turn_speed, forward_speed - (speed_error_scale * |error|))`. This keeps the robot stable during tight turns."

#### Slide 44: Safe Starting Parameters
* **Talking Points**: "Before you put the robot on the track, set these safe, conservative parameters:
  * `forward_speed`: `0.10` m/s (slow and controlled)
  * `pid_kp`: `0.5`
  * `pid_kd`: `0.2`
  * `pid_ki`: `0.01`
  This gives us a safe baseline to observe the robot's behavior."

#### Slide 45: Diagnostics Table: Oscillating
* **Talking Points**: "If your robot shakes left and right rapidly on straight track:
  * **Diagnosis**: Proportional gain `Kp` is too high, or `Kd` is too low.
  * **Fix**: Lower `/auto_driver pid_kp` to `0.4` and raise `/auto_driver pid_kd` to `0.3` via the dashboard."

#### Slide 46: Diagnostics Table: Cutting Corners
* **Talking Points**: "If your robot cuts the inside corner of a curve:
  * **Diagnosis**: The robot is looking too far ahead and turning too early.
  * **Fix**: Raise `crop_ratio_base` to `0.5` or lower to adjust the camera's sightline. If it doesn't turn enough on curves, raise `pid_kp` to `0.8`."

#### Slide 47: Physical Setup of Lane 1
* **Talking Points**: "We are moving to the physical tracks. Lane 1 is ready. It has a straight lane, a curved lane, and leads into the tunnel. We will run our steering tests on the lane section first, before entering the tunnel."

#### Slide 48: Group Rotation Schedule
* **Talking Points**: "We will rotate in pairs. Slot A (Groups 1 and 2) will start on Lane 1. Groups 3, 4, 5, 6, and 7 will remain at their stations. Use this time to prepare your dashboard and check your initial parameters."

#### Slide 49: 🔧 TRY IT: Steering Calibration on Track
* **Talking Points**: "Place your robot on the straight section of Lane 1. Set your starting parameters. Press **Start** on the joystick to enable auto mode. Watch the robot's steering behavior. If it oscillates, lower Kp. If it cuts corners or misses turns, adjust Kp or the crop ratio. Gradual speed increases only when steering is perfectly stable!"

#### Slide 50: Saving Calibration Parameters
* **Talking Points**: "Once your robot drives the lane section smoothly at 0.10 m/s or 0.12 m/s, open the parameters drawer, check your values, and click **Save 💾**. This locks in your progress before we add the tunnel challenge."

---

### 🚇 Part 6: Module D – Tunnel Navigation (Slides 51–60)

* **Visuals**: LiDAR sector classification diagram (Left/Right sectors), polar vs Cartesian coordinates, hysteresis transition diagram, tunnel debug terminal.
* **Key Topics**: LiDAR vs Camera, Wall classification sectors, Lateral & Heading errors, Hysteresis, EMA, and tunnel parameters.

#### Slide 51: Module D Title – Tunnel Navigation: LiDAR Wall Follower
* **Talking Points**: "Welcome to Module D. In this module, we solve the Tunnel challenge. Inside the tunnel, there are no lights and no lane lines. The camera goes blind. We will explain how RISA-bot uses LiDAR to navigate between walls."

#### Slide 52: Why LiDAR? Laser Rangefinding
* **Talking Points**: "LiDAR stands for Light Detection and Ranging. It shoots rotating laser beams and measures how long they take to bounce back, calculating distances. Since it uses its own laser light, it works in pitch-black tunnels. The RISA-bot uses the YDLIDAR Tmini Plus, publishing distance arrays on the `/scan` topic."

#### Slide 53: Coordinate Conversion (Polar to Cartesian)
* **Talking Points**: "Raw LiDAR scan data is in polar coordinates (an array of distances at specific angles). To make math easier, the `tunnel_wall_follower.py` node converts these polar coordinates into Cartesian coordinates (X and Y offsets relative to the robot's center)."

#### Slide 54: Wall Point Classification (Angle Sectors)
* **Talking Points**: "How does the robot know which wall is which? We filter laser points by angle:
  * **Left Wall points**: Angles from `15°` to `120°` relative to the robot's nose.
  * **Right Wall points**: Angles from `-120°` to `-15°` relative to the robot's nose.
  We ignore points directly in front or behind to focus solely on the side walls."

#### Slide 55: Error Calculation (Lateral & Heading Errors)
* **Talking Points**: "To steer, the robot calculates two errors:
  * **Lateral Error**: The difference in distance to the left and right walls. If the left wall is 30cm away and the right wall is 50cm away, the lateral error is +20cm (robot is too close to the left wall).
  * **Heading Error**: The angle of the walls. It tells the robot if the tunnel is curving ahead before the lateral distance actually changes.
  Combining these two errors creates incredibly smooth wall centering."

#### Slide 56: Auto-Switching Hysteresis
* **Talking Points**: "At the tunnel entrance, the LiDAR starts seeing walls. To avoid flickering between camera and LiDAR modes, we use **Hysteresis**. *(Refer to explanation: Hysteresis)*. The state machine requires the robot to see both walls for **3 consecutive frames** to switch to `TUNNEL` mode. It must lose the walls for **3 consecutive frames** to switch back to `LANE_FOLLOW` upon exit."

#### Slide 57: Exponential Moving Average (EMA) Smoothing
* **Talking Points**: "To prevent sudden jerks when the LiDAR misses a point or sees a wall joint, the steering command is filtered through an EMA. *(Refer to explanation: EMA)*. This smooths out high-frequency noise and ensures the robot drives along a clean, centered line."

#### Slide 58: Key Tunnel Parameters
* **Talking Points**: "Here are the parameters for the wall follower node:
  * `/tunnel_wall_follower kp`: Lateral centering strength (default: 5.0).
  * `/tunnel_wall_follower kd`: Damping (default: 0.5).
  * `/tunnel_wall_follower min_wall_points`: Minimum laser hits to confirm a wall (default: 5).
  * `/tunnel_wall_follower target_center_dist`: Shift offset (default: 0.00)."

#### Slide 59: Diagnostics Table: Tunnel Wobbles & Drifts
* **Talking Points**: "If the robot bounces between walls, lower `kp` to `3.0` and raise `kd` to `0.8`. If the robot constantly hugs the left wall, adjust `target_center_dist` by `+0.02`. If it fails to enter tunnel mode at all, lower `min_wall_points` to `3`."

#### Slide 60: 🔧 TRY IT: Run the Tunnel
* **Talking Points**: "Let's test the tunnel. Place your robot at the Lane 1 tunnel entrance. In your terminal, run `ros2 topic echo /tunnel_debug`. Check the lateral error. Watch the dashboard sensor panel change to **IN TUNNEL**. Enable auto mode: the robot should drive in, switch to LiDAR steering, center itself, exit, and switch back to camera lane following automatically!"

---

### ⏱️ Part 7: Module E – Day 1 Full Tuning Run & Wrap-Up (Slides 61–64)

* **Visuals**: Day 1 recap checklist, parameter cheat sheet, and troubleshooting matrix.
* **Key Topics**: Tuning order, troubleshooting, and preparation for Day 2.

#### Slide 61: Module E Title – Day 1 Full Tuning Run
* **Talking Points**: "We have reached our final block of Day 1. Now, we put it all together. Every group will attempt a full end-to-end run on Lane 1: straight line, curves, tunnel transition, centering, and exit."

#### Slide 62: The Golden Rule: The Tuning Order
* **Talking Points**: "When optimizing your robot, you must follow this exact order:
  1. Calibrate `white_threshold` first (get clean dots).
  2. Adjust `crop_ratio_base` (set correct look-ahead range).
  3. Tune steering `pid_kp` and `pid_kd` (stabilize lane following).
  4. Tune tunnel `kp` and `kd` (stabilize wall following).
  5. Speed up `forward_speed` last, in small increments of `0.02` m/s."

#### Slide 63: Parameter Cheat Sheet & Commands
* **Talking Points**: "Keep this cheat sheet handy on your screen or notes. These are the 8 most common parameters you will modify. Keep your changes small—never change multiple parameters between runs, or you won't know which change helped or hurt."

#### Slide 64: Wrap-Up & Day 2 Preview
* **Talking Points**: "Excellent work today! All groups have successfully run the lane and tunnel. Make sure you click **Save 💾** on your dashboards before turning off your robots. Tomorrow, we tackle Day 2: the hill ramp, bumpers, traffic lights, state machine priority control, boom gates, roundabout, and autonomous parking. Charge your batteries tonight, and I will see you tomorrow morning!"

---

## 🛠️ Parameter & Troubleshooting Reference

### Key Parameters Cheat Sheet

| Node | Parameter | Default | Recommended Action |
|---|---|---|---|
| `/auto_driver` | `forward_speed` | `0.15` | Cruising speed (m/s). Keep at `0.10` during calibration. |
| `/auto_driver` | `pid_kp` | `0.8` | Proportional gain. Lower if oscillating; raise if sluggish. |
| `/auto_driver` | `pid_kd` | `0.20` | Derivative gain (dampening). Raise if robot wobbles after exits. |
| `/auto_driver` | `pid_ki` | `0.01` | Integral gain. Keep low to prevent winding up. |
| `/line_follower_camera` | `white_threshold` | `100` | Lane pixel threshold. Calibrate first to match lighting. |
| `/line_follower_camera` | `crop_ratio_base` | `0.55` | Camera crop. Lower to see closer; raise to look ahead. |
| `/tunnel_wall_follower` | `kp` | `5.0` | Centering strength. Lower if bouncing off walls. |
| `/tunnel_wall_follower` | `kd` | `0.5` | Damping. Raise to stabilize. |

### Diagnostic & Troubleshooting Matrix

| Problem | Likely Cause | Corrective Action |
|---|---|---|
| **Robot oscillates rapidly left-right** | `pid_kp` is too high or `pid_kd` is too low | Lower `/auto_driver pid_kp` to `0.4` and raise `pid_kd` to `0.3`. |
| **Robot cuts corners and crashes** | `crop_ratio_base` is too low | Raise `/line_follower_camera crop_ratio_base` to `0.5` or `0.6` so it looks further ahead. |
| **Robot loses the lane lines entirely** | Glare or shadow blinded the camera | Check dashboard **Lane Lines** tab. Raise or lower `/line_follower_camera white_threshold` until only the tape is white. |
| **Robot bounces between tunnel walls** | Tunnel centering gain is too high | Lower `/tunnel_wall_follower kp` to `3.0` and raise `kd` to `0.8`. |
| **Robot drifts to one side in the tunnel** | Calibration offset or wall misalignment | Adjust `/tunnel_wall_follower target_center_dist` in increments of `\pm 0.02`. |
| **Robot flickers at tunnel entry** | Too few laser points detected | Lower `/tunnel_wall_follower min_wall_points` to `3`. |
