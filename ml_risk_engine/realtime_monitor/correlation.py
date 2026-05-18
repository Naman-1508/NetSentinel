"""
Correlation Engine for NetSentinel.
Analyzes session streams to detect multi-packet attack patterns like Port Scanning, 
DDoS floods, and ARP spoofing (MAC anomalies).
"""
import time
from collections import defaultdict
from typing import Dict, Any, List

# Configurable thresholds
PORT_SCAN_WINDOW = 60.0  # seconds
PORT_SCAN_THRESHOLD = 20 # distinct ports accessed by single src_ip in window

FLOOD_WINDOW = 10.0
FLOOD_PACKET_THRESHOLD = 5000 # sustained packets per second from a single src to a dst
FLOOD_PACKET_MINIMUM = 50000
FLOOD_MIN_DURATION = 5.0

class CorrelationEngine:
    def __init__(self):
        # Track port scans: src_ip -> {dst_ip -> {port1, port2...}, "last_seen": timestamp}
        self.port_scan_tracker = defaultdict(lambda: {"targets": defaultdict(set), "last_seen": 0})
        
        # Track floods: (src_ip, dst_ip) -> {"packet_count": 0, "start_time": 0, "last_seen": 0}
        self.flood_tracker = defaultdict(lambda: {"packet_count": 0, "start_time": 0, "last_seen": 0})
        
        # Track ARP/MAC anomalies: ip -> set(macs)
        self.mac_tracker = defaultdict(set)
        
        self.emitted_alerts = {}

    def process_session(self, session: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Process a completed/updated session and return any generated alerts."""
        now = time.time()
        new_alerts = []
        
        self._cleanup_old_entries(now)
        
        src_ip = session.get("src_ip")
        dst_ip = session.get("dst_ip")
        dst_port = session.get("dst_port")
        packet_count = session.get("packet_count", 0)
        duration = session.get("duration", 0)
        src_mac = session.get("src_mac")
        dst_mac = session.get("dst_mac")

        if not src_ip or not dst_ip:
            return new_alerts

        # --- 0. Layer 2 Attack Detection (ARP/Ethernet) ---
        if session.get("protocol") == "ARP":
            # ARP spoofing attempt detected
            alert = self._create_alert(
                "ARP Spoofing Detected",
                src_ip, dst_ip, 0.95,
                f"ARP packet from {src_mac} ({src_ip}) -> {dst_ip}. Check for ARP spoofing/poisoning.",
                session
            )
            if not self._alert_recently_emitted("ARP_Protocol", f"{src_ip}-{dst_ip}"):
                new_alerts.append(alert)
                self._record_alert("ARP_Protocol", f"{src_ip}-{dst_ip}", now)
            return new_alerts  # Don't run IP-based detection on ARP packets

        # --- 1. ARP/MAC Anomaly Detection (IP spoofing with multiple MACs) ---
        if src_mac and src_ip and src_mac != "00:00:00:00:00:00":
            self.mac_tracker[src_ip].add(src_mac)
            if len(self.mac_tracker[src_ip]) > 1:
                alert = self._create_alert(
                    "ARP Spoofing / MAC Anomaly", 
                    src_ip, "Broadcast/Network", 0.98,
                    f"Multiple MAC addresses detected for IP {src_ip}: {list(self.mac_tracker[src_ip])}",
                    session
                )
                if not self._alert_recently_emitted("ARP", src_ip):
                    new_alerts.append(alert)
                    self._record_alert("ARP", src_ip, now)
                    
        if dst_mac and dst_ip and dst_mac != "00:00:00:00:00:00":
            self.mac_tracker[dst_ip].add(dst_mac)
            if len(self.mac_tracker[dst_ip]) > 1:
                alert = self._create_alert(
                    "ARP Spoofing / MAC Anomaly", 
                    dst_ip, "Broadcast/Network", 0.98,
                    f"Multiple MAC addresses detected for IP {dst_ip}: {list(self.mac_tracker[dst_ip])}",
                    session
                )
                if not self._alert_recently_emitted("ARP", dst_ip):
                    new_alerts.append(alert)
                    self._record_alert("ARP", dst_ip, now)

        # --- 2. Port Scan Detection ---
        if dst_port is not None:
            tracker = self.port_scan_tracker[src_ip]
            tracker["targets"][dst_ip].add(dst_port)
            tracker["last_seen"] = now
            
            ports_hit = len(tracker["targets"][dst_ip])
            if ports_hit > PORT_SCAN_THRESHOLD:
                alert = self._create_alert(
                    "Port Scan", 
                    src_ip, dst_ip, 0.89,
                    f"High volume of distinct ports ({ports_hit}) accessed on {dst_ip} within {PORT_SCAN_WINDOW}s.",
                    session
                )
                if not self._alert_recently_emitted("PortScan", f"{src_ip}-{dst_ip}"):
                    new_alerts.append(alert)
                    self._record_alert("PortScan", f"{src_ip}-{dst_ip}", now)
                    
        # --- 3. Flood Detection ---
        flood_key = f"{src_ip}-{dst_ip}"
        f_trk = self.flood_tracker[flood_key]
        
        if f_trk["start_time"] == 0:
            f_trk["start_time"] = now - duration if duration > 0 else now
            
        f_trk["packet_count"] += packet_count
        f_trk["last_seen"] = now
        
        time_diff = max(now - f_trk["start_time"], 1.0)
        packet_rate = f_trk["packet_count"] / time_diff
        
        if (
            packet_rate > FLOOD_PACKET_THRESHOLD
            and f_trk["packet_count"] > FLOOD_PACKET_MINIMUM
            and duration >= FLOOD_MIN_DURATION
        ):
            alert = self._create_alert(
                "DDoS / Flood", 
                src_ip, dst_ip, 0.96,
                f"High packet rate detected: {int(packet_rate)} pkts/s to {dst_ip}.",
                session
            )
            if not self._alert_recently_emitted("Flood", flood_key):
                new_alerts.append(alert)
                self._record_alert("Flood", flood_key, now)

        # --- 4. Ping of Death Detection ---
        if session.get("protocol") == "ICMP" and packet_count > 0:
            avg_size = session.get("bytes", 0) / packet_count
            if avg_size > 1000:  # Suspiciously large ICMP packets
                alert = self._create_alert(
                    "Ping of Death / Oversized ICMP", 
                    src_ip, dst_ip, 0.99,
                    f"Oversized ICMP packets detected. Avg size: {int(avg_size)} bytes.",
                    session
                )
                if not self._alert_recently_emitted("PingOfDeath", f"{src_ip}-{dst_ip}"):
                    new_alerts.append(alert)
                    self._record_alert("PingOfDeath", f"{src_ip}-{dst_ip}", now)

        # --- 5. DNS Amplification ---
        if session.get("protocol") == "UDP" and (dst_port == 53 or session.get("src_port") == 53) and packet_count > 0:
            avg_size = session.get("bytes", 0) / packet_count
            if avg_size > 500 and packet_count > 50:
                alert = self._create_alert(
                    "DNS Amplification", 
                    src_ip, dst_ip, 0.97,
                    f"Suspiciously large UDP DNS traffic. Avg size: {int(avg_size)} bytes.",
                    session
                )
                if not self._alert_recently_emitted("DNSAmp", f"{src_ip}-{dst_ip}"):
                    new_alerts.append(alert)
                    self._record_alert("DNSAmp", f"{src_ip}-{dst_ip}", now)

        # --- 6. SSH Brute Force ---
        if dst_port == 22 and packet_count > 20 and packet_count < 200:
            # Lots of packets, but short duration/small size implies failing logins
            avg_size = session.get("bytes", 0) / packet_count
            if avg_size < 300:
                alert = self._create_alert(
                    "SSH Brute Force", 
                    src_ip, dst_ip, 0.94,
                    f"Potential SSH Brute Force detected on port 22.",
                    session
                )
                if not self._alert_recently_emitted("SSHBrute", f"{src_ip}-{dst_ip}"):
                    new_alerts.append(alert)
                    self._record_alert("SSHBrute", f"{src_ip}-{dst_ip}", now)

        return new_alerts

    def _create_alert(self, type_str, src_ip, dst_ip, risk, explanation, session):
        from datetime import datetime
        return {
            "timestamp": datetime.now().isoformat(),
            "session_id": session.get("id", f"{src_ip}-{dst_ip}-alert"),
            "src_ip": src_ip,
            "dst_ip": dst_ip,
            "src_port": session.get("src_port", 0),
            "dst_port": session.get("dst_port", 0),
            "protocol": session.get("protocol", "OTHER"),
            "packet_count": session.get("packet_count", 0),
            "bytes": session.get("bytes", 0),
            "duration": session.get("duration", 0.0),
            "prediction": "Malicious", # Must be Malicious to show up in alerts
            "risk_score": risk,
            "explanation": f"[{type_str}] {explanation}",
            "is_mock": False
        }

    def _cleanup_old_entries(self, now):
        """Clean up state tracking to prevent memory leaks."""
        # Port scan
        keys_to_del = []
        for src in self.port_scan_tracker:
            if now - self.port_scan_tracker[src]["last_seen"] > PORT_SCAN_WINDOW:
                keys_to_del.append(src)
        for k in keys_to_del:
            del self.port_scan_tracker[k]
                
        # Flood
        keys_to_del = []
        for key in self.flood_tracker:
            if now - self.flood_tracker[key]["last_seen"] > FLOOD_WINDOW:
                keys_to_del.append(key)
        for k in keys_to_del:
            del self.flood_tracker[k]

    def _alert_recently_emitted(self, type_str, key):
        """Prevent spamming the exact same alert repeatedly."""
        alert_key = f"{type_str}-{key}"
        last_time = self.emitted_alerts.get(alert_key, 0)
        return (time.time() - last_time) < 30.0 # Throttle identical alerts to 1 per 30s

    def _record_alert(self, type_str, key, now):
        self.emitted_alerts[f"{type_str}-{key}"] = now
