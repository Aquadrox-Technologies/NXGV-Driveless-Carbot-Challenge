# Module 2: Introducing the Dashboard

## Learning Objectives

By the end of this module, you will:
- Understand how to interact with a "headless" robot.
- Learn how to start the RISA-bot local dashboard.
- Learn how to connect to the dashboard via a web browser on your laptop.

---

## 1. What is a Headless Robot?

In the previous module, you connected to the robot using **SSH**. This is called a **headless** setup because the robot itself does not have a physical monitor, keyboard, or mouse attached to it. 

While SSH is fantastic for running commands and seeing text output, what happens when we want to look at a live camera feed or see a 2D map of a room? We can't view pictures inside an SSH terminal!

To solve this, the RISA-bot has a built-in **Web Dashboard**. This dashboard acts as your "virtual monitor." It runs on the robot and serves a webpage over the Wi-Fi network directly to your laptop's browser.

---

## 2. Launching the Dashboard

Now that you have built your own `student_ws`, it is time to transition into the main `risabotcar_ws` where the advanced features live.

1. Open a new terminal on your Windows laptop and SSH into the robot:
   ```bash
   ssh sunrise@192.168.x.x
   ```
2. Navigate to the pre-installed workspace and source it:
   ```bash
   cd ~/risabotcar_ws
   source install/setup.bash
   ```
3. Run the dashboard node:
   ```bash
   ros2 run risabot_automode dashboard
   ```

You should see an output saying `Dashboard node starting on http://0.0.0.0:8080`.

---

## 3. Viewing the Dashboard

1. On your Windows laptop, open a web browser (like Chrome, Edge, or Firefox).
2. In the address bar, type `http://192.168.x.x:8080` (replacing `192.168.x.x` with your robot's actual IP address).
3. Hit Enter!

You should now see the RISA-bot web dashboard interface! 

> [!NOTE]
> **Why does it look empty?**
> Right now, the dashboard is running, but the camera and LiDAR nodes are *not* running yet! In the next module, we will learn how to turn on the sensors, and you will see the dashboard automatically populate with real-time video and data!

---

**Previous:** [Module 1 — Introduction to ROS 2](01-introduction-to-ros.md)
**Next:** [Module 3 — Working with Sensors](03-working-with-sensors.md)
