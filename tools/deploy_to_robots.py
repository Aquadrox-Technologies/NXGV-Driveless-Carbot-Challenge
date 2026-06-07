#!/usr/bin/env python3
"""
RISA-bot Bulk Deployer & Updater
=============================================================================
Automates pulling latest updates, copying YOLOv5 BPU model, compiling code,
and running hardware verification checks across one or multiple robots.

Usage:
  python tools/deploy_to_robots.py [host1 host2 ...]
"""

import os
import sys
import re
import subprocess
import time

# ANSI color codes for premium terminal feedback
GREEN = "\033[92m"
YELLOW = "\033[93m"
RED = "\033[91m"
BLUE = "\033[94m"
CYAN = "\033[96m"
BOLD = "\033[1m"
RESET = "\033[0m"

# Path configuration
LOCAL_MODEL_PATH = "tools/bpu_model/model_output/risabot_signs_640x640_nv12.bin"
REMOTE_MODEL_DEST = "/home/sunrise/risabot_signs_640x640_nv12.bin"

def print_banner():
    print(f"{CYAN}{BOLD}")
    print("======================================================")
    print("        🤖 RISA-Bot Bulk Deployer & Updater 🤖")
    print("======================================================")
    print(f"{RESET}")

def load_ssh_hosts():
    """Parses SSH config to find configured robots."""
    ssh_config_path = os.path.expanduser('~/.ssh/config')
    hosts = []
    if not os.path.exists(ssh_config_path):
        return hosts

    try:
        with open(ssh_config_path, 'r') as f:
            current_host = None
            current_hostname = None
            current_user = None
            
            for line in f:
                line_stripped = line.strip()
                if not line_stripped or line_stripped.startswith('#'):
                    continue
                
                # Match Host alias
                host_match = re.match(r'^Host\s+(.+)$', line_stripped, re.IGNORECASE)
                if host_match:
                    if current_host and (current_host != '*'):
                        hosts.append({
                            'alias': current_host,
                            'hostname': current_hostname or current_host,
                            'user': current_user or 'sunrise'
                        })
                    current_host = host_match.group(1).strip()
                    current_hostname = None
                    current_user = None
                
                # Match HostName (IP or real domain)
                hostname_match = re.match(r'^HostName\s+(.+)$', line_stripped, re.IGNORECASE)
                if hostname_match:
                    current_hostname = hostname_match.group(1).strip()
                
                # Match User
                user_match = re.match(r'^User\s+(.+)$', line_stripped, re.IGNORECASE)
                if user_match:
                    current_user = user_match.group(1).strip()
            
            # Add final host
            if current_host and (current_host != '*'):
                hosts.append({
                    'alias': current_host,
                    'hostname': current_hostname or current_host,
                    'user': current_user or 'sunrise'
                })
    except Exception as e:
        print(f"{RED}Error parsing SSH config: {e}{RESET}")
    
    return hosts

def ping_check(host):
    """Pings host to see if it is online (supports Windows & Unix)."""
    param = '-n' if sys.platform.lower().startswith('win') else '-c'
    timeout_param = '-w' if sys.platform.lower().startswith('win') else '-W'
    timeout_val = '1000' if sys.platform.lower().startswith('win') else '1'
    
    command = ['ping', param, '1', timeout_param, timeout_val, host]
    try:
        res = subprocess.run(command, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return res.returncode == 0
    except Exception:
        return False

def run_ssh_cmd(host_alias, user, command):
    """Runs a remote command over SSH."""
    ssh_target = f"{user}@{host_alias}" if user else host_alias
    # For aliases in ~/.ssh/config, we can just use the alias directly
    full_cmd = ['ssh', host_alias, command]
    res = subprocess.run(full_cmd, capture_output=True, text=True)
    return res.returncode, res.stdout, res.stderr

def scp_file(host_alias, user, local_path, remote_path):
    """Copies a local file to a remote destination using SCP."""
    scp_target = f"{host_alias}:{remote_path}"
    full_cmd = ['scp', local_path, scp_target]
    res = subprocess.run(full_cmd, capture_output=True, text=True)
    return res.returncode, res.stdout, res.stderr

def deploy_to_host(host_info):
    alias = host_info['alias']
    hostname = host_info['hostname']
    user = host_info['user']
    
    print(f"\n{BOLD}{BLUE}[*] Starting deployment to {alias} ({hostname})...{RESET}")
    
    # 1. Connectivity Check
    print(f"  ⏳ Testing ping connection...")
    if not ping_check(hostname):
        print(f"  {RED}❌ Link Down: Host {hostname} is unreachable. Skipping.{RESET}")
        return False
    print(f"  {GREEN}✅ Link Up!{RESET}")
    
    # Check if local model file exists
    upload_model = os.path.exists(LOCAL_MODEL_PATH)
    
    # Construct combined remote command
    remote_cmds = []
    
    if upload_model:
        print(f"  ⏳ Preparing update with BPU Model upload ({os.path.getsize(LOCAL_MODEL_PATH)/1024/1024:.2f} MB)...")
        # Step 1: Write piped input to destination path
        remote_cmds.append(f"cat > {REMOTE_MODEL_DEST}")
    else:
        print(f"  {YELLOW}⚠️ Local BPU model file not found at {LOCAL_MODEL_PATH}. Skipping model upload.{RESET}")
        print(f"  ⏳ Preparing updates...")
        
    # Step 2: Git update (fetch & force reset to align history, preserving local uncommitted hacks via stash)
    remote_cmds.append(
        "cd ~/risabotcar_ws && "
        "echo '=== [1/3] Updating Repository ===' && "
        "git stash && "
        "git fetch origin && "
        "git checkout refactor-test && "
        "git reset --hard origin/refactor-test && "
        "git stash pop || true"
    )
    
    # Step 3: Colcon build (with self-healing retry on failure)
    remote_cmds.append(
        "echo '=== [2/3] Compiling ROS 2 Workspace ===' && "
        "bash -c 'source /opt/ros/humble/setup.bash && "
        "(colcon build --symlink-install --packages-select control_servo risabot_automode || "
        "(echo \"⚠️ Build failed. Wiping build cache and retrying clean build...\" && "
        "rm -rf build/ install/ log/ && "
        "colcon build --symlink-install --packages-select control_servo risabot_automode))'"
    )
    
    # Step 4: Verification
    remote_cmds.append(
        "echo '=== [3/3] Running BPU Verification ===' && "
        "python3 ~/risabotcar_ws/tools/bpu_model/verify_bpu.py"
    )
    
    # Combine commands with '&&' so any intermediate failure stops execution
    combined_cmd = " && ".join(remote_cmds)
    
    # Spawn SSH process
    ssh_args = ['ssh', alias, combined_cmd]
    
    try:
        proc = subprocess.Popen(
            ssh_args,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        
        # If model exists, send it as stdin
        if upload_model:
            with open(LOCAL_MODEL_PATH, 'rb') as f:
                model_data = f.read()
            # This writes data to stdin and closes it, sending EOF to "cat > dest"
            stdout_data, stderr_data = proc.communicate(input=model_data)
        else:
            stdout_data, stderr_data = proc.communicate()
            
        stdout_str = stdout_data.decode(errors='replace')
        stderr_str = stderr_data.decode(errors='replace')
        code = proc.returncode
        
        if code != 0:
            print(f"  {RED}❌ Deployment Failed (code {code}):{RESET}")
            if stdout_str:
                print(f"--- Remote Output ---\n{stdout_str}")
            if stderr_str:
                print(f"--- Remote Errors ---\n{stderr_str}")
            return False
            
        # Success! Print out summary
        print(f"  {GREEN}✅ Repo updated successfully!{RESET}")
        if upload_model:
            print(f"  {GREEN}✅ BPU Model uploaded successfully to {REMOTE_MODEL_DEST}!{RESET}")
        print(f"  {GREEN}✅ Workspace compiled successfully!{RESET}")
        
        if "Verification Successful" in stdout_str:
            print(f"  {GREEN}✅ BPU Verification Successful!{RESET}")
        else:
            print(f"  {YELLOW}⚠️ BPU Verification Output:{RESET}\n{stdout_str}")
            
        print(f"{GREEN}{BOLD}🎉 Success: {alias} is fully updated and verified!{RESET}")
        return True
        
    except Exception as e:
        print(f"  {RED}❌ Failed to execute SSH deployment: {e}{RESET}")
        return False

def main():
    print_banner()
    
    # Load hosts from SSH config
    ssh_hosts = load_ssh_hosts()
    selected_hosts = []
    
    # Check if CLI args are provided
    if len(sys.argv) > 1:
        args = sys.argv[1:]
        for arg in args:
            # Check if arg is an alias in SSH config
            matched = False
            for h in ssh_hosts:
                if h['alias'] == arg or h['hostname'] == arg:
                    selected_hosts.append(h)
                    matched = True
                    break
            if not matched:
                selected_hosts.append({
                    'alias': arg,
                    'hostname': arg,
                    'user': 'sunrise'
                })
    else:
        # No args: run interactive selection menu
        if not ssh_hosts:
            print(f"{RED}No SSH hosts found in ~/.ssh/config.{RESET}")
            custom = input("Enter robot IP or SSH alias to update: ").strip()
            if not custom:
                print("Exit.")
                return
            selected_hosts.append({
                'alias': custom,
                'hostname': custom,
                'user': 'sunrise'
            })
        else:
            print(f"{BOLD}Configured hosts found in ~/.ssh/config:{RESET}")
            for idx, h in enumerate(ssh_hosts):
                print(f"  [{idx + 1}] {BOLD}{h['alias']}{RESET} ({h['hostname']}) as {h['user']}")
            
            print(f"  [{len(ssh_hosts) + 1}] Custom IP / Host")
            print(f"  [A] Update ALL Configured Robots")
            print(f"  [Q] Quit")
            
            choice = input(f"\nSelect robot(s) to update (e.g., 1, 2 or A): ").strip().lower()
            if choice == 'q' or not choice:
                print("Exit.")
                return
            elif choice == 'a':
                selected_hosts = ssh_hosts
            else:
                try:
                    parts = [p.strip() for p in choice.split(',')]
                    for p in parts:
                        val = int(p)
                        if val == len(ssh_hosts) + 1:
                            custom = input("Enter custom IP or SSH alias: ").strip()
                            if custom:
                                selected_hosts.append({
                                    'alias': custom,
                                    'hostname': custom,
                                    'user': 'sunrise'
                                })
                        elif 1 <= val <= len(ssh_hosts):
                            selected_hosts.append(ssh_hosts[val - 1])
                except ValueError:
                    print(f"{RED}Invalid selection.{RESET}")
                    return

    if not selected_hosts:
        print(f"{RED}No targets selected. Exit.{RESET}")
        return

    print(f"\n{BOLD}{CYAN}Preparing to update {len(selected_hosts)} robot(s):{RESET}")
    for h in selected_hosts:
        print(f" - {h['alias']} ({h['hostname']})")
        
    confirm = input(f"\nProceed with deployment? (y/n): ").strip().lower()
    if confirm != 'y':
        print("Cancelled.")
        return

    success_count = 0
    start_time = time.time()
    
    for h in selected_hosts:
        if deploy_to_host(h):
            success_count += 1
            
    elapsed = time.time() - start_time
    print(f"\n{BOLD}======================================================{RESET}")
    print(f"Deployment Completed in {elapsed/60:.1f} minutes.")
    print(f"Status: {GREEN if success_count == len(selected_hosts) else YELLOW}{success_count}/{len(selected_hosts)} Successful{RESET}")
    print(f"{BOLD}======================================================{RESET}")

if __name__ == '__main__':
    main()
