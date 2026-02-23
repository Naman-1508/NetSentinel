import time
import threading
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
                
                # Check if it was previously closed (e.g. timeout) but now alive again
                # In this logic we actually fully delete closed sessions from self.sessions after emitting 'closed' event.
                # So if it's in self.sessions, it's active.
                
                s["packet_count"] += 1
                s["bytes"] += length
                s["last_seen"] = now
                s["duration"] = now - s["start_time"]
                
                if "S" in flags: s["syn_count"] += 1
                if "A" in flags: s["ack_count"] += 1
                if "F" in flags: s["fin_count"] += 1
                if "R" in flags: s["rst_count"] += 1
                
                # We could calculate rates dynamically when generating batch updates
                self.updated_sessions.add(key)
            else:
                # Create new session
                s = {
                    "id": key,
                    "src_ip": pkt.get("src_ip", ""),
                    "dst_ip": pkt.get("dst_ip", ""),
                    "src_port": pkt.get("src_port"),
                    "dst_port": pkt.get("dst_port"),
                    "protocol": pkt.get("protocol", "OTHER"),
                    "packet_count": 1,
                    "bytes": length,
                    "start_time": now,
                    "last_seen": now,
                    "duration": 0.0,
                    "syn_count": 1 if "S" in flags else 0,
                    "ack_count": 1 if "A" in flags else 0,
                    "fin_count": 1 if "F" in flags else 0,
                    "rst_count": 1 if "R" in flags else 0,
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
        return [s for _, s in to_close]

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
                    
                    updated_data.append(dict(s)) # copy
                    
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
