import pandas as pd
import numpy as np
from sklearn.preprocessing import StandardScaler
import os
import glob
from feature_extractor.extractor import FEATURES

def validate_datasets(base_path: str):
    """Check what datasets are available to train on."""
    unsw_train = os.path.join(base_path, "UNSW_NB15_training-set.csv")
    unsw_test = os.path.join(base_path, "UNSW_NB15_testing-set.csv")
    
    cicids_files = glob.glob(os.path.join(base_path, "*ISCX.csv"))
    
    has_unsw = os.path.exists(unsw_train) and os.path.exists(unsw_test)
    has_cicids = len(cicids_files) > 0
    
    return has_unsw, has_cicids, unsw_train, unsw_test, cicids_files

def load_unsw_nb15(train_path: str, test_path: str):
    print("Loading UNSW-NB15 dataset...")
    df_train = pd.read_csv(train_path)
    df_test = pd.read_csv(test_path)
    df = pd.concat([df_train, df_test], axis=0, ignore_index=True)

    df["flow_duration"] = df["dur"].clip(lower=0.001)
    df["total_packets"] = df["spkts"] + df["dpkts"]
    df["total_bytes"] = df["sbytes"] + df["dbytes"]
    df["avg_packet_size"] = df["total_bytes"] / df["total_packets"]

    df["packet_rate"] = df["total_packets"] / df["flow_duration"]
    df["byte_rate"] = df["total_bytes"] / df["flow_duration"]

    df["syn_count"] = 0
    df["ack_count"] = 0
    df["fin_count"] = 0
    df["rst_count"] = 0

    proto_str = df["proto"].astype(str).str.upper()
    df["proto_tcp"] = (proto_str == "TCP").astype(int)
    df["proto_udp"] = (proto_str == "UDP").astype(int)
    df["proto_icmp"] = (proto_str.isin(["ICMP", "IGMP"])).astype(int)
    df["proto_other"] = (~proto_str.isin(["TCP", "UDP", "ICMP", "IGMP"])).astype(int)

    X = df[FEATURES].copy()
    y = df["label"].values
    
    return X, y

def load_cicids2017(file_paths: list):
    print(f"Loading CICIDS2017 ({len(file_paths)} files)...")
    dfs = []
    # Only load a subset of data or it blows up memory for training
    for p in file_paths:
        print(f"  Reading {os.path.basename(p)}")
        df = pd.read_csv(p, engine="python", on_bad_lines="skip")
        df.columns = df.columns.str.strip()
        dfs.append(df)
        
    df = pd.concat(dfs, axis=0, ignore_index=True)
    
    print("Mapping CICIDS2017 to DeepShark features...")
    df["flow_duration"] = (df["Flow Duration"] / 1e6).clip(lower=0.001) # microseconds to seconds
    df["total_packets"] = df["Total Fwd Packets"] + df["Total Backward Packets"]
    df["total_bytes"] = df["Total Length of Fwd Packets"] + df["Total Length of Bwd Packets"]
    df["avg_packet_size"] = df["total_bytes"] / df["total_packets"]
    
    df["packet_rate"] = df["Flow Packets/s"]
    df["byte_rate"] = df["Flow Bytes/s"]
    
    df["syn_count"] = df["SYN Flag Count"]
    df["ack_count"] = df["ACK Flag Count"]
    df["fin_count"] = df["FIN Flag Count"]
    df["rst_count"] = df["RST Flag Count"]
    
    # Protocol is numeric in CICIDS (6=TCP, 17=UDP, 1=ICMP)
    if "Protocol" in df.columns:
        proto = df["Protocol"]
        df["proto_tcp"] = (proto == 6).astype(int)
        df["proto_udp"] = (proto == 17).astype(int)
        df["proto_icmp"] = (proto == 1).astype(int)
        df["proto_other"] = (~proto.isin([1, 6, 17])).astype(int)
    else:
        # Fallback if Protocol column is missing from CSV
        # Infer TCP based on presence of TCP-specific flags
        is_tcp = (df["syn_count"] > 0) | (df["fin_count"] > 0) | (df["ack_count"] > 0) | (df["rst_count"] > 0)
        df["proto_tcp"] = is_tcp.astype(int)
        # We'll generously assume the rest is UDP for training purposes
        df["proto_udp"] = (~is_tcp).astype(int)
        df["proto_icmp"] = 0
        df["proto_other"] = 0
    
    X = df[FEATURES].copy()
    
    # Label is string "BENIGN" or attack name
    label_str = df["Label"].astype(str).str.upper()
    y = (label_str != "BENIGN").astype(int)
    
    return X, y

def load_and_preprocess(base_path: str):
    has_unsw, has_cicids, unsw_train, unsw_test, cicids_files = validate_datasets(base_path)
    
    Xs, ys = [], []
    
    if has_unsw:
        x_unsw, y_unsw = load_unsw_nb15(unsw_train, unsw_test)
        Xs.append(x_unsw)
        ys.append(y_unsw)
        
    if has_cicids:
        x_cic, y_cic = load_cicids2017(cicids_files)
        Xs.append(x_cic)
        ys.append(y_cic)
        
    if not Xs:
        raise ValueError("No valid datasets found in: " + base_path)
        
    X = pd.concat(Xs, axis=0, ignore_index=True)
    y = np.concatenate(ys, axis=0)
    
    print(f"Combined dataset: {len(X)} samples, {y.sum()} malicious.")
    
    print("Cleaning & Scaling data...")
    X.replace([np.inf, -np.inf], np.nan, inplace=True)
    X.fillna(0, inplace=True)

    scaler = StandardScaler()
    numeric_cols = ["flow_duration", "total_packets", "total_bytes", "avg_packet_size", "packet_rate", "byte_rate", "syn_count", "ack_count", "fin_count", "rst_count"]
    X[numeric_cols] = scaler.fit_transform(X[numeric_cols])
    
    return X, y, scaler
