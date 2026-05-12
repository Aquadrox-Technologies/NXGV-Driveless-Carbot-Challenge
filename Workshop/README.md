# RISA-bot Workshop

Hands-on workshop modules for learning ROS 2 using the RISA-bot platform.

## Prerequisites

- Ubuntu 22.04 (on robot or VM)
- ROS 2 Humble installed
- SSH access to the robot (`ssh risabot`)
- Basic Python and Linux terminal knowledge

## Modules

| #   | Topic                                                  | Duration | Description                             |
| --- | ------------------------------------------------------ | -------- | --------------------------------------- |
| 1   | [Introduction to ROS 2](01-introduction-to-ros.md)     | 120 min  | Setup, Nodes, Topics, Launch & Joystick |
| 2   | [Working with Sensors](02-working-with-sensors.md)     | 45 min   | Camera and LiDAR data                   |
| 3   | [Computer Vision Basics](03-computer-vision-basics.md) | 60 min   | OpenCV, HSV filtering, line detection   |
| 4   | [Obstacle Detection](04-obstacle-detection.md)         | 45 min   | LiDAR processing, obstacle avoidance    |
| 5   | [Putting It Together](05-putting-it-together.md)       | 60 min   | Combining modules into a system         |

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
