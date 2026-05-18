# NetSentinel: ML Flow Classification Engine Report

## 1. Overview
NetSentinel incorporates a robust, real-time Machine Learning Risk Engine designed to classify network traffic flows using supervised learning methodologies. The goal is to perform dynamic, deep packet anomaly detection and classify flows into "Benign" or "Malicious" categories, with further refinement into specific attack vectors. 

The implementation acts strictly as a supervised learning mechanism that relies heavily on flow-level characteristics instead of deep payload inspection for its primary ML gates, optimizing for high-throughput packet capture.

## 2. Dataset and Preprocessing
The engine is trained on two highly recognized, industry-standard network intrusion datasets:
- **UNSW-NB15 Dataset:** A modern dataset containing normal and contemporary attack activities.
- **CICIDS2017 Dataset:** Known for realistic background traffic and extensive attack profiles (DDoS, Brute Force, Web Attacks).

### 2.1 Feature Engineering
The raw pcap/flow data is mapped into a specific subset of features designed for NetSentinel. The following features are utilized in the classification models:
*   **Time-based:** `flow_duration` (clipped to 0.001s min)
*   **Volume-based:** `total_packets`, `total_bytes`, `avg_packet_size`
*   **Rate-based:** `packet_rate` (packets/sec), `byte_rate` (bytes/sec)
*   **Flag Counts:** `syn_count`, `ack_count`, `fin_count`, `rst_count`
*   **Protocol Encoding (One-Hot):** `proto_tcp`, `proto_udp`, `proto_icmp`, `proto_other`

### 2.2 Data Cleaning and Normalization
- Missing or infinite values in the dataset are replaced with zeros or NaN-handled gracefully.
- The numeric columns (e.g., duration, rates, byte counts) are scaled using `StandardScaler` (Scikit-Learn). 
- The resulting `scaler.pkl` artifact is saved for deployment to ensure live network flows undergo the exact same normalization during real-time inference.

## 3. Model Architecture

The NetSentinel predictor system employs a **Two-Stage Gate Architecture** utilizing Scikit-Learn algorithms (primarily `RandomForest`).

### Stage 1: Binary Gate (Benign vs. Malicious)
Every active flow is extracted and passed to the binary model. The model outputs a probability (risk score).
- **Thresholding Strategy:** Network ML models often suffer from False Positives on standard home/office networks due to irregular but benign background traffic. To counteract this, a strict **85% confidence threshold** (`risk_score < 0.85`) is applied. Any flow scoring below 85% malicious probability is automatically overridden to "Benign."

### Stage 2: Multiclass Refinement (Attack Typing)
If a flow passes the binary gate (is confirmed malicious), it is immediately fed to a secondary `multiclass_model`. This model analyzes the same normalized features to classify the exact nature of the attack based on the patterns learned from the CICIDS/UNSW datasets. 
- *Fallback Mechanism:* If the models (`.pkl` files) are absent in the local environment, the engine seamlessly downgrades to a deterministic mock heuristic logic, primarily flagging high volumetric flows (>1,000 pkts/s) as malicious.

## 4. Threat Generation & Validation (Simulation)
To validate the model's accuracy, the project includes universal attack simulators (`attack.py` and `simulate_attack.py`) that generate realistic, multi-vector malicious traffic against local interfaces:
1.  **Volumetric UDP/SYN Floods (DoS):** Creates high `packet_rate` and `syn_count` anomalies.
2.  **TCP Port Scans:** Creates rapid, low-duration connection flows.
3.  **SSH Brute Force Simulation:** Simulates noisy, repetitive login attempts.
4.  **DNS Amplification:** Exploits UDP by sending excessively large payloads, testing the `avg_packet_size` and `byte_rate` feature boundaries.
5.  **Xmas Tree Protocol Anomaly:** Injects illegal packet flags (`FPU`) to test flag-based feature correlations.

## 5. Conclusion
NetSentinel’s approach strictly adheres to reality-based flow classification. By relying on robust, deterministic feature mapping combined with high-confidence ensemble tree classifiers (RandomForest), the tool efficiently distinguishes legitimate network usage from active security threats in real-time, completely dynamically.
