# Module 6: Putting It Together

## Learning Objectives

By the end of this module, you will:
- Understand how to combine multiple ROS 2 nodes into a working autonomous system
- Write a **launch file** that starts everything in a single command
- Know how to use `TimerAction` to control node startup order
- Learn how to share a central parameter file across all nodes
- Run the full RISA-bot system using `bringup.launch.py` and understand every piece inside it

---

## 1. The Problem: Too Many Terminals!

Over the previous modules, you built and ran individual pieces of the robot:

| Module | What You Built | How You Ran It |
|--------|---------------|----------------|
| 1 | Joystick driver | `ros2 run my_robot_controller joy_driver` |
| 2 | Dashboard + sensors | `ros2 run risabot_automode dashboard` |
| 3 | Lane follower | `ros2 launch risabot_automode lane_test.launch.py` |
| 4 | Obstacle detector | `ros2 run my_first_pkg obstacle_detector` |
| 5 | Tunnel wall follower | `ros2 run risabot_automode tunnel_wall_follower` |

Each time, you had to open **multiple SSH terminals** — one for the camera, one for the LiDAR, one for the dashboard, one for your node... On competition day with 10+ nodes, this becomes completely unmanageable.

The solution is a **launch file**: a single Python script that starts every node in the correct order, with the correct parameters, in one command.

---

## 2. What is a Launch File?

A launch file is a Python script that tells ROS 2: "Start these nodes, in this order, with these settings." Think of it as a conductor's score for an orchestra — it coordinates all the musicians (nodes) so they play together.

```text
Without a launch file:                    With a launch file:

Terminal 1: ros2 launch astra_camera...   Terminal 1: ros2 launch risabot_automode bringup.launch.py
Terminal 2: ros2 run ydlidar...           
Terminal 3: ros2 run risabot... dashboard   ← That's it! One command starts everything.
Terminal 4: ros2 run risabot... line_follower_camera
Terminal 5: ros2 run risabot... auto_driver
Terminal 6: ros2 run joy joy_node
Terminal 7: ros2 run control_servo servo_controller
...
```

---

## 3. Anatomy of a Launch File

Let's look at the structure of a launch file. Open `src/risabot_automode/launch/bringup.launch.py` and follow along.

### 3.1. Imports

Every launch file starts with these imports:

```python
import os
from launch import LaunchDescription
from launch.actions import IncludeLaunchDescription, TimerAction
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch_ros.actions import Node
from ament_index_python.packages import get_package_share_directory
```

| Import | What It Does |
|--------|-------------|
| `LaunchDescription` | The container that holds all nodes to launch |
| `Node` | Defines a single ROS 2 node to start |
| `TimerAction` | Delays a node's start by N seconds |
| `IncludeLaunchDescription` | Includes another launch file (like the camera's) |
| `get_package_share_directory` | Finds where a package is installed |

### 3.2. The `generate_launch_description()` Function

Every launch file **must** contain this function. ROS 2 calls it when you run `ros2 launch`:

```python
def generate_launch_description():
    # Find installed package paths
    astra_pkg = get_package_share_directory('astra_camera')
    risabot_pkg = get_package_share_directory('risabot_automode')
    params_file = os.path.join(risabot_pkg, 'config', 'params.yaml')

    return LaunchDescription([
        # ... list of nodes goes here ...
    ])
```

The `params_file` variable points to a single YAML file (`config/params.yaml`) that contains the settings for **all** nodes. This is how the RISA-bot keeps all tunable parameters in one place — you don't have to edit 10 different files.

### 3.3. Starting a Node

The simplest way to add a node:

```python
Node(
    package='joy',              # Which ROS 2 package?
    executable='joy_node',      # Which executable inside that package?
    name='joy_node',            # Name to give it in the ROS graph
    output='screen',            # Print its log output to your terminal
    parameters=[{               # Pass parameters directly
        'deadzone': 0.12,
        'autorepeat_rate': 20.0,
    }]
),
```

Or load parameters from a shared YAML file:

```python
Node(
    package='risabot_automode',
    executable='line_follower_camera',
    name='line_follower_camera',
    output='screen',
    parameters=[params_file]    # ← Load from params.yaml
),
```

### 3.4. Including Another Launch File

Some packages (like the Astra camera) come with their own launch files. You can include them inside yours:

```python
IncludeLaunchDescription(
    PythonLaunchDescriptionSource(
        os.path.join(astra_pkg, 'launch', 'astra_mini.launch.py')
    )
),
```

This is like saying "run their launch file as part of mine."

### 3.5. Delaying Node Startup with `TimerAction`

Some nodes depend on others being ready first. For example, the `line_follower_camera` needs the camera to be publishing frames before it can start processing images. Without a delay, it would start, see no camera data, and either crash or produce errors.

```python
# Wait 3 seconds for the camera to initialize, then start the line follower
TimerAction(period=3.0, actions=[
    Node(
        package='risabot_automode',
        executable='line_follower_camera',
        name='line_follower_camera',
        output='screen',
        parameters=[params_file]
    ),
]),
```

The `auto_driver` (the brain) waits 5 seconds — it needs ALL sensors ready before it starts making decisions:

```python
# Wait 5 seconds so all perception nodes are publishing
TimerAction(period=5.0, actions=[
    Node(
        package='risabot_automode',
        executable='auto_driver',
        name='auto_driver',
        output='screen',
        parameters=[params_file]
    ),
]),
```

---

## 4. The RISA-bot Bringup Launch File — Full Walkthrough

Here is the full startup sequence of `bringup.launch.py`. Every node you learned about in previous modules is here:

```text
TIME   NODE                      MODULE   PURPOSE
──────────────────────────────────────────────────────────────────
0s     Astra Camera              (2)      Camera hardware driver
0s     YDLiDAR driver            (2)      LiDAR hardware driver
0s     TF publisher              (—)      Coordinate frame link
0s     cmd_safety_controller     (3)      Speed limits & emergency stop
0s     joy_node                  (1)      Joystick input
0s     servo_controller          (1)      Motor & steering hardware
0s     health_monitor            (—)      System health watchdog
0s     dashboard                 (2)      Web UI at :8080
──────────────────────────────────────────────────────────────────
3s     obstacle_avoidance        (4)      LiDAR obstacle detection
3s     obstacle_avoidance_camera (4)      Camera obstacle detection
3s     line_follower_camera      (3)      Lane detection
3s     traffic_light_detector    (—)      Traffic light detection
3s     tunnel_wall_follower      (5)      LiDAR tunnel navigation
──────────────────────────────────────────────────────────────────
5s     auto_driver               (3)      The brain — decides what to do
```

**Notice the three startup groups:**
1. **Immediate (0s):** Hardware drivers and infrastructure — these must start first
2. **Delayed 3s:** Perception nodes — wait for sensors to be publishing
3. **Delayed 5s:** The brain — waits for everything else to be ready

---

## 5. Hands-On: Write Your Own Launch File

Now let's create a launch file for the nodes you built in earlier modules!

### Step 1 — Create the launch directory

```bash
mkdir -p ~/student_ws/src/my_robot_controller/launch
```

### Step 2 — Write the launch file

Create `~/student_ws/src/my_robot_controller/launch/my_bringup.launch.py`:

```python
import os
from launch import LaunchDescription
from launch.actions import TimerAction
from launch_ros.actions import Node
from ament_index_python.packages import get_package_share_directory


def generate_launch_description():
    return LaunchDescription([

        # ==================== HARDWARE ====================

        # Joystick driver (from the joy package)
        Node(
            package='joy',
            executable='joy_node',
            name='joy_node',
            output='screen',
            parameters=[{
                'deadzone': 0.12,
                'autorepeat_rate': 20.0,
            }]
        ),

        # ==================== PERCEPTION ====================
        # Delayed 3s to let the LiDAR and camera initialize

        # Your obstacle detector (from Module 4)
        TimerAction(period=3.0, actions=[
            Node(
                package='my_robot_controller',
                executable='obstacle_detector',
                name='obstacle_detector',
                output='screen',
                parameters=[{
                    'min_distance': 0.40,
                    'scan_angle': 30.0,
                }]
            ),
        ]),

        # ==================== BRAIN ====================
        # Delayed 5s to let perception nodes start first

        # Your simple brain (from Module 4)
        TimerAction(period=5.0, actions=[
            Node(
                package='my_robot_controller',
                executable='simple_brain',
                name='simple_brain',
                output='screen',
                parameters=[{
                    'speed': 0.15,
                    'steering_gain': 0.5,
                }]
            ),
        ]),
    ])
```

### Step 3 — Register the launch file in `setup.py`

For ROS 2 to find your launch file, you need to tell `setup.py` to install it. Edit `~/student_ws/src/my_robot_controller/setup.py`:

```python
import os
from glob import glob
from setuptools import setup

package_name = 'my_robot_controller'

setup(
    name=package_name,
    # ... existing fields ...
    data_files=[
        ('share/ament_index/resource_index/packages', ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
        # ADD THIS LINE to install launch files:
        (os.path.join('share', package_name, 'launch'), glob('launch/*.launch.py')),
    ],
    # ... rest of setup ...
)
```

> [!IMPORTANT]
> Don't forget the `import os` and `from glob import glob` at the top of `setup.py`!

### Step 4 — Build and run

```bash
cd ~/student_ws
colcon build --packages-select my_robot_controller
source install/setup.bash

# Launch everything with one command!
ros2 launch my_robot_controller my_bringup.launch.py
```

You should see all three nodes start up in sequence — joystick immediately, obstacle detector after 3 seconds, and the brain after 5 seconds.

---

## 6. Adding Sensor Nodes to Your Launch File

Your launch file above starts your custom nodes, but the camera and LiDAR still need to be launched separately. Let's fix that by adding them:

```python
# Add these imports at the top:
from launch.actions import IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource

def generate_launch_description():
    # Find the astra_camera package
    astra_pkg = get_package_share_directory('astra_camera')
    
    # LiDAR serial port
    lidar_port = '/dev/serial/by-id/usb-Silicon_Labs_CP2102_USB_to_UART_Bridge_Controller_0001-if00-port0'

    return LaunchDescription([

        # Camera (include its own launch file)
        IncludeLaunchDescription(
            PythonLaunchDescriptionSource(
                os.path.join(astra_pkg, 'launch', 'astra_mini.launch.py')
            )
        ),

        # LiDAR
        Node(
            package='ydlidar_ros2_driver',
            executable='ydlidar_ros2_driver_node',
            name='ydlidar_ros2_driver_node',
            output='screen',
            parameters=[{
                'port': lidar_port,
                'baudrate': 230400,
                'frame_id': 'laser_frame',
                'frequency': 10.0,
            }],
        ),

        # ... your other nodes with TimerAction delays ...
    ])
```

Now `ros2 launch my_robot_controller my_bringup.launch.py` starts **everything** — sensors, perception, and control — in one command. No more juggling 7 terminals!

---

## 7. Running the Full RISA-bot System

Now that you understand how launch files work, let's run the real thing:

```bash
cd ~/risabotcar_ws
source install/setup.bash
ros2 launch risabot_automode bringup.launch.py
```

You will see a stream of log messages as each node initializes. Watch for these key messages:

```
[ydlidar_ros2_driver_node]: Now lidar is scanning...
[servo_controller]: ✅ Rosmaster Connected (V9 Competition)
[dashboard]: Dashboard live!
[dashboard]:   → http://10.118.151.222:8080
[line_follower_camera]: Line Follower Camera: Ready
[tunnel_wall_follower]: Tunnel Wall Follower started (Centerline Path)
[auto_driver]: Auto Driver Node Starting (Competition Mode)...
[auto_driver]: State: MANUAL
```

Once `auto_driver` prints `State: MANUAL`, the full system is running.

### Verify on the Dashboard

1. Open `http://<robot_ip>:8080` in your browser.
2. You should see:
   - **Status:** Connected (green dot)
   - **State:** MANUAL
   - **LiDAR canvas:** Showing real-time distance dots
   - **Camera:** Click "Enable Camera" to see the live feed
3. Press **Start** on the joystick to toggle between MANUAL and AUTO mode.

---

## 8. Compare: Your Launch File vs RISA-bot's

| Feature | Your `my_bringup.launch.py` | RISA-bot's `bringup.launch.py` |
|---------|---------------------------|-------------------------------|
| Nodes | 3 (joy, obstacle, brain) | 13+ (sensors, perception, control, monitoring) |
| Sensor drivers | Not included | Camera + LiDAR + TF |
| Parameters | Inline values | Central `params.yaml` file |
| Delays | 3s and 5s groups | Same pattern! |
| Safety | None | `cmd_safety_controller` enforces limits |
| Monitoring | None | `dashboard` + `health_monitor` |

The core pattern is identical: **start hardware → wait → start perception → wait → start the brain**. The RISA-bot just has more nodes and a centralized parameter file.

---

## 9. Exercises

### Exercise 1: Add the Dashboard to Your Launch File

Add the RISA-bot dashboard to your `my_bringup.launch.py`:

```python
# Add this to your LaunchDescription list:
Node(
    package='risabot_automode',
    executable='dashboard',
    name='dashboard',
    output='screen',
),
```

Rebuild and launch. Open the dashboard in your browser — you now have a visual monitor for your system!

### Exercise 2: Create a Parameter File

Instead of hardcoding parameters inline, create a `config/params.yaml` for your package:

```yaml
# ~/student_ws/src/my_robot_controller/config/params.yaml
obstacle_detector:
  ros__parameters:
    min_distance: 0.40
    scan_angle: 30.0

simple_brain:
  ros__parameters:
    speed: 0.15
    steering_gain: 0.5
```

Then update your launch file to use it:

```python
risabot_pkg = get_package_share_directory('my_robot_controller')
params_file = os.path.join(risabot_pkg, 'config', 'params.yaml')

# In each Node:
parameters=[params_file]
```

> [!TIP]
> Don't forget to register the `config/` folder in your `setup.py`'s `data_files` list, just like you did with `launch/`:
> ```python
> (os.path.join('share', package_name, 'config'), glob('config/*.yaml')),
> ```

### Exercise 3: Add a New Node to the System

Create a simple "status printer" node that subscribes to `/my_obstacle` and `/lane_error` and prints a summary every second. Add it to your launch file with a 3-second delay.

**Challenge:** Can you make it publish a `String` message on `/system_status` summarizing the robot's current situation (e.g. "Lane OK, No obstacle" or "Lane lost, Obstacle at 0.3m")?

---

## 10. Troubleshooting

| Symptom | Likely Cause | Fix |
|---------|-------------|-----|
| `[ERROR] Package 'xyz' not found` | Package not built or not sourced | Run `colcon build` and `source install/setup.bash` |
| Node starts but no data flows | Started too early, sensors not ready | Add `TimerAction` delay |
| `Address already in use` (dashboard) | Old dashboard process still running | `pkill -f dashboard` then relaunch |
| Launch file not found | Not registered in `setup.py` | Add the `data_files` line for `launch/` |
| Parameters not loading from YAML | File not installed | Add `config/` to `data_files` in `setup.py` |

---

## 11. What You've Learned

In this module you brought everything together:

```text
Individual nodes  →  Launch file  →  One-command startup  →  Full autonomous system
```

You learned that:
- A **launch file** is a Python script that starts multiple nodes in one command
- **`TimerAction`** delays nodes so dependencies (like sensors) start first
- **`IncludeLaunchDescription`** lets you nest other packages' launch files inside yours
- A **shared parameter file** (`params.yaml`) keeps all settings in one place
- The RISA-bot's `bringup.launch.py` uses the exact same patterns you just learned — just with more nodes
- The startup order follows a clear pattern: **hardware → perception → brain**

---

**Previous:** [Module 5 — Tunnel Navigation](05-tunnel-navigation.md)

🎉 **Congratulations!** You've completed all 6 modules of the RISA-bot Workshop!
