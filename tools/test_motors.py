#!/usr/bin/env python3
import time
import sys
import os

# Add the rosmaster_lib path if it's in tools
sys.path.append(os.path.join(os.path.dirname(__file__), 'rosmaster_lib'))
from Rosmaster_Lib import Rosmaster

def main():
    print("Testing Rosmaster Connection and Movement...")
    try:
        bot = Rosmaster(com="/dev/myserial")
        print("✅ Serial port opened successfully.")
        
        print("Testing beep...")
        bot.set_beep(50)
        time.sleep(0.5)
        
        print("Testing servo steering (ID 4)...")
        print("Setting servo to 60 deg...")
        bot.set_pwm_servo(4, 60)
        time.sleep(1.0)
        print("Setting servo to 120 deg...")
        bot.set_pwm_servo(4, 120)
        time.sleep(1.0)
        print("Setting servo back to center (90 deg)...")
        bot.set_pwm_servo(4, 90)
        time.sleep(1.0)
        
        print("Testing motor (Channel 1, speed 30)...")
        # RISA-Bot uses channel 1 or motor_idx 0 (depends on Yahboom setup)
        # We will try set_motor(30, 0, 0, 0)
        bot.set_motor(30, 0, 0, 0)
        time.sleep(1.0)
        print("Stopping motor...")
        bot.set_motor(0, 0, 0, 0)
        
        print("Read IMU data test...")
        bot.create_receive_threading()
        time.sleep(0.5)
        roll, pitch, yaw = bot.get_imu_attitude_data()
        print(f"IMU: roll={roll:.2f}, pitch={pitch:.2f}, yaw={yaw:.2f}")
        
        print("✅ Test complete!")
    except Exception as e:
        print(f"❌ Error during test: {e}")

if __name__ == '__main__':
    main()
