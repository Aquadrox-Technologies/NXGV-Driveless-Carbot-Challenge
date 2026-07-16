# Module 7: Computer Vision & Hardware-Accelerated AI (BPU)

## Learning Objectives

By the end of this module, you will:
- Understand the role of a **BPU (Brain Processing Unit)** in running deep learning models at high frame rates (30+ FPS) on edge devices
- Learn how the custom-trained YOLOv5 BPU model detects **signage** and **traffic lights** in `risabotcar_ws`
- Trace the complete **BPU working pipeline** (Preprocessing, BPU Forward Pass, Non-Maximum Suppression, and Hysteresis)
- Design and implement **AI Trigger Points** using a "Priming Window" architecture (using the Hill Sign as a reference)
- Learn how to run the BPU diagnostic and live validation scripts inside the `tools/bpu_model/` folder
- Understand how to build a camera-based **Boom Gate Detector** using OpenCV HSV color thresholding and contours

---

## 1. AI on the Edge: The Brain Processing Unit (BPU)

When a mobile robot runs object detection (like YOLOv5) on a standard CPU, it can only process 1 to 2 frames per second (FPS), leading to slow reaction times and high CPU utilization. 

To solve this, the RISA-bot computer (RDK X5) is equipped with a **BPU (Brain Processing Unit)**. The BPU is a hardware accelerator specialized in matrix calculations. It processes a $640 \times 640$ YOLOv5 model at **30+ FPS** while keeping the CPU load extremely low.

In `risabotcar_ws`, the BPU model is stored as a quantized binary file:
`file:///c:/Users/Lenovo/Downloads/Kerja/RISA-bot-1/tools/bpu_model/model_output/risabot_signs_640x640_nv12.bin`

---

## 2. The Custom Dataset & BPU Compilation Pipeline

Before a neural network runs at high speeds on the robot, it undergoes a multi-stage compilation and quantization process:

```
[ Roboflow Dataset ] ──▶ [ Train YOLOv5 PyTorch ] ──▶ [ Export ONNX ] ──▶ [ Horizon Toolchain (Quantize & Compile) ] ──▶ [ BPU .bin Model ]
```

1. **Dataset Collection**: Images of traffic lights and competition signs (Hill, Parking, Bumper, Obstacle) are captured on the physical track and annotated using Roboflow.
2. **Training**: A standard YOLOv5 model (usually `yolov5s` or `yolov5n` for speed) is trained on the custom dataset and exported to the **ONNX** format.
3. **Quantization & Compilation**: Using the Horizon Toolchain (`hb_mapper`), the ONNX model weights are quantized from FP32 to **INT8**. This quantization allows the BPU to perform integer matrix multiplications extremely fast with minimal accuracy loss.
4. **NV12 Native Format**: The compiler configures the model to accept the **NV12** (YUV420sp) color format natively, bypassing expensive BGR decoding steps at runtime.

---

## 3. The Runtime BPU Inference Pipeline

Open `src/risabot_automode/risabot_automode/signage_detector.py` and observe the pipeline:

```
[ Camera Frame BGR ] ──▶ [ Resize to 640x640 ] ──▶ [ Convert to NV12 ] ──▶ [ BPU Forward Pass ] ──▶ [ NMS Filtering ] ──▶ [ Trigger Flag Publisher ]
```

### 3.1. Preprocessing (BGR to NV12)
The BPU hardware expects images in the **NV12** format (YUV420sp, separating brightness Y from chroma UV). The camera output is standard BGR. The node resizes the BGR frame to $640 \times 640$ and reformats the byte layout:
```python
def bgr_to_nv12(self, bgr640: np.ndarray) -> np.ndarray:
    # 1. Convert to YUV I420 (960x640 layout)
    yuv = cv2.cvtColor(bgr640, cv2.COLOR_BGR2YUV_I420)

    # 2. Extract planar components
    y = yuv[0:640, :]
    u = yuv[640:800, :]
    v = yuv[800:960, :]

    # 3. Interleave U and V for NV12
    uv_planar = np.stack([u.ravel(), v.ravel()], axis=1).ravel().reshape(320, 640)

    # 4. Stack Y and interleaved UV planes
    return np.vstack((y, uv_planar))
```

### 3.2. BPU Forward Pass
The inference is run using the Horizon `pyeasy_dnn` library. The call runs directly on the BPU hardware accelerator:
```python
outputs = self.model.forward([nv12])
pred = outputs[0].buffer  # Raw predictions tensor
```

### 3.3. Postprocessing & Non-Maximum Suppression (NMS)
The output buffer contains thousands of anchor bounding boxes, confidences, and class probabilities. The node:
1. Filters out predictions below the class-specific confidence thresholds using vectorized NumPy arrays (e.g., `self._class_thresh_array`).
2. Runs a vectorized **NMS (Non-Maximum Suppression)** algorithm to merge overlapping bounding boxes pointing to the same object.
3. Performs hybrid HSV classification on traffic lights to resolve the active state.
4. Publishes Boolean/String state updates over ROS 2 topics.

---

## 4. AI Trigger Points: The "Priming Window" Architecture

> [!IMPORTANT]
> **Instant Triggering is a Common Failure Mode:**
> Initiating robot behavior (like stopping or turning) the exact millisecond the camera sees a sign is highly unreliable. Network delays, momentary false positives, or seeing a sign from an adjacent lane can cause the robot to trigger prematurely or crash.

To ensure stability, RISA-bot uses a **Priming Window** (Gated Trigger) architecture. We combine AI computer vision (perception) with physical validation (sensors).

### Case Study: The Hill Climb Trigger
Observe how the Hill Climb is sequenced in `src/risabot_automode/risabot_automode/auto_driver.py`:

```
                       [ BPU CAMERA ]
                             │
                      Hill Sign Detected
                             │
                             ▼
                    [ PRIMING WINDOW ] 
              (Starts 8-second countdown timer)
              (Reduces IMU pitch threshold)
                             │
                             ▼
                    [ PHYSICAL CHECK ] ──(No Slope)──▶ Keep driving normal
                 (Exceeds lowered pitch?)
                             │
                       (Slope Sensed)
                             │
                             ▼
                     [ HILL CLIMB STATE ]
                       (Boost motors)
```

1. **Perception**: The camera detects the `Hill_signboard` sign. The `signage_detector` publishes `True` to `/hill_sign_detected`.
2. **Priming**: When `auto_driver` receives this, it opens an 8-second **Priming Window** by setting `self._hill_primed = True`.
3. **Parameter Modulation**: During this window, the robot lowers the pitch threshold required to trigger the hill climbing mode (e.g., from 8.0° to 5.0°). This primes the robot to react immediately upon hitting the incline.
4. **Physical Validation**: The robot continues driving normal lane-follow. It only enters the `HILL` state when the **physical IMU pitch sensor** confirms that the pitch angle has crossed the threshold.
5. **Execution**: Once physical pitch is validated, the state machine triggers the `HILL` state, boosting motor speeds and keeping steering straight (`hill_steer_scale = 0.4`).
6. **Time-out Reset**: If the 8-second window expires and the IMU never registers a pitch increase (e.g., the sign was a false positive or far away), the prime window resets to `False` safely.

### How to Implement a Gated Trigger in Your Code
When building custom behaviors, use this general programming blueprint:

```python
class CustomTriggerNode(Node):
    def __init__(self):
        super().__init__('custom_trigger_node')
        self.ai_primed = False
        self.prime_start_time = 0.0
        self.prime_duration = 5.0  # 5-second window
        
        self.create_subscription(Bool, '/ai_detection', self.ai_callback, 10)
        self.create_subscription(Float32, '/sensor_reading', self.sensor_callback, 10)

    def ai_callback(self, msg):
        if msg.data:
            self.ai_primed = True
            self.prime_start_time = self.get_clock().now().nanoseconds / 1e9
            self.get_logger().info("AI Detection Received: Gated Trigger Primed.")

    def sensor_callback(self, msg):
        now = self.get_clock().now().nanoseconds / 1e9
        
        # 1. Check if the priming window is still active
        window_active = self.ai_primed and (now - self.prime_start_time <= self.prime_duration)
        if not window_active:
            self.ai_primed = False  # Reset
            return

        # 2. Check if the physical condition is met (e.g. sensor value > threshold)
        physical_triggered = msg.data > 4.5
        
        # 3. Combine both constraints to trigger the behavior
        if window_active and physical_triggered:
            self.execute_behavior()

    def execute_behavior(self):
        self.get_logger().info("Gated Trigger Fired! Executing target behavior...")
```

---

## 5. Hands-On: BPU Model Diagnostics in `risabotcar_ws`

The workspace contains two diagnostic scripts in `tools/bpu_model/` designed to check and test the BPU model in isolation.

### Exercise 1: Run BPU Model Verification
Run the offline verification script to test imports, load the model file, inspect tensor layout, and perform a dry forward pass using a dummy image.

1. SSH into the robot and navigate to the directory:
   ```bash
   cd ~/risabotcar_ws/tools/bpu_model
   ```
2. Run the script:
   ```bash
   python3 verify_bpu.py
   ```
3. Observe the output. It should print out:
   *   Successful load confirmation.
   *   Model input tensor shape: `1x3x640x640` (NCHW layout).
   *   Model output prediction buffer shape.
   *   Inference confirmation.

```text
=== BPU Model Verification Script ===
Successfully imported pyeasy_dnn from hobot_dnn_rdkx5
Attempting to load BPU model from: /home/sunrise/risabot_signs_640x640_nv12.bin
SUCCESS: BPU model loaded successfully.

--- Model Inputs ---
  Input[0]: name='images', shape=[1, 3, 640, 640], layout='NCHW', type=IMG_TYPE_NV12
...
=== Verification Successful! BPU model is fully functional. ===
```

---

### Exercise 2: Run Live BPU Inference Diagnostic
The second script, `verify_live.py`, subscribes to a single live camera frame, runs it through the BPU, and prints out detailed statistics of the highest-scoring anchors.

1. In Terminal 1, ensure the camera is running:
   ```bash
   ros2 launch astra_camera bringup.launch.py
   ```
2. In Terminal 2, run the diagnostic:
   ```bash
   cd ~/risabotcar_ws/tools/bpu_model
   ```
3. Run the live diagnostic script:
   ```bash
   python3 verify_live.py
   ```
4. Hold a sign (like the parking signboard or hill signboard) in front of the camera.
5. The script will output raw diagnostic measurements:
   *   Highest anchor confidence.
   *   Class probabilities.
   *   Number of anchors passing different confidence thresholds (`0.01`, `0.10`, `0.30`, etc.).

This allows you to verify that the camera is publishing and that the BPU is outputting high confidence numbers before you launch the full autonomous driver.

---

## 6. Designing a Computer Vision Boom Gate Detector

The standard RISA-bot uses a LiDAR-based boom gate detector, which looks for a horizontal line of laser points. However, we can also build a **Camera-based Boom Gate Detector** using OpenCV!

A boom gate arm typically has bright red/orange and white stripes. We can isolate it using an OpenCV pipeline:

```text
     [ RAW IMAGE ]             [ CROP REGION ]           [ HSV THRESHOLD ]          [ FIND CONTOURS ]
  ┌─────────────────┐         ┌───────────────┐         ┌───────────────┐          ┌───────────────┐
  │    [GATE ARM]   │  ──▶    │   [GATE ARM]  │  ──▶    │   ■ ■ ■ ■ ■   │   ──▶    │ ┌───────────┐ │  (Bounding
  │      🚗         │         └───────────────┘         └───────────────┘          │ └───────────┘ │   Box Aspect
  └─────────────────┘                                                              └───────────────┘   Ratio > 3.0)
```

1. **Crop Region of Interest**: Crop the upper-middle frame where a gate arm appears when the robot stops.
2. **HSV Color Threshold**: Filter for orange/red pixels:
   *   Lower Orange: `[5, 100, 100]`
   *   Upper Orange: `[25, 255, 255]`
3. **Morphological Closing**: Use a horizontal rectangular structuring element (e.g. size `(20, 3)`) to merge the separated colored stripes into a single contour.
4. **Bounding Box Aspect Ratio**: Find the outline of the shape. If the width of its bounding box is significantly larger than its height (e.g., aspect ratio $> 3.0$), the gate is **CLOSED**. If the shape is vertical or missing, the gate is **OPEN**.

---

### Exercise 3: Run the CV Gate Detector Node
Let's run a custom CV-based boom gate detector node on the robot using the topics configured in `risabotcar_ws`.

Create `~/student_ws/src/my_robot_controller/my_robot_controller/cv_gate_detector.py`:

```python
#!/usr/bin/env python3
import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Image
from std_msgs.msg import Bool
from cv_bridge import CvBridge
import cv2
import numpy as np

class CVGateDetector(Node):
    def __init__(self):
        super().__init__('cv_gate_detector')
        self.bridge = CvBridge()
        
        # Subscribe to camera raw feed
        self.create_subscription(Image, '/camera/color/image_raw', self.image_callback, 10)
        
        # Publish gate status: True = Open (clear), False = Closed (blocked)
        self.gate_pub = self.create_publisher(Bool, '/boom_gate_open', 10)
        self.debug_pub = self.create_publisher(Image, '/camera/debug/boom_gate', 10)

        # Orange/Red HSV boundaries for the barrier arm
        self.lower_orange = np.array([5, 100, 100])
        self.upper_orange = np.array([25, 255, 255])
        
        self.get_logger().info('CV Gate Detector node initialized.')

    def image_callback(self, msg):
        try:
            bgr = self.bridge.imgmsg_to_cv2(msg, 'bgr8')
            h, w = bgr.shape[:2]

            # Crop Region of Interest (only look at middle area in front of the robot)
            roi = bgr[int(h*0.3):int(h*0.75), int(w*0.2):int(w*0.8)]
            hsv = cv2.cvtColor(roi, cv2.COLOR_BGR2HSV)

            # Mask for orange barrier arm
            mask = cv2.inRange(hsv, self.lower_orange, self.upper_orange)

            # Close gaps between stripes
            kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (20, 3))
            mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)

            # Find contours
            contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            
            gate_open = True
            debug_img = roi.copy()

            for cnt in contours:
                area = cv2.contourArea(cnt)
                if area < 300:  # ignore small noise
                    continue

                # Get bounding box
                x, y, w_box, h_box = cv2.boundingRect(cnt)
                aspect_ratio = float(w_box) / h_box

                # Closed barrier is horizontal rectangle
                if aspect_ratio > 3.0:
                    gate_open = False
                    cv2.rectangle(debug_img, (x, y), (x+w_box, y+h_box), (0, 0, 255), 3)
                    cv2.putText(debug_img, "GATE CLOSED", (x, y-10), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)
                    break

            if gate_open:
                cv2.putText(debug_img, "PATH CLEAR", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)

            # Publish gate state
            msg_out = Bool()
            msg_out.data = gate_open
            self.gate_pub.publish(msg_out)

            # Publish debug image
            self.debug_pub.publish(self.bridge.cv2_to_imgmsg(debug_img, encoding='bgr8'))

        except Exception as e:
            self.get_logger().error(f'Error processing frame: {e}')

def main(args=None):
    rclpy.init(args=args)
    node = CVGateDetector()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()

if __name__ == '__main__':
    main()
```

1. Register in `~/student_ws/src/my_robot_controller/setup.py`:
   ```python
   'cv_gate_detector = my_robot_controller.cv_gate_detector:main',
   ```
2. Build and run:
   ```bash
   cd ~/student_ws && colcon build --packages-select my_robot_controller
   source install/setup.bash
   ros2 run my_robot_controller cv_gate_detector
   ```
3. Test by showing a red/orange card to the camera and observing `/boom_gate_open` topic.

---

## 7. Live Parameter Tuning in `risabotcar_ws`

The BPU signage detector has parameters you can modify live to adapt to room conditions:
```bash
# Verify the current signage detector parameter values
ros2 param dump /signage_detector

# Adjust confidence threshold if detection is slow or has false positives
ros2 param set /signage_detector conf_threshold 0.35

# Adjust minimum required sign width to avoid premature triggers
ros2 param set /signage_detector min_parking_sign_width 80
```

---

## 8. Troubleshooting

| Symptom | Likely Cause | Fix |
|---|---|---|
| **BPU script fails to import libraries** | Script run on local PC instead of RDK board | The BPU libraries are only available on the robot. Always run BPU diagnostic scripts via SSH |
| **`verify_live.py` hangs on waiting for frame** | Camera driver node not running | Ensure the camera driver is running: `ros2 launch astra_camera bringup.launch.py` |
| **CV Gate detector detects floor/boxes as gate** | HSV boundaries are too wide | Increase the Saturation (`sat_min`) or Value (`val_min`) thresholds to ignore background details |

---

**Previous:** [Module 6 — Autonomous Parking](06-autonomous-parking.md)

🎉 **Congratulations!** You have completed all 8 modules of the RISA-bot Workshop!
