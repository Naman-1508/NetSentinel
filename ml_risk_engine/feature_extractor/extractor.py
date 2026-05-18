import pandas as pd
import numpy as np
from typing import Dict, Any

# Features the trained model expects (from feature_list.pkl)
FEATURES = [
    'Flow Duration',
    'Tot Fwd Pkts',
    'Tot Bwd Pkts',
    'TotLen Fwd Pkts',
    'TotLen Bwd Pkts',
    'Fwd Pkt Len Max',
    'Fwd Pkt Len Min',
    'Fwd Pkt Len Mean',
    'Bwd Pkt Len Max',
    'Bwd Pkt Len Min',
    'Bwd Pkt Len Mean',
    'Flow Byts/s',
    'Flow Pkts/s',
    'Flow IAT Mean',
    'Fwd IAT Mean',
    'Bwd IAT Mean',
    'Fwd PSH Flags',
    'FIN Flag Cnt',
    'SYN Flag Cnt',
    'RST Flag Cnt',
    'PSH Flag Cnt',
    'ACK Flag Cnt',
    'Down/Up Ratio',
    'Fwd Seg Size Avg',
    'Bwd Seg Size Avg',
]

def extract_features(session: Dict[str, Any]) -> pd.DataFrame:
    """
    Converts a live NetSentinel session dictionary into a single-row DataFrame 
    with exactly the features the ML model requires.
    """
    duration = max(session.get("duration", 0.0), 0.001)
    total_pkts = session.get("packet_count", 1)
    total_bytes = session.get("bytes", 0)

    fwd_pkts = session.get("fwd_pkts", 0)
    bwd_pkts = session.get("bwd_pkts", 0)
    fwd_bytes = session.get("fwd_bytes", 0)
    bwd_bytes = session.get("bwd_bytes", 0)

    fwd_pkt_len_max = session.get("fwd_pkt_len_max", 0)
    fwd_pkt_len_min = session.get("fwd_pkt_len_min", 0)
    fwd_pkt_len_mean = (session.get("fwd_pkt_len_sum", 0) / fwd_pkts) if fwd_pkts > 0 else 0

    bwd_pkt_len_max = session.get("bwd_pkt_len_max", 0)
    bwd_pkt_len_min = session.get("bwd_pkt_len_min", 0)
    bwd_pkt_len_mean = (session.get("bwd_pkt_len_sum", 0) / bwd_pkts) if bwd_pkts > 0 else 0

    flow_byts_s = total_bytes / duration
    flow_pkts_s = total_pkts / duration

    total_iat_sum = session.get("fwd_iat_sum", 0.0) + session.get("bwd_iat_sum", 0.0)
    total_iat_count = session.get("fwd_iat_count", 0) + session.get("bwd_iat_count", 0)
    flow_iat_mean = (total_iat_sum / total_iat_count) if total_iat_count > 0 else 0
    fwd_iat_mean = (session.get("fwd_iat_sum", 0.0) / session.get("fwd_iat_count", 1)) if session.get("fwd_iat_count", 0) > 0 else 0
    bwd_iat_mean = (session.get("bwd_iat_sum", 0.0) / session.get("bwd_iat_count", 1)) if session.get("bwd_iat_count", 0) > 0 else 0

    fwd_psh = session.get("fwd_psh_count", 0)
    psh_count = session.get("psh_count", 0)

    syn_count = session.get("syn_count", 0)
    fin_count = session.get("fin_count", 0)
    rst_count = session.get("rst_count", 0)
    ack_count = session.get("ack_count", 0)

    down_up_ratio = (bwd_bytes / (fwd_bytes if fwd_bytes > 0 else 1))
    fwd_seg_size_avg = (fwd_bytes / fwd_pkts) if fwd_pkts > 0 else 0
    bwd_seg_size_avg = (bwd_bytes / bwd_pkts) if bwd_pkts > 0 else 0

    features = {
        'Flow Duration': duration,
        'Tot Fwd Pkts': fwd_pkts,
        'Tot Bwd Pkts': bwd_pkts,
        'TotLen Fwd Pkts': fwd_bytes,
        'TotLen Bwd Pkts': bwd_bytes,
        'Fwd Pkt Len Max': fwd_pkt_len_max,
        'Fwd Pkt Len Min': (0 if fwd_pkt_len_min == float('inf') else fwd_pkt_len_min),
        'Fwd Pkt Len Mean': fwd_pkt_len_mean,
        'Bwd Pkt Len Max': bwd_pkt_len_max,
        'Bwd Pkt Len Min': (0 if bwd_pkt_len_min == float('inf') else bwd_pkt_len_min),
        'Bwd Pkt Len Mean': bwd_pkt_len_mean,
        'Flow Byts/s': flow_byts_s,
        'Flow Pkts/s': flow_pkts_s,
        'Flow IAT Mean': flow_iat_mean,
        'Fwd IAT Mean': fwd_iat_mean,
        'Bwd IAT Mean': bwd_iat_mean,
        'Fwd PSH Flags': fwd_psh,
        'FIN Flag Cnt': fin_count,
        'SYN Flag Cnt': syn_count,
        'RST Flag Cnt': rst_count,
        'PSH Flag Cnt': psh_count,
        'ACK Flag Cnt': ack_count,
        'Down/Up Ratio': down_up_ratio,
        'Fwd Seg Size Avg': fwd_seg_size_avg,
        'Bwd Seg Size Avg': bwd_seg_size_avg,
    }

    # Return as DataFrame to match scikit-learn training format
    df = pd.DataFrame([features], columns=FEATURES)
    
    # Sanitize: replace Inf/-Inf with large-but-finite caps, replace NaN with 0.
    # Live sessions can produce Inf when duration is extremely tiny (≈0),
    # and the CICIDS2017 dataset has known Inf values in packet/byte rate columns.
    df.replace([np.inf, -np.inf], np.nan, inplace=True)
    df.fillna(0, inplace=True)
    
    return df


