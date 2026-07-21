#!/usr/bin/env python3
"""
RISA-bot Paramiko Deployer & Updater
=============================================================================
Automates model upload, repository pull, compilation, and verification
across multiple robots using Paramiko (avoiding SSH key passwordless requirements).

Usage:
  python tools/deploy_to_robots_paramiko.py [host1 host2 ...] [options]
Options:
  --mode {1,2}  1 = Full Deployment (Model, Git, Build, Verify)
                2 = Model Upload & Verification Only
  -y, --yes     Auto-confirm prompt
"""

import os
import sys
import argparse
import time

# Ensure paramiko is available
try:
    import paramiko
except ImportError:
    print("paramiko not found. Installing...")
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "paramiko"])
    import paramiko

# ANSI color codes
GREEN = "\033[92m"
YELLOW = "\033[93m"
RED = "\033[91m"
BLUE = "\033[94m"
CYAN = "\033[96m"
BOLD = "\033[1m"
RESET = "\033[0m"

LOCAL_MODEL_PATH = "tools/bpu_model/model_output/risabot_signs_640x640_nv12.bin"
REMOTE_MODEL_DEST = "/home/sunrise/risabot_signs_640x640_nv12.bin"

DEFAULT_ROBOTS = [
    "risabot1.local", "risabot2.local", "risabot3.local", "risabot4.local",
    "risabot5.local", "risabot6.local", "risabot7.local", "risabot9.local",
    "risabot10.local"
]

def print_banner():
    print(f"{CYAN}{BOLD}")
    print("======================================================")
    print("     RISA-Bot Paramiko Model Deployer & Updater")
    print("======================================================")
    print(f"{RESET}")

def ping_check(host):
    import subprocess as sp
    param = '-n' if sys.platform.lower().startswith('win') else '-c'
    timeout_param = '-w' if sys.platform.lower().startswith('win') else '-W'
    timeout_val = '1000' if sys.platform.lower().startswith('win') else '1'
    try:
        res = sp.run(
            ['ping', param, '1', timeout_param, timeout_val, host],
            stdout=sp.DEVNULL, stderr=sp.DEVNULL
        )
        return res.returncode == 0
    except Exception:
        return False

def ssh_run(client, command, timeout=180):
    stdin, stdout, stderr = client.exec_command(command, timeout=timeout, get_pty=True)
    stdin.close()
    out = stdout.read().decode('utf-8', errors='replace')
    code = stdout.channel.recv_exit_status()
    return code, out

def deploy_to_host(host, mode):
    print(f"\n{BOLD}{BLUE}[*] Starting deployment to {host}...{RESET}")
    
    # 1. Connectivity Check
    print(f"  ... Testing ping connection...")
    if not ping_check(host):
        print(f"  {RED}[ERROR] Link Down: Host {host} is unreachable. Skipping.{RESET}")
        return False
    print(f"  {GREEN}[OK] Link Up!{RESET}")
    
    # 2. SSH Connection
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    
    try:
        print(f"  ... Connecting via SSH...")
        client.connect(
            hostname=host,
            username='sunrise',
            password='sunrise',
            timeout=15,
            look_for_keys=False,
            allow_agent=False
        )
        print(f"  {GREEN}[OK] SSH Connected!{RESET}")
    except Exception as e:
        print(f"  {RED}[ERROR] SSH Connection Failed: {e}{RESET}")
        return False
        
    try:
        # Check if local model file exists
        upload_model = os.path.exists(LOCAL_MODEL_PATH)
        
        # 3. Model Upload (SFTP)
        if upload_model:
            print(f"  ... Uploading BPU model ({os.path.getsize(LOCAL_MODEL_PATH)/1024/1024:.2f} MB) via SFTP...")
            sftp = client.open_sftp()
            sftp.put(LOCAL_MODEL_PATH, REMOTE_MODEL_DEST)
            sftp.close()
            print(f"  {GREEN}[OK] Model uploaded successfully to {REMOTE_MODEL_DEST}!{RESET}")
        else:
            print(f"  {YELLOW}[WARN] Local BPU model file not found at {LOCAL_MODEL_PATH}. Skipping upload.{RESET}")
            
        if mode == 1:
            # 4. Git pull & reset
            print(f"  ... [1/3] Updating Repository...")
            git_cmd = (
                "cd ~/risabotcar_ws && "
                "git stash && "
                "git fetch origin && "
                "git checkout refactor-test && "
                "git reset --hard origin/refactor-test && "
                "git stash pop || true"
            )
            code, out = ssh_run(client, git_cmd)
            if code != 0:
                print(f"  {RED}[ERROR] Git Update Failed (code {code}):{RESET}\n{out}")
                return False
            print(f"  {GREEN}[OK] Repository updated!{RESET}")
            
            # 5. Colcon Build
            print(f"  ... [2/3] Compiling ROS 2 Workspace...")
            build_cmd = (
                "cd ~/risabotcar_ws && "
                "bash -c 'source /opt/ros/humble/setup.bash && "
                "(colcon build --symlink-install --packages-select control_servo risabot_automode || "
                "(rm -rf build/ install/ log/ && "
                "colcon build --symlink-install --packages-select control_servo risabot_automode)) && "
                "source install/setup.bash'"
            )
            code, out = ssh_run(client, build_cmd, timeout=240)
            if code != 0:
                print(f"  {RED}[ERROR] Build Failed (code {code}):{RESET}\n{out}")
                return False
            print(f"  {GREEN}[OK] Workspace compiled and sourced!{RESET}")
            
            # 6. BPU Verification
            print(f"  ... [3/3] Running BPU Verification...")
            verify_cmd = "python3 ~/risabotcar_ws/tools/bpu_model/verify_bpu.py"
            code, out = ssh_run(client, verify_cmd)
            if "Verification Successful" in out:
                print(f"  {GREEN}[OK] BPU Verification Successful!{RESET}")
            else:
                print(f"  {YELLOW}[WARN] BPU Verification Output (code {code}):{RESET}\n{out}")
                if code != 0:
                    return False
        else:
            # Mode 2: Verify only
            print(f"  ... [1/1] Running BPU Verification...")
            verify_cmd = "python3 ~/risabotcar_ws/tools/bpu_model/verify_bpu.py"
            code, out = ssh_run(client, verify_cmd)
            if "Verification Successful" in out:
                print(f"  {GREEN}[OK] BPU Verification Successful!{RESET}")
            else:
                print(f"  {YELLOW}[WARN] BPU Verification Output (code {code}):{RESET}\n{out}")
                if code != 0:
                    return False
                    
        print(f"{GREEN}{BOLD}[SUCCESS] {host} is fully updated and verified!{RESET}")
        return True
    except Exception as e:
        print(f"  {RED}[ERROR] Error during deployment to {host}: {e}{RESET}")
        return False
    finally:
        client.close()

def main():
    print_banner()
    
    # Setup Argument Parser
    parser = argparse.ArgumentParser(description="Bulk Deployer & Updater via Paramiko")
    parser.add_argument('hosts', metavar='H', type=str, nargs='*', help='Robot hostnames/IPs to deploy to')
    parser.add_argument('--mode', type=int, choices=[1, 2], help='1 = Full Deploy, 2 = Model Upload & Verify Only')
    parser.add_argument('-y', '--yes', action='store_true', help='Skip confirmation prompt')
    args = parser.parse_args()
    
    # Determine hosts
    hosts = args.hosts if args.hosts else DEFAULT_ROBOTS
    
    # Determine mode
    mode = args.mode
    if not mode:
        print("Select deployment mode:")
        print("  [1] Complete Deployment (Model Upload + Git Update + Workspace Rebuild + BPU Verify)")
        print("  [2] Model Upload & BPU Verification Only (Quick Copy & Test)")
        try:
            choice = input("Enter choice [2]: ").strip()
            if choice == '1':
                mode = 1
            else:
                mode = 2
        except (KeyboardInterrupt, EOFError):
            print("\nCancelled.")
            return
            
    # Confirm
    print(f"\n{BOLD}{CYAN}Summary of Operations:{RESET}")
    print(f"  Mode:   {'Full Deployment' if mode == 1 else 'Model Upload & Verification Only'}")
    print(f"  Target Robots ({len(hosts)} total):")
    for h in hosts:
        print(f"    - {h}")
        
    if not args.yes:
        try:
            confirm = input(f"\nProceed with deployment? (y/n) [n]: ").strip().lower()
            if confirm != 'y':
                print("Cancelled.")
                return
        except (KeyboardInterrupt, EOFError):
            print("\nCancelled.")
            return

    success_count = 0
    start_time = time.time()
    
    for h in hosts:
        if deploy_to_host(h, mode):
            success_count += 1
            
    elapsed = time.time() - start_time
    print(f"\n{BOLD}======================================================{RESET}")
    print(f"Deployment Completed in {elapsed/60:.1f} minutes.")
    color = GREEN if success_count == len(hosts) else YELLOW
    print(f"Status: {color}{success_count}/{len(hosts)} Successful{RESET}")
    print(f"{BOLD}======================================================{RESET}")

if __name__ == '__main__':
    main()
