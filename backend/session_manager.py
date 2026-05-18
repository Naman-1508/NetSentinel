import time
import threading
import math
from typing import Dict, List, Any

# Configure session timeout (seconds)
SESSION_TIMEOUT = 60.0

class SessionManager:
    """
    Manages active IP sessions. Groups packets by 5-tuple, calculates metrics,
    handles timeouts, and buffers updates for batch transmission.
    """
    def __init__(self):
        # Key: 5-tuple string (or tuple). We will use a canonical string: "srcIP:srcPort-dstIP:dstPort-Proto"
        # Since A->B and B->A are the same session, we must order the endpoints to create a unique consistent key.
        self.sessions: Dict[str, Dict[str, Any]] = {}
        
        self.lock = threading.Lock()
        
        # Batch holding IDs of sessions that were updated or closed
        self.updated_sessions = set()
        self.closed_sessions = set()

    def _make_key(self, pkt: Dict[str, Any]) -> str:
        src_ip = pkt.get("src_ip", "")
        dst_ip = pkt.get("dst_ip", "")
        src_port = pkt.get("src_port") or 0
        dst_port = pkt.get("dst_port") or 0
        protocol = pkt.get("protocol", "OTHER")

        # Lexicographical ordering to ensure A->B and B->A hash to the same key
        if f"{src_ip}:{src_port}" < f"{dst_ip}:{dst_port}":
            ep1 = f"{src_ip}:{src_port}"
            ep2 = f"{dst_ip}:{dst_port}"
        else:
            ep1 = f"{dst_ip}:{dst_port}"
            ep2 = f"{src_ip}:{src_port}"
            
        return f"{ep1}-{ep2}-{protocol}"

    def _sanitize_session(self, session: Dict[str, Any]) -> Dict[str, Any]:
        """Return a JSON-safe copy of a session record."""
        safe_session = dict(session)
        for key, value in list(safe_session.items()):
            if isinstance(value, float) and not math.isfinite(value):
                safe_session[key] = 0.0
        return safe_session

    def process_packet(self, pkt: Dict[str, Any]):
        # We only really care about IP based traffic. If no IPs, skip.
        if not pkt.get("src_ip") or not pkt.get("dst_ip"):
            return

        key = self._make_key(pkt)
        now = time.time()
        length = pkt.get("length", 0)
        flags = pkt.get("tcp_flags") or ""

        with self.lock:
            # If session exists, update it
            if key in self.sessions:
                s = self.sessions[key]

                # update basic totals
                s["packet_count"] += pkt.get("packet_count", 1)
                s["bytes"] += length
                s["last_seen"] = now
                s["duration"] = now - s["start_time"]

                # direction: compare pkt src to session src as recorded when session created
                is_fwd = (pkt.get("src_ip") == s.get("src_ip") and pkt.get("src_port") == s.get("src_port"))

                # per-direction pkt/bytes
                if is_fwd:
                    s["fwd_pkts"] += pkt.get("packet_count", 1)
                    s["fwd_bytes"] += length
                    plen = length
                    s["fwd_pkt_len_sum"] += plen
                    s["fwd_pkt_len_max"] = max(s["fwd_pkt_len_max"], plen)
                    s["fwd_pkt_len_min"] = min(s["fwd_pkt_len_min"], plen)
                    # IAT
                    if s.get("fwd_last_ts"):
                        s["fwd_iat_sum"] += now - s["fwd_last_ts"]
                        s["fwd_iat_count"] += 1
                    s["fwd_last_ts"] = now
                else:
                    s["bwd_pkts"] += pkt.get("packet_count", 1)
                    s["bwd_bytes"] += length
                    plen = length
                    s["bwd_pkt_len_sum"] += plen
                    s["bwd_pkt_len_max"] = max(s["bwd_pkt_len_max"], plen)
                    s["bwd_pkt_len_min"] = min(s["bwd_pkt_len_min"], plen)
                    # IAT
                    if s.get("bwd_last_ts"):
                        s["bwd_iat_sum"] += now - s["bwd_last_ts"]
                        s["bwd_iat_count"] += 1
                    s["bwd_last_ts"] = now

                # Flags
                if "S" in flags: s["syn_count"] += 1
                if "A" in flags: s["ack_count"] += 1
                if "F" in flags: s["fin_count"] += 1
                if "R" in flags: s["rst_count"] += 1
                if "P" in flags:
                    s["psh_count"] += 1
                    # increment per-direction PSH
                    if is_fwd:
                        s["fwd_psh_count"] += 1
                    else:
                        s["bwd_psh_count"] += 1

                self.updated_sessions.add(key)
            else:
                # Create new session
                # initialize session store with per-direction and flag aggregates
                s = {
                    "id": key,
                    "src_ip": pkt.get("src_ip", ""),
                    "dst_ip": pkt.get("dst_ip", ""),
                    "src_port": pkt.get("src_port"),
                    "dst_port": pkt.get("dst_port"),
                    "src_mac": pkt.get("src_mac", ""),
                    "dst_mac": pkt.get("dst_mac", ""),
                    "protocol": pkt.get("protocol", "OTHER"),
                    "packet_count": pkt.get("packet_count", 1),
                    "bytes": length,
                    "start_time": now,
                    "last_seen": now,
                    "duration": 0.0,
                    # directional
                    "fwd_pkts": pkt.get("packet_count", 1),
                    "bwd_pkts": 0,
                    "fwd_bytes": length,
                    "bwd_bytes": 0,
                    # per-direction packet lengths
                    "fwd_pkt_len_sum": length,
                    "bwd_pkt_len_sum": 0,
                    "fwd_pkt_len_max": length,
                    "bwd_pkt_len_max": 0,
                    "fwd_pkt_len_min": length,
                    "bwd_pkt_len_min": float("inf"),
                    # IAT sums and counters
                    "fwd_iat_sum": 0.0,
                    "fwd_iat_count": 0,
                    "bwd_iat_sum": 0.0,
                    "bwd_iat_count": 0,
                    "fwd_last_ts": now,
                    "bwd_last_ts": None,
                    # flags
                    "syn_count": 1 if "S" in flags else 0,
                    "ack_count": 1 if "A" in flags else 0,
                    "fin_count": 1 if "F" in flags else 0,
                    "rst_count": 1 if "R" in flags else 0,
                    "psh_count": 1 if "P" in flags else 0,
                    "fwd_psh_count": 1 if "P" in flags else 0,
                    "bwd_psh_count": 0,
                    "status": "Active"
                }
                self.sessions[key] = s
                self.updated_sessions.add(key)

    def check_timeouts(self):
        """Finds inactive sessions, marks them closed, and removes them from active dict."""
        now = time.time()
        to_close = []
        
        with self.lock:
            for key, s in self.sessions.items():
                if now - s["last_seen"] > SESSION_TIMEOUT:
                    to_close.append((key, s))
                    
            for key, s in to_close:
                # Calculate final duration
                s["duration"] = s["last_seen"] - s["start_time"]
                s["status"] = "Closed"
                
                self.closed_sessions.add(key)
                # Remove from updated to prevent mixed signals
                self.updated_sessions.discard(key)
                # Remove from tracking memory
                del self.sessions[key]
                
        # Return the closed session data so they can be broadcasted immediately 
        return [self._sanitize_session(s) for _, s in to_close]

    def get_batch_updates(self) -> Dict[str, List[Dict[str, Any]]]:
        """Returns the lists of updated and closed sessions since last call."""
        
        # 1. Do timeout check first
        closed_data_from_timeout = self.check_timeouts()
        
        now = time.time()
        updated_data = []
        
        with self.lock:
            for key in self.updated_sessions:
                if key in self.sessions:
                    s = self.sessions[key]
                    
                    # Update duration just before sending
                    s["duration"] = now - s["start_time"]
                    
                    # Calculate rates (approximate overall rate)
                    dur = s["duration"] if s["duration"] > 0 else 1.0 # prevent div by zero
                    s["packet_rate"] = s["packet_count"] / dur
                    s["byte_rate"] = s["bytes"] / dur
                    
                    updated_data.append(self._sanitize_session(s))
                    
            # closed_sessions might include something manually closed (like if we track FIN/RST immediately later, but for now timeout does it)
            # Add closed from timeouts and clear tracking
            self.updated_sessions.clear()
            self.closed_sessions.clear()
            
        return {
            "updated": updated_data,
            "closed": closed_data_from_timeout
        }

    def clear(self):
        with self.lock:
            self.sessions.clear()
            self.updated_sessions.clear()
            self.closed_sessions.clear()
