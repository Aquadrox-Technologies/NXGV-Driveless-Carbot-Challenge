#!/usr/bin/env python3
"""
PID Logger Node for RISA-bot.
Subscribes to:
  - /lane_error (std_msgs/Float32)
  - /cmd_vel_auto_raw (geometry_msgs/Twist)
  - /auto_mode (std_msgs/Bool)

Logs data to /home/sunrise/pid_log.csv when auto mode is active.
"""

import os
import sys
import csv
import time
import rclpy
from rclpy.node import Node
from rclpy.qos import QoSPresetProfiles
from std_msgs.msg import Bool, Float32
from geometry_msgs.msg import Twist

class PidLogger(Node):
    def __init__(self):
        super().__init__('pid_logger')
        self.get_logger().info('RISA-bot PID Logger starting...')
        
        # State variables
        self.latest_lane_error = 0.0
        self.auto_mode_active = False
        
        self.log_file = None
        self.log_writer = None
        self.log_path = '/home/sunrise/pid_log.csv'
        self.log_counter = 0
        
        # Subscriptions
        self.create_subscription(
            Float32,
            '/lane_error',
            self.lane_error_callback,
            QoSPresetProfiles.SENSOR_DATA.value
        )
        
        self.create_subscription(
            Bool,
            '/auto_mode',
            self.auto_mode_callback,
            10
        )
        
        self.create_subscription(
            Twist,
            '/cmd_vel_auto_raw',
            self.cmd_vel_callback,
            QoSPresetProfiles.SENSOR_DATA.value
        )
        
        self.get_logger().info(f'Subscribed to /lane_error, /auto_mode, and /cmd_vel_auto_raw. Logs will save to {self.log_path}')

    def lane_error_callback(self, msg: Float32):
        self.latest_lane_error = msg.data

    def auto_mode_callback(self, msg: Bool):
        previous_mode = self.auto_mode_active
        self.auto_mode_active = msg.data
        
        if self.auto_mode_active and not previous_mode:
            self.get_logger().info('Auto Mode activated. Logging started.')
        elif not self.auto_mode_active and previous_mode:
            self.get_logger().info('Auto Mode deactivated. Logging paused/stopped.')
            self.close_log()

    def cmd_vel_callback(self, msg: Twist):
        # We only log when auto mode is active
        if not self.auto_mode_active:
            return
            
        try:
            if self.log_file is None:
                # Resolve directory and ensure it exists
                log_dir = os.path.dirname(self.log_path)
                if log_dir and not os.path.exists(log_dir):
                    os.makedirs(log_dir, exist_ok=True)
                
                # Open/create file (overwrite each run to keep file clean)
                self.log_file = open(self.log_path, 'w', newline='')
                self.log_writer = csv.writer(self.log_file)
                self.log_writer.writerow(['timestamp', 'lane_error', 'linear_x', 'angular_z'])
                self.get_logger().info(f'Created new log file at {self.log_path}')
            
            # Write data row
            self.log_writer.writerow([
                time.time(),
                self.latest_lane_error,
                msg.linear.x,
                msg.angular.z
            ])
            
            self.log_counter += 1
            # Flush to disk every 50 records (~1 second of logging at 50Hz)
            if self.log_counter % 50 == 0:
                self.log_file.flush()
                
        except Exception as e:
            self.get_logger().error(f'Error writing to log file: {str(e)}')

    def close_log(self):
        if self.log_file is not None:
            try:
                self.log_file.close()
                self.log_file = None
                self.log_writer = None
                self.get_logger().info('Closed log file successfully.')
            except Exception as e:
                self.get_logger().error(f'Error closing log file: {str(e)}')

    def destroy_node(self):
        self.close_log()
        super().destroy_node()

def main(args=None):
    rclpy.init(args=args)
    node = PidLogger()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()

if __name__ == '__main__':
    main()
