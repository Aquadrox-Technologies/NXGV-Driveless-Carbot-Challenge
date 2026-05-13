# RISA-bot Workshop

Hands-on workshop modules for learning ROS 2 using the RISA-bot platform.

## Prerequisites

- Ubuntu 22.04 (on robot or VM)
- ROS 2 Humble installed
- SSH access to the robot (`ssh risabot`)
- Basic Python and Linux terminal knowledge

## Modules

| #   | Topic                                                      | Duration | Description                                        |
| --- | ---------------------------------------------------------- | -------- | -------------------------------------------------- |
| 1   | [Introduction to ROS 2](01-introduction-to-ros.md)         | 120 min  | Setup, Nodes, Topics, & Joystick                   |
| 2   | [Introducing the Dashboard](02-introducing-the-dashboard.md) | 20 min   | Setting up the headless robot monitor              |
| 3   | [Working with Sensors](03-working-with-sensors.md)         | 45 min   | Camera and LiDAR data                              |
| 4   | [Lane Following](04-lane-follower.md)                      | 60 min   | Image pipeline, PID control, launch & tuning       |
| 5   | [Computer Vision Basics](04-computer-vision-basics.md)     | 60 min   | OpenCV, HSV filtering, color detection             |
| 6   | [Obstacle Detection](05-obstacle-detection.md)             | 45 min   | LiDAR processing, obstacle avoidance               |
| 7   | [Putting It Together](06-putting-it-together.md)           | 60 min   | Combining modules into a full system               |

## How to Use

- Each module is **self-contained** — pick the ones relevant to your workshop
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
