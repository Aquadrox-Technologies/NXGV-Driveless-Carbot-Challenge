#!/usr/bin/env python3
"""
RISA-bot Bulk Setup & Configuration Utility
=============================================================================
Automates running setup_mdns.sh, setup_wifi.sh, and install_bashalias.sh
across multiple robots simultaneously via SSH.

Usage:
  python tools/bulk_setup_robots.py
"""

import sys
import os
import subprocess
import time

# ANSI color codes
GREEN = "\033[92m"
YELLOW = "\033[93m"
RED = "\033[91m"
BLUE = "\033[94m"
CYAN = "\033[96m"
BOLD = "\033[1m"
RESET = "\033[0m"

def print_banner():
    print(f"{CYAN}{BOLD}")
    print("======================================================")
    print("      🤖 RISA-Bot Multi-Robot Setup Utility 🤖")
    print("======================================================")
    print(f"{RESET}")

def ping_check(host):
    """Pings a host to check connectivity."""
    param = '-n' if sys.platform.lower().startswith('win') else '-c'
    timeout_param = '-w' if sys.platform.lower().startswith('win') else '-W'
    timeout_val = '1000' if sys.platform.lower().startswith('win') else '1'
    
    command = ['ping', param, '1', timeout_param, timeout_val, host]
    try:
        res = subprocess.run(command, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return res.returncode == 0
    except Exception:
        return False

def configure_robot(host_ip, index, ssid, password, sudo_password):
    hostname = f"risabot{index}"
    print(f"\n{BOLD}{BLUE}[*] Configuring robot {index} ({host_ip}) -> Hostname: {hostname}...{RESET}")
    
    # 1. Connectivity Check
    print(f"  ⏳ Testing ping connection...")
    if not ping_check(host_ip):
        print(f"  {RED}❌ Link Down: Host {host_ip} is unreachable. Skipping.{RESET}")
        return False
    print(f"  {GREEN}✅ Link Up!{RESET}")
    
    # 2. Remote Command Setup
    # Run git pull to ensure the robot has the latest tools first
    # Run install_bashalias
    # Run setup_mdns with the target hostname
    # Run setup_wifi with credentials
    commands = [
        # Step 1: Update repository
        "echo '=== [1/4] Pulling Latest Updates ===' && "
        "cd ~/risabotcar_ws && "
        "git fetch origin && "
        "git checkout refactor-test && "
        "git reset --hard origin/refactor-test",
        
        # Step 2: Install bash aliases
        "echo '=== [2/4] Configuring Bashrc & Aliases ===' && "
        "bash tools/install_bashalias.sh",
        
        # Step 3: Run mDNS Setup with target hostname
        f"echo '=== [3/4] Configuring mDNS & Hostname: {hostname} ===' && "
        f"echo '{sudo_password}' | sudo -S bash tools/setup_mdns.sh {hostname}",
        
        # Step 4: Run WiFi Setup
        f"echo '=== [4/4] Setting Up WiFi Connection ===' && "
        f"echo '{sudo_password}' | sudo -S bash tools/setup_wifi.sh '{ssid}' '{password}'"
    ]
    
    combined_cmd = " && ".join(commands)
    ssh_args = ['ssh', '-o', 'StrictHostKeyChecking=no', f'sunrise@{host_ip}', combined_cmd]
    
    try:
        proc = subprocess.Popen(
            ssh_args,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        stdout_str, stderr_str = proc.communicate()
        code = proc.returncode
        
        if code != 0:
            print(f"  {RED}❌ Configuration Failed on {host_ip} (code {code}):{RESET}")
            if stdout_str:
                print(f"--- Remote Output ---\n{stdout_str}")
            if stderr_str:
                print(f"--- Remote Errors ---\n{stderr_str}")
            return False
            
        print(f"  {GREEN}✅ Aliases successfully configured!{RESET}")
        print(f"  {GREEN}✅ Hostname set to '{hostname}' and mDNS enabled!{RESET}")
        print(f"  {GREEN}✅ WiFi profiles configured for SSID '{ssid}'!{RESET}")
        print(f"{GREEN}{BOLD}🎉 Success: {host_ip} configured as {hostname}!{RESET}")
        return True
        
    except Exception as e:
        print(f"  {RED}❌ Failed to execute SSH configuration: {e}{RESET}")
        return False

def main():
    print_banner()
    
    # Get configuration details
    ssid = input(f"{BOLD}Enter WiFi SSID (Hotspot Name): {RESET}").strip()
    if not ssid:
        print("SSID cannot be empty. Exit.")
        return
        
    password = input(f"{BOLD}Enter WiFi Password: {RESET}").strip()
    if len(password) < 8:
        print("Password must be at least 8 characters. Exit.")
        return
        
    sudo_password = input(f"{BOLD}Enter Sudo Password on Robot (default 'sunrise'): {RESET}").strip() or "sunrise"
    
    print(f"\n{BOLD}Enter robot IP addresses (separated by commas):{RESET}")
    print("Example: 192.168.1.101, 192.168.1.102, 192.168.1.103")
    ip_input = input("> ").strip()
    if not ip_input:
        print("No IPs entered. Exit.")
        return
        
    robot_ips = [ip.strip() for ip in ip_input.split(',') if ip.strip()]
    
    print(f"\n{BOLD}Enter starting index for hostnames (e.g. if '1', robots will name 'risabot1', 'risabot2'...):{RESET}")
    start_idx_str = input("Starting Index [default 1]: ").strip() or "1"
    try:
        start_idx = int(start_idx_str)
    except ValueError:
        print("Invalid index. Exit.")
        return

    print(f"\n{BOLD}{CYAN}Summary of Planned Operations:{RESET}")
    print(f"  WiFi SSID:     {ssid}")
    print(f"  WiFi Password: {'*' * len(password)}")
    print(f"  Target Robots:")
    for idx, ip in enumerate(robot_ips):
        print(f"    - {ip} -> risabot{start_idx + idx}.local")
        
    confirm = input(f"\n{BOLD}Proceed with configuring {len(robot_ips)} robots? (y/n): {RESET}").strip().lower()
    if confirm != 'y':
        print("Cancelled.")
        return

    success_count = 0
    start_time = time.time()
    
    for idx, ip in enumerate(robot_ips):
        target_idx = start_idx + idx
        if configure_robot(ip, target_idx, ssid, password, sudo_password):
            success_count += 1
            
    elapsed = time.time() - start_time
    print(f"\n{BOLD}======================================================{RESET}")
    print(f"Bulk Configuration Completed in {elapsed:.1f} seconds.")
    print(f"Status: {GREEN if success_count == len(robot_ips) else YELLOW}{success_count}/{len(robot_ips)} Successful{RESET}")
    print(f"======================================================{RESET}")

if __name__ == '__main__':
    main()
