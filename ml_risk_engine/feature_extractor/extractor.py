import pandas as pd
import numpy as np
from typing import Dict, Any

# Features the ML model expects, in exact order
FEATURES = [
    "flow_duration",
    "total_packets",
    "total_bytes",
    "avg_packet_size",
    "packet_rate",
    "byte_rate",
    "syn_count",
    "ack_count",
    "fin_count",
    "rst_count",
    "proto_tcp",
    "proto_udp",
    "proto_icmp",
    "proto_other",
]

def extract_features(session: Dict[str, Any]) -> pd.DataFrame:
    """
    Converts a live NetSentinel session dictionary into a single-row DataFrame 
    with exactly the features the ML model requires.
    """
    duration = max(session.get("duration", 0.0), 0.001)
    pkts = session.get("packet_count", 1)
    bytes_count = session.get("bytes", 0)
    
    proto = session.get("protocol", "OTHER").upper()
    proto_tcp = 1 if proto == "TCP" else 0
    proto_udp = 1 if proto == "UDP" else 0
    proto_icmp = 1 if proto == "ICMP" else 0
    proto_other = 1 if proto not in ["TCP", "UDP", "ICMP"] else 0

    features = {
        "flow_duration": duration,
        "total_packets": pkts,
        "total_bytes": bytes_count,
        "avg_packet_size": bytes_count / pkts,
        "packet_rate": session.get("packet_rate", pkts / duration),
        "byte_rate": session.get("byte_rate", bytes_count / duration),
        "syn_count": session.get("syn_count", 0),
        "ack_count": session.get("ack_count", 0),
        "fin_count": session.get("fin_count", 0),
        "rst_count": session.get("rst_count", 0),
        "proto_tcp": proto_tcp,
        "proto_udp": proto_udp,
        "proto_icmp": proto_icmp,
        "proto_other": proto_other,
    }

    # Return as DataFrame to match scikit-learn training format
    return pd.DataFrame([features], columns=FEATURES)

