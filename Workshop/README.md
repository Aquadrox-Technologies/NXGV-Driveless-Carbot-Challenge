# RISA-bot Workshop

Hands-on workshop modules for learning ROS 2 using the RISA-bot platform.

## Prerequisites

- Ubuntu 22.04 (on robot or VM)
- ROS 2 Humble installed
- SSH access to the robot (`ssh risabot`)
- Basic Python and Linux terminal knowledge

## Modules

| #   | Topic                                                        | Duration | Description                                        |
| --- | ------------------------------------------------------------ | -------- | -------------------------------------------------- |
| 0   | [Linux Basics](00-linux-basics.md)                           | 30 min   | Terminal commands, SSH, file navigation             |
| 1   | [Introduction to ROS 2](01-introduction-to-ros.md)           | 120 min  | Setup, Nodes, Topics, & Joystick                   |
| 2   | [Dashboard & Sensors](02-dashboard-and-sensors.md)           | 60 min   | Headless robot monitor, Camera & LiDAR data        |
| 3   | [Lane Following](03-lane-follower.md)                        | 60 min   | Image pipeline, PID control, launch & tuning       |
| 4   | [Obstacle Detection](05-obstacle-detection.md)               | 45 min   | LiDAR processing, obstacle avoidance               |
| 5   | [Tunnel Navigation](05-tunnel-navigation.md)                 | 60 min   | LiDAR wall following, RANSAC, PD control           |
| 6   | [Putting It Together](06-putting-it-together.md)             | 60 min   | Combining modules into a full system               |

## How to Use

- Each module is **self-contained** — pick the ones relevant to your workshop
- **Module 0** is recommended for students new to Linux terminals
- Modules build on each other sequentially, but you can skip ahead
- All exercises use the RISA-bot hardware and codebase
- Code examples reference actual files in this repository

## Setup Before Workshop

```bash
# On the robot
cd ~/risabotcar_ws
git checkout main && git pull
cb
sos
```
