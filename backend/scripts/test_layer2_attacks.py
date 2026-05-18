#!/usr/bin/env python3
"""
Layer 2 Attack Testing Script for NetSentinel
============================================

Tests the following Layer 2/3/4 attack scenarios on Windows loopback interface:
  1. ARP Spoofing (Layer 2)
  2. MAC Spoofing (Layer 2)
  3. TCP SYN Flood (Layer 4)
  4. UDP Flood (Layer 4)
  5. Port Scan (Layer 3/4)
  6. DNS Amplification (Layer 4)

Requirements:
  - Scapy >= 2.5.0
  - Npcap installed with WinPcap API compatible mode
  - Run as Administrator
  - Works on Windows loopback interface or physical interfaces

Usage:
  python test_layer2_attacks.py --help
  python test_layer2_attacks.py --interface "Loopback" --test-type arp-spoof --count 10
  python test_layer2_attacks.py --interface "Loopback" --test-type all
"""

import argparse
import sys
import os
import time
import logging
from typing import List, Optional

# Scapy imports
try:
    from scapy.all import (
        send, sendp, IP, TCP, UDP, ICMP, ARP, Ether, 
        get_if_hwaddr, conf, RandMAC, RandIP
    )
except ImportError:
    print("ERROR: Scapy not installed. Install with: pip install scapy>=2.5.0")
    sys.exit(1)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s'
)
logger = logging.getLogger(__name__)


class Layer2AttackTester:
    """Generates Layer 2/3/4 attack traffic for testing."""
    
    def __init__(self, interface: str, verbose: bool = False):
        self.interface = interface
        self.verbose = verbose
        conf.iface = interface
        
        # Try to get MAC address for this interface
        try:
            self.src_mac = get_if_hwaddr(interface)
        except:
            self.src_mac = "00:11:22:33:44:55"
        
        logger.info(f"Using interface: {interface}")
        logger.info(f"Source MAC: {self.src_mac}")
    
    def arp_spoof_attack(self, count: int = 10, delay: float = 0.1) -> None:
        """
        ARP Spoofing Attack (Layer 2)
        Sends ARP requests claiming to be different IPs.
        """
        logger.info(f"Starting ARP Spoofing Attack ({count} packets, {delay}s delay)")
        
        target_ips = [
            ("192.168.1.1", "192.168.1.50"),
            ("192.168.1.100", "192.168.1.200"),
            ("10.0.0.1", "10.0.0.254"),
        ]
        
        for i in range(count):
            src_ip, dst_ip = target_ips[i % len(target_ips)]
            
            # ARP request: who-has dst_ip tell src_ip
            packet = ARP(
                op="is-at",  # ARP reply (spoofing)
                pdst=dst_ip,
                psrc=src_ip,
                hwsrc=RandMAC(),  # Random MAC to simulate spoofing
                hwdst="ff:ff:ff:ff:ff:ff"  # Broadcast
            )
            
            if self.verbose:
                logger.debug(f"Sending ARP spoof: {src_ip} -> {dst_ip}")
            
            try:
                sendp(packet, iface=self.interface, verbose=0)
            except Exception as e:
                logger.warning(f"Failed to send ARP packet: {e}")
            
            time.sleep(delay)
        
        logger.info(f"✓ ARP Spoofing Attack completed ({count} packets sent)")
    
    def mac_spoof_attack(self, count: int = 10, delay: float = 0.1) -> None:
        """
        MAC Spoofing / ARP Anomaly Detection (Layer 2)
        Sends packets from the same IP but different MACs.
        """
        logger.info(f"Starting MAC Spoofing Attack ({count} packets, {delay}s delay)")
        
        spoofed_ip = "10.0.0.99"
        
        for i in range(count):
            spoofed_mac = f"00:11:22:{i:02x}:{i:02x}:{i:02x}"
            
            # Build packet with spoofed MAC
            eth = Ether(src=spoofed_mac, dst="ff:ff:ff:ff:ff:ff")
            arp = ARP(
                op="is-at",
                psrc=spoofed_ip,
                pdst="10.0.0.1",
                hwsrc=spoofed_mac,
                hwdst="ff:ff:ff:ff:ff:ff"
            )
            packet = eth/arp
            
            if self.verbose:
                logger.debug(f"Sending MAC spoof: {spoofed_ip} from {spoofed_mac}")
            
            try:
                sendp(packet, iface=self.interface, verbose=0)
            except Exception as e:
                logger.warning(f"Failed to send spoofed packet: {e}")
            
            time.sleep(delay)
        
        logger.info(f"✓ MAC Spoofing Attack completed ({count} packets sent)")
    
    def syn_flood_attack(self, target_ip: str = "192.168.1.100", 
                        target_port: int = 80, count: int = 100, 
                        delay: float = 0.01) -> None:
        """
        TCP SYN Flood Attack (Layer 4 DoS)
        Sends SYN packets rapidly to simulate DDoS.
        """
        logger.info(f"Starting SYN Flood Attack to {target_ip}:{target_port} ({count} packets)")
        
        for i in range(count):
            src_port = 40000 + (i % 20000)
            
            packet = IP(dst=target_ip) / TCP(
                sport=src_port,
                dport=target_port,
                flags="S",  # SYN flag
                seq=1000 + i
            )
            
            if self.verbose:
                logger.debug(f"Sending SYN: {src_port} -> {target_ip}:{target_port}")
            
            try:
                send(packet, iface=self.interface, verbose=0)
            except Exception as e:
                logger.warning(f"Failed to send SYN packet: {e}")
            
            time.sleep(delay)
        
        logger.info(f"✓ SYN Flood Attack completed ({count} packets sent)")
    
    def udp_flood_attack(self, target_ip: str = "203.0.113.50", 
                        target_port: int = 53, count: int = 500, 
                        delay: float = 0.001) -> None:
        """
        UDP Flood Attack (Layer 4 DoS)
        Sends UDP packets rapidly to simulate DDoS.
        """
        logger.info(f"Starting UDP Flood Attack to {target_ip}:{target_port} ({count} packets)")
        
        for i in range(count):
            src_port = 1234 + (i % 10000)
            payload = b"X" * 64  # Payload size
            
            packet = IP(dst=target_ip) / UDP(
                sport=src_port,
                dport=target_port
            ) / payload
            
            if self.verbose and i % 50 == 0:
                logger.debug(f"Sending UDP: {src_port} -> {target_ip}:{target_port}")
            
            try:
                send(packet, iface=self.interface, verbose=0)
            except Exception as e:
                logger.warning(f"Failed to send UDP packet: {e}")
            
            time.sleep(delay)
        
        logger.info(f"✓ UDP Flood Attack completed ({count} packets sent)")
    
    def port_scan_attack(self, target_ip: str = "10.0.0.5", 
                        start_port: int = 1, end_port: int = 100, 
                        delay: float = 0.05) -> None:
        """
        Port Scan Attack (Layer 3/4)
        Scans many ports on target to simulate reconnaissance.
        """
        ports_to_scan = list(range(start_port, end_port + 1))
        logger.info(f"Starting Port Scan Attack on {target_ip} (ports {start_port}-{end_port})")
        
        for port in ports_to_scan:
            packet = IP(dst=target_ip) / TCP(
                sport=40001,
                dport=port,
                flags="S"  # SYN flag
            )
            
            if self.verbose and port % 10 == 0:
                logger.debug(f"Scanning port: {port}")
            
            try:
                send(packet, iface=self.interface, verbose=0)
            except Exception as e:
                logger.warning(f"Failed to send scan packet: {e}")
            
            time.sleep(delay)
        
        logger.info(f"✓ Port Scan Attack completed ({end_port - start_port + 1} ports scanned)")
    
    def dns_amplification_attack(self, target_ip: str = "203.0.113.5", 
                                count: int = 50, delay: float = 0.05) -> None:
        """
        DNS Amplification Attack (Layer 4 DDoS)
        Sends large DNS responses to simulate amplification attack.
        """
        logger.info(f"Starting DNS Amplification Attack on {target_ip} ({count} packets)")
        
        for i in range(count):
            # Large DNS response-like UDP packet
            large_payload = b"DNS_RESPONSE_" * 50  # ~650 bytes
            
            packet = IP(dst=target_ip, src=RandIP()) / UDP(
                sport=53,  # DNS port as source (spoofed)
                dport=33434 + (i % 100)
            ) / large_payload
            
            if self.verbose and i % 10 == 0:
                logger.debug(f"Sending DNS amplification packet {i}")
            
            try:
                send(packet, iface=self.interface, verbose=0)
            except Exception as e:
                logger.warning(f"Failed to send DNS amplification packet: {e}")
            
            time.sleep(delay)
        
        logger.info(f"✓ DNS Amplification Attack completed ({count} packets sent)")
    
    def benign_traffic(self, count: int = 20, delay: float = 0.1) -> None:
        """
        Generate benign traffic for baseline comparison.
        """
        logger.info(f"Generating benign traffic ({count} packets)")
        
        for i in range(count):
            # Normal HTTP-like traffic
            packet = IP(dst="93.184.216.34", src="10.0.0.100") / TCP(
                sport=52345 + i,
                dport=80,
                flags="S"
            )
            
            try:
                send(packet, iface=self.interface, verbose=0)
            except Exception as e:
                logger.warning(f"Failed to send benign packet: {e}")
            
            time.sleep(delay)
        
        logger.info(f"✓ Benign traffic completed ({count} packets sent)")


def main():
    parser = argparse.ArgumentParser(
        description="Layer 2/3/4 Attack Testing for NetSentinel IDS",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Test ARP spoofing on loopback
  python test_layer2_attacks.py --interface "Loopback" --test-type arp-spoof --count 20
  
  # Run all tests with custom delays
  python test_layer2_attacks.py --interface "Ethernet" --test-type all --delay 0.05
  
  # Test SYN flood with verbose output
  python test_layer2_attacks.py --interface "Loopback" --test-type syn-flood --verbose
        """
    )
    
    parser.add_argument(
        "--interface", "-i",
        default="Loopback",
        help="Interface name to send packets on (default: Loopback)"
    )
    
    parser.add_argument(
        "--test-type", "-t",
        choices=["arp-spoof", "mac-spoof", "syn-flood", "udp-flood", "port-scan", "dns-amp", "benign", "all"],
        default="all",
        help="Type of attack to simulate (default: all)"
    )
    
    parser.add_argument(
        "--count", "-c",
        type=int,
        default=50,
        help="Number of packets to send per test (default: 50)"
    )
    
    parser.add_argument(
        "--delay", "-d",
        type=float,
        default=0.05,
        help="Delay between packets in seconds (default: 0.05)"
    )
    
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable verbose debug output"
    )
    
    args = parser.parse_args()
    
    # Validate interface exists
    try:
        from scapy.all import get_if_list
        available = get_if_list()
        logger.info(f"Available interfaces: {available}")
        
        if args.interface not in available:
            logger.warning(f"Interface '{args.interface}' not found!")
            logger.info(f"Available: {', '.join(available)}")
    except:
        pass
    
    # Create tester
    tester = Layer2AttackTester(args.interface, verbose=args.verbose)
    
    logger.info("=" * 70)
    logger.info("NetSentinel Layer 2/3/4 Attack Testing Script")
    logger.info("=" * 70)
    logger.info(f"Interface: {args.interface}")
    logger.info(f"Packet count: {args.count}")
    logger.info(f"Delay: {args.delay}s")
    logger.info("=" * 70)
    
    # Run tests
    try:
        if args.test_type in ["arp-spoof", "all"]:
            logger.info("\n[1/7] ARP Spoofing Attack...")
            tester.arp_spoof_attack(count=args.count, delay=args.delay)
            time.sleep(1)
        
        if args.test_type in ["mac-spoof", "all"]:
            logger.info("\n[2/7] MAC Spoofing Attack...")
            tester.mac_spoof_attack(count=args.count, delay=args.delay)
            time.sleep(1)
        
        if args.test_type in ["syn-flood", "all"]:
            logger.info("\n[3/7] SYN Flood Attack...")
            tester.syn_flood_attack(count=args.count, delay=args.delay)
            time.sleep(1)
        
        if args.test_type in ["udp-flood", "all"]:
            logger.info("\n[4/7] UDP Flood Attack...")
            tester.udp_flood_attack(count=args.count, delay=args.delay)
            time.sleep(1)
        
        if args.test_type in ["port-scan", "all"]:
            logger.info("\n[5/7] Port Scan Attack...")
            tester.port_scan_attack(start_port=1, end_port=args.count)
            time.sleep(1)
        
        if args.test_type in ["dns-amp", "all"]:
            logger.info("\n[6/7] DNS Amplification Attack...")
            tester.dns_amplification_attack(count=args.count, delay=args.delay)
            time.sleep(1)
        
        if args.test_type in ["benign", "all"]:
            logger.info("\n[7/7] Benign Traffic...")
            tester.benign_traffic(count=args.count, delay=args.delay)
        
        logger.info("\n" + "=" * 70)
        logger.info("✓ All tests completed successfully!")
        logger.info("=" * 70)
        logger.info("\nCheck the NetSentinel dashboard to see:")
        logger.info("  - Layer 2 attacks: ARP Spoofing, MAC Anomalies")
        logger.info("  - Layer 4 attacks: SYN Floods, UDP Floods, Port Scans")
        logger.info("  - ML predictions with risk scores")
        logger.info("  - Captured MAC addresses and protocols")
        
    except KeyboardInterrupt:
        logger.info("\n✗ Tests interrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"✗ Test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
