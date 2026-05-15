# RISA-Bot: Fresh Robot Deployment Guide

This guide outlines the exact, minimal steps required to provision a brand-new RISA-Bot unit (Sunrise OS / Ubuntu 22.04) from scratch, utilizing the automated dependency installer.

## Prerequisites
- The new robot must be connected to the internet.
- You must be logged into the robot via SSH or a local terminal.

---

### Step 1: Clone the Repository
Clone the `refactor-test` branch of the RISA-Bot repository directly into the home directory. The installer relies on the workspace being named `risabotcar_ws`.

```bash
cd ~
git clone -b refactor-test https://github.com/eemrull/RISA-bot.git risabotcar_ws
```

### Step 2: Run the Automated Setup
Navigate into the newly cloned workspace and run the installer script. This script requires `sudo` privileges to install system packages and rules, so you will be prompted for your password.

```bash
cd ~/risabotcar_ws
bash tools/install_deps.sh
```

**What this script does automatically:**
1. Sources ROS 2 Humble and updates your `~/.bashrc`.
2. Installs all required system dependencies via `apt` (rosdep, colcon, cmake, git-lfs, nlohmann-json, etc.).
3. Pulls down large binary files via `git lfs pull` (like the `libOpenNI2.so` camera libraries).
4. Clones, builds, and installs the **YDLidar-SDK** (C++ LiDAR driver).
5. Clones, builds, and installs **libuvc** and **magic_enum** (C++ Camera drivers).
6. Installs **Rosmaster_Lib** (Hardware/Servo interface).
7. Installs Orbbec Astra USB `udev` rules.
8. Runs `rosdep install` to fetch any remaining ROS 2 specific package dependencies.
9. Runs `colcon build --symlink-install` to compile the entire workspace.
10. Disables FastRTPS shared memory to prevent known DDS crashes on the Sunrise OS.

### Step 3: Apply the Environment
Once the script successfully completes, apply the new bash configurations to your current terminal session.

```bash
source ~/.bashrc
```

### Step 4: Launch the Robot
The robot is now fully provisioned and ready to run. Start the main bringup sequence:

```bash
ros2 launch risabot_automode bringup.launch.py
```

> [!TIP]
> **Dashboard Access**
> Once the launch script is running, open a browser on a device connected to the same network and navigate to:
> `http://<ROBOT_IP>:5000` (e.g., `http://10.77.116.198:5000`)
