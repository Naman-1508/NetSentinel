import socket
import threading
import time
import argparse
import sys

def udp_flood(target_ip, target_port, duration):
    """Simulate a Volumetric UDP Flood (DoS) attack"""
    print(f"[*] Starting UDP Flood against {target_ip}:{target_port}...")
    payload = b"X" * 1024  # 1KB payload
    end_time = time.time() + duration
    packets = 0
    while time.time() < end_time:
        try:
            # Rotate sockets to force NFStream to emit flows immediately
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            for _ in range(500):
                sock.sendto(payload, (target_ip, target_port))
                packets += 1
            sock.close()
            time.sleep(0.01)
        except: pass
    print(f"[+] UDP Flood complete. Sent ~{packets} packets.")

def port_scan(target_ip, duration):
    """Simulate a rapid TCP Port Scan"""
    print(f"[*] Starting TCP Port Scan against {target_ip}...")
    end_time = time.time() + duration
    port = 1
    connections = 0
    while time.time() < end_time:
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(0.05)
            s.connect((target_ip, port))
            s.close()
        except: pass
        finally:
            port = (port % 1024) + 1
            connections += 1
    print(f"[+] Port Scan complete. Attempted ~{connections} ports.")

def ssh_bruteforce(target_ip, duration):
    """Simulate an SSH Brute Force attack"""
    print(f"[*] Starting SSH Brute Force against {target_ip}:22...")
    end_time = time.time() + duration
    attempts = 0
    while time.time() < end_time:
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(0.5)
            s.connect((target_ip, 22))
            # Send multiple payloads to simulate a noisy brute force tool on a single connection
            for _ in range(15):
                s.send(b"SSH-2.0-OpenSSH_8.2p1\r\n")
                time.sleep(0.01)
            s.close()
        except: pass
        finally:
            attempts += 1
            time.sleep(0.05) # Throttle to mimic real bruteforce
    print(f"[+] SSH Brute Force complete. ~{attempts} attempts made.")

def dns_amplification(target_ip, duration):
    """Simulate a DNS Amplification attack (Large UDP to Port 53)"""
    print(f"[*] Starting DNS Flood against {target_ip}:53...")
    payload = b"A" * 600  # Large DNS payload size
    end_time = time.time() + duration
    packets = 0
    while time.time() < end_time:
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            for _ in range(50):
                sock.sendto(payload, (target_ip, 53))
                packets += 1
            sock.close()
            time.sleep(0.01)
        except: pass
    print(f"[+] DNS Flood complete. Sent ~{packets} large UDP packets.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="NetSentinel Universal Attack Simulator")
    parser.add_argument("--target", default="127.0.0.1", help="Target IP address (default: 127.0.0.1)")
    parser.add_argument("--duration", type=int, default=15, help="Duration for each attack in seconds")
    parser.add_argument("--mode", choices=['sequential', 'simultaneous'], default='sequential', 
                        help="How to launch multiple attacks (default: sequential)")
    
    args = parser.parse_args()

    print("==================================================")
    print("   NetSentinel AI Threat Generation Framework")
    print("==================================================")
    print(f"Target: {args.target} | Mode: {args.mode.upper()} | Duration: {args.duration}s per attack")
    print("==================================================\n")

    attacks = [
        (udp_flood, (args.target, 9999, args.duration)),
        (port_scan, (args.target, args.duration)),
        (ssh_bruteforce, (args.target, args.duration)),
        (dns_amplification, (args.target, args.duration))
    ]

    if args.mode == 'sequential':
        for i, (func, f_args) in enumerate(attacks, 1):
            print(f"\n--- [Attack {i}/4] ---")
            func(*f_args)
            if i < len(attacks):
                print("[*] Cooling down for 3 seconds before next attack...")
                time.sleep(3)
    else:
        print("[!] Launching all attacks SIMULTANEOUSLY!")
        threads = []
        for func, f_args in attacks:
            t = threading.Thread(target=func, args=f_args)
            t.start()
            threads.append(t)
            
        for t in threads:
            t.join()
            
    print("\n==================================================")
    print("[!] All attack simulations complete. Check the NetSentinel Dashboard!")
