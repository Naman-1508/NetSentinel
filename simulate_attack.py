import socket
import time
import random

print("DeepShark ML Engine — Threat Simulator")
print("We're going to generate some suspicious traffic locally.")
print("This will trigger high packet rates but low byte sizes, which should trigger a 'Malicious' prediction.")

target_ip = "127.0.0.1"
target_port = 8080

print(f"Blasting {target_ip}:{target_port} with UDP garbage...")

# Create a UDP socket
sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

try:
    for i in range(1, 20000):
        # Send tiny 4-byte packets extremely fast
        msg = b"HACK"
        sock.sendto(msg, (target_ip, target_port))
        
        if i % 1000 == 0:
            print(f"Sent {i} packets...")
            time.sleep(0.01) # Slight breather so we don't instantly crash our own buffer
            
except KeyboardInterrupt:
    print("Stopped.")
finally:
    sock.close()
    
print("Done. Check the DeepShark live dashboard!")
