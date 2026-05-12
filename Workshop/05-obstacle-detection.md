# Module 4: Obstacle Detection

## Learning Objectives

By the end of this module, you will:

- Process LiDAR scan data to detect obstacles
- Write a simple obstacle detection node
- Understand how detection distance and angle affect behavior
- See how the RISA-bot uses LiDAR for obstacle avoidance

## LiDAR Data Recap

The `/scan` topic gives us an array of distances:

```text
ranges: [0.45, 0.46, ..., inf, ..., 0.82]
         ↑                              ↑
    angle_min (-π)               angle_max (+π)
```

Each element is the distance to the nearest object at that angle. We need to check the **front** of the robot for obstacles.

## Hands-On: Simple Obstacle Detector

Create `my_first_pkg/my_first_pkg/obstacle_detector.py`:

```python
#!/usr/bin/env python3
import rclpy
import math
from rclpy.node import Node
from sensor_msgs.msg import LaserScan
from std_msgs.msg import Bool


class ObstacleDetector(Node):
    def __init__(self):
        super().__init__('obstacle_detector')

        # Parameters
        self.declare_parameter('min_distance', 0.40)   # meters
        self.declare_parameter('scan_angle', 30.0)      # degrees to check

        self.min_distance = self.get_parameter('min_distance').value
        self.scan_angle = self.get_parameter('scan_angle').value

        # Subscribe to LiDAR
        self.create_subscription(LaserScan, '/scan', self.scan_callback, 10)

        # Publish obstacle detection
        self.obstacle_pub = self.create_publisher(Bool, '/my_obstacle', 10)

        self.get_logger().info(
            f'Obstacle detector started! '
            f'Distance: {self.min_distance}m, Angle: ±{self.scan_angle}°'
        )

    def scan_callback(self, msg):
        # Calculate which indices correspond to the front arc
        angle_rad = math.radians(self.scan_angle)
        num_readings = len(msg.ranges)
        center = num_readings // 2

        # Indices for ±scan_angle degrees around center
        spread = int(angle_rad / msg.angle_increment)
        start = max(0, center - spread)
        end = min(num_readings, center + spread)

        # Check for obstacles in the front arc
        obstacle_found = False
        closest = float('inf')

        for i in range(start, end):
            dist = msg.ranges[i]
            if msg.range_min < dist < self.min_distance:
                obstacle_found = True
                closest = min(closest, dist)

        # Publish result
        result = Bool()
        result.data = obstacle_found
        self.obstacle_pub.publish(result)

        if obstacle_found:
            self.get_logger().warn(
                f'OBSTACLE at {closest:.2f}m!',
                throttle_duration_sec=0.5
            )


def main(args=None):
    rclpy.init(args=args)
    node = ObstacleDetector()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()


if __name__ == '__main__':
    main()
```

### Register, build, run

````python
# In setup.py
'obstacle_detector = my_first_pkg.obstacle_detector:main',
```bash
cd ~/risabotcar_ws
cbp my_first_pkg
sos
````

### Terminal 1: LiDAR

ros2 run ydlidar_ros2_driver ydlidar_ros2_driver_node

### Terminal 2: Your detector

ros2 run my_first_pkg obstacle_detector

### Terminal 3: Watch

ros2 topic echo /my_obstacle

````

Walk in front of the LiDAR — you should see `data: true` when you're closer than 0.4m!

## Making the Robot Stop

Now combine obstacle detection with motor control:

```python
# In your joy_driver or auto node:
def obstacle_callback(self, msg):
    self.obstacle_detected = msg.data

def publish_velocity(self):
    twist = Twist()
    if self.obstacle_detected:
        # STOP!
        twist.linear.x = 0.0
        twist.angular.z = 0.0
    else:
        # Normal driving
        twist.linear.x = self.desired_speed
        twist.angular.z = self.desired_turn
    self.cmd_pub.publish(twist)
````

## Tuning Parameters

```bash
# Change detection distance live
ros2 param set /obstacle_detector min_distance 0.30

# Change scan angle
ros2 param set /obstacle_detector scan_angle 45.0
```

| Parameter      | Effect of Increasing    | Effect of Decreasing           |
| -------------- | ----------------------- | ------------------------------ |
| `min_distance` | Detects earlier (safer) | Detects later (closer pass)    |
| `scan_angle`   | Wider detection (safer) | Narrower (only straight ahead) |

## How RISA-bot Does It

The real `obstacle_avoidance` package checks a ±30° front arc and publishes `Bool` on `/obstacle_front`. The `auto_driver` subscribes and stops when `True`.

See: `src/obstacle_avoidance/obstacle_avoidance/obstacle_avoidance.py`

## Testing Your Obstacle Detector

Now let's test your code and experiment with ROS 2 parameters!

### Step 1: Basic Testing
1. Make sure the LiDAR is running: `ros2 run ydlidar_ros2_driver ydlidar_ros2_driver_node`
2. Run your obstacle detector: `ros2 run my_first_pkg obstacle_detector`
3. Walk towards the front of the robot. As soon as you cross the `0.40m` threshold, your terminal will start warning you!

### Step 2: Live Parameter Tuning
One of the best features of ROS 2 is that you can change parameters *while the code is running*.
1. Leave your `obstacle_detector` running.
2. Open a new terminal and change the `min_distance` parameter to 60cm (0.60m):
   ```bash
   ros2 param set /obstacle_detector min_distance 0.60
   ```
3. Walk towards the robot again. Notice how it detects you much earlier now!

### Step 3: Upgrading the Code (Publishing Distance)
Right now, the node only publishes `True` or `False`. Let's modify it to actually publish the exact distance to the closest obstacle so the robot's brain knows *how close* the object is!

1. Open `obstacle_detector.py`.
2. Change the publisher type from `Bool` to `Float32`:
   ```python
   from std_msgs.msg import Float32  # Update the import at the top!
   
   # Update the publisher line in __init__:
   self.obstacle_pub = self.create_publisher(Float32, '/my_obstacle', 10)
   ```
3. Update the bottom of the `scan_callback` function to publish the distance:
   ```python
        # Publish result
        result = Float32()
        if obstacle_found:
            result.data = closest
        else:
            result.data = -1.0  # -1 means the path is clear!
            
        self.obstacle_pub.publish(result)
   ```
4. Rebuild your workspace (`colcon build`), restart your node, and run `ros2 topic echo /my_obstacle`. You will now see the exact distance streaming to your screen!

---

**Previous:** [Module 4 — Computer Vision Basics](04-computer-vision-basics.md)
**Next:** [Module 6 — Putting It Together](06-putting-it-together.md)
