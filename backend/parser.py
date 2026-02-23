"""
Packet parser module.
Extracts structured fields from raw Scapy packets.
"""
import time
from typing import Optional, Dict, Any
import logging

logger = logging.getLogger(__name__)

# TCP flag bit masks
TCP_FLAG_MAP = {
    0x01: "FIN",
    0x02: "SYN",
    0x04: "RST",
    0x08: "PSH",
    0x10: "ACK",
    0x20: "URG",
}


def parse_tcp_flags(flags_int: int) -> str:
    """Convert TCP flags integer to human-readable string."""
    active = [name for bit, name in TCP_FLAG_MAP.items() if flags_int & bit]
    return ", ".join(active) if active else "None"


def build_info_string(protocol: str, src_port: Optional[int], dst_port: Optional[int],
                      tcp_flags: Optional[str], length: int) -> str:
    """Build Wireshark-style info string."""
    if protocol == "TCP" and src_port is not None and dst_port is not None:
        flags_str = f" [{tcp_flags}]" if tcp_flags and tcp_flags != "None" else ""
        return f"{src_port} → {dst_port}{flags_str} Len={length}"
    elif protocol == "UDP" and src_port is not None and dst_port is not None:
        return f"{src_port} → {dst_port} Len={length}"
    elif protocol == "ICMP":
        return f"ICMP Echo/Reply Len={length}"
    else:
        return f"Len={length}"


def parse_packet(packet) -> Optional[Dict[str, Any]]:
    """
    Parse a Scapy packet into a structured dictionary.
    Returns None if the packet is not IP-based.
    """
    try:
        from scapy.layers.inet import IP, TCP, UDP, ICMP
        from scapy.layers.l2 import Ether

        # Only process IP packets
        if not packet.haslayer(IP):
            return None

        ip_layer = packet[IP]

        src_ip: str = ip_layer.src
        dst_ip: str = ip_layer.dst
        length: int = len(packet)
        timestamp: str = f"{packet.time:.6f}"

        src_port: Optional[int] = None
        dst_port: Optional[int] = None
        protocol: str = "OTHER"
        tcp_flags: Optional[str] = None

        if packet.haslayer(TCP):
            protocol = "TCP"
            tcp_layer = packet[TCP]
            src_port = int(tcp_layer.sport)
            dst_port = int(tcp_layer.dport)
            flags_int = int(tcp_layer.flags)
            tcp_flags = parse_tcp_flags(flags_int)

        elif packet.haslayer(UDP):
            protocol = "UDP"
            udp_layer = packet[UDP]
            src_port = int(udp_layer.sport)
            dst_port = int(udp_layer.dport)

        elif packet.haslayer(ICMP):
            protocol = "ICMP"

        elif ip_layer.proto == 6:
            protocol = "TCP"
        elif ip_layer.proto == 17:
            protocol = "UDP"
        elif ip_layer.proto == 1:
            protocol = "ICMP"

        info = build_info_string(protocol, src_port, dst_port, tcp_flags, length)

        return {
            "timestamp": timestamp,
            "src_ip": src_ip,
            "dst_ip": dst_ip,
            "src_port": src_port,
            "dst_port": dst_port,
            "protocol": protocol,
            "tcp_flags": tcp_flags,
            "length": length,
            "info": info,
        }

    except Exception as e:
        logger.debug(f"Packet parse error: {e}")
        return None
