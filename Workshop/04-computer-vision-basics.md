# Module 3: Computer Vision Basics

## Learning Objectives

By the end of this module, you will:
- Convert ROS Image messages to OpenCV images
- Filter colors using HSV color space
- Detect lines and calculate lane error
- Understand how the RISA-bot follows lanes

## ROS + OpenCV Bridge

ROS images use the `sensor_msgs/Image` format. OpenCV uses NumPy arrays. We use `cv_bridge` to convert between them:

```python
from cv_bridge import CvBridge
import cv2

bridge = CvBridge()

def image_callback(msg):
    # ROS Image → OpenCV (NumPy array)
    cv_image = bridge.imgmsg_to_cv2(msg, 'bgr8')

    # Now you can use any OpenCV function
    gray = cv2.cvtColor(cv_image, cv2.COLOR_BGR2GRAY)
```

## Understanding HSV Color Space

**RGB** (Red, Green, Blue) is hard to filter — the same color looks different under different lighting.

**HSV** (Hue, Saturation, Value) separates **color** from **brightness**, making it much easier to filter:

| Component | What It Controls | Range |
|---|---|---|
| **H** (Hue) | The color itself | 0–179 |
| **S** (Saturation) | How vivid the color is | 0–255 |
| **V** (Value) | How bright it is | 0–255 |

Common color ranges:

| Color | H Low | H High | S Min | V Min |
|---|---|---|---|---|
| Red (low) | 0 | 10 | 100 | 100 |
| Red (high) | 170 | 179 | 100 | 100 |
| Green | 40 | 80 | 50 | 50 |
| Yellow | 20 | 35 | 100 | 100 |
| White | 0 | 179 | 0 | 150+ |

## Hands-On: Color Filter Node

Create `my_first_pkg/my_first_pkg/color_detector.py`:

```python
#!/usr/bin/env python3
import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Image
from std_msgs.msg import String
from cv_bridge import CvBridge
import cv2
import numpy as np


class ColorDetector(Node):
    def __init__(self):
        super().__init__('color_detector')
        self.bridge = CvBridge()

        # Subscribe to camera
        self.create_subscription(
            Image, '/camera/color/image_raw',
            self.image_callback, 10
        )

        # Publish detected color
        self.color_pub = self.create_publisher(String, '/detected_color', 10)
        self.get_logger().info('Color detector started!')

    def image_callback(self, msg):
        # Convert to OpenCV
        frame = self.bridge.imgmsg_to_cv2(msg, 'bgr8')

        # Convert to HSV
        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)

        # Define color ranges
        colors = {
            'red_low': ((0, 100, 100), (10, 255, 255)),
            'red_high': ((170, 100, 100), (179, 255, 255)),
            'green': ((40, 50, 50), (80, 255, 255)),
        }

        # Check each color
        for name, (lower, upper) in colors.items():
            mask = cv2.inRange(hsv, np.array(lower), np.array(upper))
            pixel_count = cv2.countNonZero(mask)

            if pixel_count > 500:  # Minimum pixels to count as "detected"
                color_name = 'red' if 'red' in name else name
                self.get_logger().info(f'Detected: {color_name} ({pixel_count} pixels)')
                msg_out = String()
                msg_out.data = color_name
                self.color_pub.publish(msg_out)
                return

        # Nothing detected
        msg_out = String()
        msg_out.data = 'none'
        self.color_pub.publish(msg_out)


def main(args=None):
    rclpy.init(args=args)
    node = ColorDetector()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()


if __name__ == '__main__':
    main()
```

## How Lane Following Works

The RISA-bot's `line_follower_camera.py` uses this pipeline:

```text
Camera Image
    ↓
Crop bottom 40%        ← Only look at the road
    ↓
Convert to grayscale
    ↓
Threshold for WHITE    ← white_threshold = 150
    ↓
Column histogram       ← Sum white pixels per column
    ↓
Find peaks             ← Left line and right line positions
    ↓
Calculate midpoint     ← Center between the two lines
    ↓
Error = image_center - midpoint
    ↓
Publish /lane_error    ← Float32 value (-1.0 to 1.0)
```

### Try It

```bash
# Start camera + line follower
ros2 launch astra_camera astra_mini.launch.py
ros2 run risabot_automode line_follower_camera

# Watch the error value
ros2 topic echo /lane_error
```

Place white tape or paper lines in front of the camera — the error value should change as you move them!

## 5. Testing the Color Detector

Now that you understand how HSV works and you've written your `color_detector.py` node, let's put it to the test!

### Step 1: Detect Red and Green
1. Start the camera stream in Terminal 1:
   ```bash
   ros2 launch astra_camera astra_mini.launch.py
   ```
2. Run your new color detector in Terminal 2:
   ```bash
   ros2 run my_first_pkg color_detector
   ```
3. Open a third terminal to watch the output topic:
   ```bash
   ros2 topic echo /detected_color
   ```
4. Hold a bright red object (like an apple or red tape) in front of the camera. The terminal should print `data: red`!
5. Swap it for a bright green object. The terminal should print `data: green`!

### Step 2: Adding a Yellow Filter
Right now, your script only knows what red and green look like. Let's make it detect yellow!
1. Open your `color_detector.py` script.
2. Find the `colors = { ... }` dictionary inside the `image_callback` function.
3. Add the yellow HSV range to the dictionary (refer back to the HSV table above!):
   ```python
        colors = {
            'red_low': ((0, 100, 100), (10, 255, 255)),
            'red_high': ((170, 100, 100), (179, 255, 255)),
            'green': ((40, 50, 50), (80, 255, 255)),
            'yellow': ((20, 100, 100), (35, 255, 255)),  # <-- NEW LINE
        }
   ```
4. Rebuild your workspace using `colcon build`.
5. Run the node again and hold up a yellow object. It should now successfully detect `data: yellow`!

---

**Previous:** [Module 3 — Working with Sensors](03-working-with-sensors.md)
**Next:** [Module 5 — Obstacle Detection](05-obstacle-detection.md)
