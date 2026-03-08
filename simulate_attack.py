import socket
import time
import sys

print("NetSentinel ML Engine — Threat Simulator")
print("We're going to generate a SYN flood style attack locally.")
print("This will trigger high packet rates but low byte sizes, which should trigger a 'Malicious' prediction.")
print("Blasting 127.0.0.1:80 with TCP SYN-like garbage...")

# We'll just rapid-fire connect/send to a port to generate lots of small TCP packets
# A true raw socket SYN flood requires admin privileges on Windows.
# As a workaround to generate the same *metrics* (high packet rate, low bytes) 
# we'll just spam tiny UDP packets from the SAME source port to the SAME dest port 
# so the session manager groups them into one massive flow.

target_ip = "127.0.0.1"
target_port = 8080

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
# Bind to a specific local port so it's always the same 5-tuple session Key
sock.bind(("127.0.0.1", 55555))

packets_sent = 0
try:
    for i in range(20000):
        # Send tiny 10 byte payload
        sock.sendto(b"X" * 10, (target_ip, target_port))
        packets_sent += 1
        
        if packets_sent % 100 == 0:
            time.sleep(0.005) # Keep the attack running for ~1 second to generate a stable, high sustained packet_rate
            
        if packets_sent % 1000 == 0:
            print(f"Sent {packets_sent} packets...")
except Exception as e:
    print(f"Error: {e}")
finally:
    sock.close()

print("Done. Check the NetSentinel live dashboard!")
