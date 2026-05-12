# Module 3: Working with Sensors

## Learning Objectives

By the end of this module, you will:
- Understand how camera and LiDAR data flows in ROS 2
- View camera images using ROS tools
- Read and interpret LiDAR scan data
- Know which topics the RISA-bot sensors publish on

## RISA-bot Sensors

| Sensor | Model | Topic | Message Type |
|---|---|---|---|
| Camera | Astra Mini | `/camera/color/image_raw` | `sensor_msgs/Image` |
| Depth | Astra Mini | `/camera/depth/image_raw` | `sensor_msgs/Image` |
| LiDAR | YDLiDAR Tmini Plus | `/scan` | `sensor_msgs/LaserScan` |

## Hands-On: Camera

### 1. Start the camera

```bash
ros2 launch astra_camera astra_mini.launch.py
```

### 2. Check camera topics

```bash
ros2 topic list | grep camera
# /camera/color/camera_info
# /camera/color/image_raw
# /camera/depth/image_raw
```

### 3. Check frame rate

```bash
ros2 topic hz /camera/color/image_raw
# Should be ~30 Hz
```

### 4. View the Camera Stream

Because our robot is headless, we cannot use traditional graphical tools like `rqt_image_view`. Instead, we will use the dashboard we learned about in Module 2!

1. Open a **new terminal** and SSH into the robot.
2. Ensure your workspace is sourced:
   ```bash
   cd ~/risabotcar_ws
   source install/setup.bash
   ```
3. Run the dashboard node:
   ```bash
   ros2 run risabot_automode dashboard
   ```
4. Open a web browser on your laptop and go to `http://192.168.x.x:8080`.

Since you already started the camera in Step 1, the dashboard will now automatically display the live video feed!

### 5. Understanding the Image message

```bash
ros2 topic echo /camera/color/image_raw --no-arr
# Shows header (timestamp, frame_id), height, width, encoding
# --no-arr hides the actual pixel data (too large to print)
```

Key fields:
- `height`: 480 pixels
- `width`: 640 pixels
- `encoding`: `rgb8` (3 bytes per pixel: R, G, B)
- `data`: Raw pixel array (480 × 640 × 3 = 921,600 bytes)

## Hands-On: LiDAR

### 1. Start the LiDAR

```bash
ros2 run ydlidar_ros2_driver ydlidar_ros2_driver_node --ros-args \
  -p port:=/dev/serial/by-id/usb-Silicon_Labs_CP2102_USB_to_UART_Bridge_Controller_0001-if00-port0
```

> **Why such a long port path?** The robot has multiple USB devices (LiDAR, motor board, camera). Linux assigns `/dev/ttyUSB0`, `/dev/ttyUSB1`, etc. in random order at boot. If you use `/dev/ttyUSB1` and the order changes, you'll connect to the wrong device and get `Check Sum` errors. The `/dev/serial/by-id/...` path is a **stable symlink** that always points to the LiDAR regardless of boot order.

### 2. Check the scan topic

```bash
ros2 topic hz /scan
# Should be ~8-12 Hz
```

### 3. Read a single scan

```bash
ros2 topic echo /scan --once
```

### 4. Understanding the LaserScan message

```text
header:
  stamp: {sec: ..., nanosec: ...}     ← Timestamp
angle_min: -3.14                       ← Start angle (radians, -180°)
angle_max: 3.14                        ← End angle (radians, +180°)
angle_increment: 0.0087                ← Angle between readings (~0.5°)
range_min: 0.05                        ← Minimum valid range (meters)
range_max: 12.0                        ← Maximum valid range (meters)
ranges: [0.45, 0.46, 0.48, ...]       ← Distance array (one per angle)
```

**Interpreting ranges:**
- `ranges[0]` = distance at `angle_min` (behind-left)
- `ranges[180]` = distance at roughly 0° (straight ahead)
- `ranges[360]` = distance at `angle_max` (behind-right)
- `inf` or values > `range_max` = nothing detected

### 5. Quick distance check

```python
# In Python, to get the distance directly ahead:
import math
front_index = len(ranges) // 2  # Middle of array = straight ahead
front_distance = ranges[front_index]
```

### 6. Visualize LiDAR on the Dashboard

Looking at an array of thousands of numbers in the terminal can be confusing! Luckily, you can use your dashboard to visually see the LiDAR scan.

1. Ensure the `ydlidar_ros2_driver_node` is running in your first terminal.
2. In a second terminal, start your dashboard:
   ```bash
   ros2 run risabot_automode dashboard
   ```
3. Open your laptop's web browser and go to `http://192.168.x.x:8080`.

You will now see the LiDAR canvas drawing red dots in real-time! The dashboard automatically subscribes to the `/scan` topic and converts the distance data into a 2D map of the room around the robot. Try walking around the robot and watch your legs appear on the dashboard!

## 7. Testing Your Sensors

Now that everything is running, let's verify the sensors are working accurately! 

**Testing the LiDAR Range:**
1. While watching your dashboard LiDAR canvas, place your hand about **30cm directly in front** of the robot.
2. You will see a cluster of red dots appear very close to the center of the canvas!
3. Now, move your hand slowly to the right side of the robot. You will see the red dots move along the circular canvas in real-time.

**Understanding the Raw Data:**
1. Go back to your SSH terminal and run a single scan:
   ```bash
   ros2 topic echo /scan --once
   ```
2. Scroll through the giant `ranges:` array.
3. **How many readings are there?** The YDLiDAR Tmini Plus outputs roughly 360 to 400 readings per scan, meaning the length of the `ranges` array is around `400`. Each reading corresponds to a fraction of a degree around the robot!
4. If you place your hand in front of the LiDAR and run the command again, you will notice the numbers near the **middle** of the array (e.g., `ranges[200]`) drop from `inf` down to `0.30` (which is 30 centimeters).

---

**Previous:** [Module 2 — Introducing the Dashboard](02-introducing-the-dashboard.md)
**Next:** [Module 4 — Computer Vision Basics](04-computer-vision-basics.md)
