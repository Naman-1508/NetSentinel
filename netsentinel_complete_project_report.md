# NetSentinel: Comprehensive Technical & Architecture Report
**Version 1.0 | May 2026**

---

## Table of Contents
1. Executive Summary
2. Project Identity & Scope
3. High-Level System Architecture
4. Machine Learning Risk Engine — Deep Dive
   - 4.1 The CSE-CIC-IDS2018 Dataset
   - 4.2 Label Distribution & Class Imbalance
   - 4.3 Chronological Train/Test Split
   - 4.4 Feature Engineering: The 25-Dimensional Flow Vector
   - 4.5 Data Preprocessing & RobustScaler
   - 4.6 XGBoost Binary Classifier — Hyperparameters
   - 4.7 Cross-Validation & Training Performance
   - 4.8 Threshold Sweep & False Positive Mitigation
   - 4.9 Final Evaluation Metrics
   - 4.10 SHAP Explainability
   - 4.11 Serialized Artifact Set
5. Live Feature Extraction Pipeline
6. Frontend Architecture
   - 6.1 Technology Stack
   - 6.2 DOM Virtualization via react-window
   - 6.3 State Management via Zustand
   - 6.4 Component Ecosystem
   - 6.5 Dual Filter Engine
7. Backend Packet Capture Engine
   - 7.1 Hybrid Strategy Overview
   - 7.2 Thread 1 — nfstream (Layer 3/4 Flow Engine)
   - 7.3 Thread 2 — Scapy (Layer 2 MAC Cache)
   - 7.4 Thread Safety Model
   - 7.5 Windows Npcap Driver Integration
8. WebSocket IPC Layer
   - 8.1 asyncio Server
   - 8.2 Batch Broadcaster
   - 8.3 Control Plane Protocol
   - 8.4 Session Manager
9. Attack Simulation & Validation Framework
10. Build & Deployment Pipeline
    - 10.1 PowerShell Build Automation
    - 10.2 Next.js Static Export
    - 10.3 PyInstaller Freezing
    - 10.4 PyWebView Desktop Wrapper
    - 10.5 NSIS Installer
11. Operating System Security Integrations
    - 11.1 UAC Elevation Check
    - 11.2 Global Singleton Mutex
    - 11.3 Logging Infrastructure
12. Conclusion & Future Roadmap

---

## 1. Executive Summary

NetSentinel is a real-time network packet analysis platform that combines high-throughput traffic capture with an embedded machine learning risk scoring engine. It operates as a standalone desktop application on Windows 10/11, wrapping a Python backend inside a native OS window using PyWebView, with a React/Next.js interface for live traffic visualization.

The platform is designed to give security engineers and network administrators an immediate, ML-augmented view of every network flow traversing their machine or monitored interface. Every captured network flow is scored in real-time against a binary classification model (Benign or Malicious) trained on the CSE-CIC-IDS2018 dataset — one of the most comprehensive and realistic network security datasets available publicly.

NetSentinel is explicitly **not** an Intrusion Detection System (IDS). It is a network packet analyzer with an integrated ML risk scoring engine. It does not issue alerts to a SIEM, does not maintain rule sets, and does not act on traffic autonomously. It provides live, human-readable threat intelligence scores to the analyst through a premium desktop UI.

---

## 2. Project Identity & Scope

### What NetSentinel Does
- Captures raw network packets from a selected Windows network adapter in promiscuous mode.
- Aggregates packets into bidirectional network flows using `nfstream`.
- Extracts a 25-feature statistical vector from each completed flow.
- Feeds that vector through a trained XGBoost binary classifier to obtain a Malicious/Benign score with a confidence probability.
- Applies an 85% confidence threshold before labelling any flow as malicious, minimizing false positives.
- Streams all data to a React UI in real-time via WebSocket.
- Renders the hex payload of any selected packet for deep inspection.

### What NetSentinel Does NOT Do
- It does not classify attacks by type (no "DoS", "Brute Force", "XSS" labels).
- It does not send alerts to external systems.
- It does not modify firewall rules autonomously.
- It does not require cloud connectivity.

### Supported Environment
- **OS:** Windows 10 / Windows 11 (64-bit)
- **Privilege:** Administrator required
- **Dependency:** Npcap installed in WinPcap API-compatible mode
- **Runtime:** Self-contained via PyInstaller; no Python or Node.js installation needed by the end user

---

## 3. High-Level System Architecture

NetSentinel follows a localized client-server model unified inside a single executable:

```
┌──────────────────────────────────────────────────────────────────┐
│                    NetSentinel.exe (PyInstaller)                  │
│                                                                    │
│  ┌──────────────┐    WebSocket     ┌──────────────────────────┐  │
│  │  Python      │◄────────────────►│  Next.js/React (Static)  │  │
│  │  Backend     │   ws://localhost  │  Served via PyWebView    │  │
│  │  (main.py)   │      :8765        │  (Chromium Edge Engine)  │  │
│  └──────┬───────┘                  └──────────────────────────┘  │
│         │                                                          │
│  ┌──────┴────────────────────────────────────┐                   │
│  │           PacketCaptureEngine              │                   │
│  │  Thread 1: NFStreamer (Layer 3/4 flows)    │                   │
│  │  Thread 2: Scapy sniffer (Layer 2 MACs)   │                   │
│  └──────┬────────────────────────────────────┘                   │
│         │                                                          │
│  ┌──────┴────────────────┐                                        │
│  │   RiskPredictor        │                                       │
│  │   (ml_risk_engine/)    │                                       │
│  │   model.pkl (XGBoost)  │                                       │
│  │   scaler.pkl           │                                       │
│  │   explainer.pkl (SHAP) │                                       │
│  └───────────────────────┘                                        │
└──────────────────────────────────────────────────────────────────┘
```

### Repository Layout
```
PacketCapturingTool/
├── backend/
│   ├── main.py            # asyncio WebSocket server, PyWebView launcher
│   ├── capture.py         # PacketCaptureEngine (nfstream + Scapy threads)
│   ├── interfaces.py      # Adapter enumeration
│   └── session_manager.py # Flow session tracking
├── frontend/
│   ├── src/               # React components, Zustand stores, pages
│   └── out/               # Built static export (after npm run build)
├── ml_risk_engine/
│   ├── predictor/
│   │   └── predictor.py   # RiskPredictor class
│   └── feature_extractor/
│       └── extractor.py   # extract_features() — live 25-feature mapping
├── Offline2/offline/
│   ├── train.ipynb        # Training notebook (master ML pipeline)
│   └── artifacts/         # model.pkl, scaler.pkl, explainer.pkl, feature_list.pkl
├── simulate_attack.py     # Multi-vector attack simulation framework
├── attack.py              # Low-level raw socket attack primitives
├── build-installer.ps1    # One-click build & packaging script
└── README.md
```

---

## 4. Machine Learning Risk Engine — Deep Dive

### 4.1 The CSE-CIC-IDS2018 Dataset

The model is trained exclusively on the **CSE-CIC-IDS2018** dataset, produced collaboratively by the Canadian Institute for Cybersecurity (CIC) and the Communications Security Establishment (CSE). It is among the most rigorous and realistic publicly available network security datasets, capturing actual attack traffic generated in a controlled but realistic lab environment across multiple days in February and March 2018.

The dataset is provided as pre-processed CICFlowMeter CSV files — one file per capture day — each containing 80 statistical flow features plus a `Label` column. NetSentinel uses 10 of these files.

**Raw Dataset Statistics:**
| File | Attack Type | Benign Flows | Attack Flows |
|---|---|---|---|
| Wednesday-14-02-2018 | FTP-BruteForce, SSH-Bruteforce | 667,626 | 380,949 |
| Thursday-15-02-2018 | DoS GoldenEye, DoS Slowloris | 996,077 | 52,498 |
| Wednesday-21-02-2018 | DDoS HOIC, DDoS LOIC-UDP | 360,833 | 687,742 |
| Thursday-22-02-2018 | Brute Force -Web, XSS, SQLi | 1,048,213 | 362 |
| Wednesday-28-02-2018 | Infiltration | 544,200 | 68,871 |
| Thursday-01-03-2018 | Infiltration (cont.) | 238,037 | 93,063 |
| Friday-16-02-2018 | DoS Hulk, DoS SlowHTTPTest | 446,772 | 601,802 |
| Friday-23-02-2018 | Brute Force -Web, XSS, SQLi | 1,048,009 | 566 |
| Friday-02-03-2018 | Botnet | 762,384 | 286,191 |
| Tuesday-20-02-2018 | DDoS LOIC-HTTP | 7,372,557 | 576,191 |

After deduplication, Inf/NaN removal, and combining all files: **9,777,285 valid flow records**.

### 4.2 Label Distribution & Class Imbalance

The full cleaned dataset contains:
- **Benign:** 8,487,399 flows (86.8%)
- **Malicious:** 1,289,886 flows (13.2%)

This ~6.87:1 imbalance is critical. A naive model that always predicts "Benign" achieves 86.8% accuracy while detecting zero attacks — an obviously useless outcome. NetSentinel addresses this via `scale_pos_weight` in XGBoost (see Section 4.6).

All attack labels (FTP-BruteForce, SSH-Bruteforce, DoS attacks-Hulk, DDOS attack-HOIC, Bot, Infilteration, Brute Force -Web, Brute Force -XSS, SQL Injection, DoS attacks-GoldenEye, DoS attacks-Slowloris, DDOS attack-LOIC-UDP, DDoS attacks-LOIC-HTTP, DoS attacks-SlowHTTPTest) are binarized into a single `Attack` label (1), with `Benign` mapped to 0.

### 4.3 Chronological Train/Test Split

Standard random Train/Test splits would allow the model to see future attack patterns during training, leaking information and inflating test metrics. NetSentinel uses a **strict chronological split**:

**Training Set (Wednesday & Thursday captures):**
- Files: Wed-14-Feb, Thu-15-Feb, Wed-21-Feb, Thu-22-Feb, Wed-28-Feb, Thu-01-Mar
- Total: ~3,132,600 rows
- Benign: 2,684,207 | Attack: 448,393
- `scale_pos_weight` (neg/pos ratio): **5.99**
- Attack types present: FTP/SSH BruteForce, DoS GoldenEye/Slowloris, DDoS HOIC/LOIC-UDP, Web Attacks, Infiltration

**Test Set (Friday & Tuesday captures):**
- Files: Fri-16-Feb, Fri-23-Feb, Fri-02-Mar, Tue-20-Feb
- Total: ~6,644,685 rows
- Benign: 5,803,192 | Attack: 841,493
- Attack types present: DoS Hulk (**UNSEEN**), DoS SlowHTTPTest (**UNSEEN**), Botnet (**UNSEEN**), DDoS LOIC-HTTP (**UNSEEN**), minor Web Attacks

The test set attacks are entirely **different attack families** from those seen during training, emulating a real-world zero-day evaluation. If the model generalizes well, it has learned *behavioral anomaly patterns* rather than memorized signatures.

### 4.4 Feature Engineering: The 25-Dimensional Flow Vector

From the 80 available CICFlowMeter columns, 25 were carefully selected based on attack discriminative power, computational availability from live flows, and absence of dataset-specific leakage.

**Category 1 — Flow Timing & Duration:**
| Feature | Description |
|---|---|
| `Flow Duration` | Total elapsed time of the bidirectional flow in microseconds |
| `Flow IAT Mean` | Mean inter-arrival time across all packets in the flow (both directions) |
| `Fwd IAT Mean` | Mean inter-arrival time of forward (client→server) packets |
| `Bwd IAT Mean` | Mean inter-arrival time of backward (server→client) packets |

Timing features are highly discriminative: DoS floods produce near-zero IAT (packets arrive as fast as possible), while idle connections have very large IAT.

**Category 2 — Packet Counts:**
| Feature | Description |
|---|---|
| `Tot Fwd Pkts` | Total packets sent in the forward direction |
| `Tot Bwd Pkts` | Total packets received in the backward direction |

Asymmetric counts (many forward, zero backward) are strong indicators of one-way flooding attacks.

**Category 3 — Byte Volumes:**
| Feature | Description |
|---|---|
| `TotLen Fwd Pkts` | Total bytes in all forward packets |
| `TotLen Bwd Pkts` | Total bytes in all backward packets |

**Category 4 — Packet Length Statistics:**
| Feature | Description |
|---|---|
| `Fwd Pkt Len Max` | Largest single packet in the forward direction |
| `Fwd Pkt Len Min` | Smallest single packet in the forward direction |
| `Fwd Pkt Len Mean` | Mean forward packet size |
| `Bwd Pkt Len Max` | Largest single packet in the backward direction |
| `Bwd Pkt Len Min` | Smallest single packet in the backward direction |
| `Bwd Pkt Len Mean` | Mean backward packet size |
| `Fwd Seg Size Avg` | Average forward segment size (bytes per fwd packet) |
| `Bwd Seg Size Avg` | Average backward segment size (bytes per bwd packet) |

SYN flood attacks produce very small forward packets (just the SYN header, ~60 bytes) with zero backward responses. HTTP GET floods produce larger uniform-size requests.

**Category 5 — Flow Velocity:**
| Feature | Description |
|---|---|
| `Flow Byts/s` | Total bytes (both directions) per second of flow duration |
| `Flow Pkts/s` | Total packets (both directions) per second |

These are the most explosive DoS indicators. A legitimate HTTP download may reach 10 MB/s; a DoS Hulk attack can push 500 MB/s on a Gigabit link.

**Category 6 — Asymmetry:**
| Feature | Description |
|---|---|
| `Down/Up Ratio` | `bwd_bytes / fwd_bytes` — ratio of received to sent bytes |

Normal web browsing has a high Down/Up ratio (server sends more). Amplification attacks (DNS/NTP amplification) have extremely high Down/Up ratios. Port scans have a Down/Up ratio near zero (no response).

**Category 7 — TCP Flag Counts:**
| Feature | Description |
|---|---|
| `Fwd PSH Flags` | Count of PSH flags in forward packets |
| `FIN Flag Cnt` | Total FIN flags across the flow |
| `SYN Flag Cnt` | Total SYN flags — SYN floods set this extremely high |
| `RST Flag Cnt` | RST count — port scanners generate RSTs for closed ports |
| `PSH Flag Cnt` | Total PSH flags — used in data exfiltration patterns |
| `ACK Flag Cnt` | Total ACK flags |

TCP flag abuse is one of the most reliable attack fingerprints. A SYN flood has `SYN Flag Cnt` >> `ACK Flag Cnt` with no FINs; a Xmas scan has PSH+URG+FIN all set simultaneously.

### 4.5 Data Preprocessing & RobustScaler

**Infinite Value Handling:**
Raw network statistics contain IEEE 754 `Inf` and `-Inf` values, typically in rate columns when a flow's duration rounds to zero. During training, the pipeline replaces `Inf/-Inf` with `np.nan` and then `dropna()`. During live inference, the `extract_features()` function clamps these values to 0 before scaling.

**Deduplication:**
`df.drop_duplicates(subset=FEATURES + ['Label'])` removes flows with identical feature vectors and label, reducing dataset noise while preserving class balance.

**float32 Downcast:**
All feature columns are downcast from `float64` to `float32` to halve memory usage during training on the 9.7M-row dataset.

**RobustScaler:**
Network data is dominated by outliers. A single DDoS flow may have `Flow Byts/s` = 5,000,000 while 95% of flows have values under 50,000. Standard `StandardScaler` (which uses mean and std) would compress the entire benign distribution into a tiny band.

`RobustScaler` instead uses the **Interquartile Range (IQR)**:

```
X_scaled = (X - median(X)) / IQR(X)
```

This makes it immune to extreme outliers. The scaler is **fit only on the training set** and serialized to `scaler.pkl`. During live inference, each flow vector is transformed using the pre-fit scaler, ensuring consistent feature scaling to match training conditions.

### 4.6 XGBoost Binary Classifier — Hyperparameters

The final model is an `XGBClassifier` from the `xgboost` Python library. XGBoost (eXtreme Gradient Boosting) builds an ensemble of decision trees sequentially, where each tree corrects the errors of the previous. It is the industry standard for tabular binary classification tasks.

**Full Hyperparameter Configuration:**
```python
XGBClassifier(
    n_estimators     = 300,      # 300 sequential decision trees
    max_depth        = 8,        # Max tree depth — captures complex interactions
    learning_rate    = 0.05,     # Small step size — prevents overfitting
    subsample        = 0.8,      # 80% of rows sampled per tree (row bagging)
    colsample_bytree = 0.8,      # 80% of features sampled per tree
    scale_pos_weight = 5.99,     # Balances 6:1 class imbalance
    min_child_weight = 3,        # Minimum samples in leaf — regularization
    base_score       = 0.5,      # Initial prediction
    random_state     = 42,
    n_jobs           = -1,       # All CPU cores during training
    eval_metric      = 'logloss',
    verbosity        = 0
)
```

**`scale_pos_weight` Explained:**
This is the most critical hyperparameter for imbalanced network data. It tells XGBoost to weight each malicious sample as if it were 5.99 benign samples, effectively telling the model: "missing an attack is ~6x worse than a false positive." The value is computed directly from the training set split ratio: `2,684,207 benign / 448,393 attack = 5.99`.

### 4.7 Cross-Validation & Training Performance

Before the final training run, the model is evaluated via **5-Fold Stratified Cross-Validation** on the training set to confirm stability:

```
CV F1 Scores: [0.8054, 0.8035, 0.8060, 0.8094, 0.8024]
Mean F1: 0.8054 ± 0.0024
```

The minimal standard deviation (0.0024) confirms the model is not overfitting to a specific fold. Final training on the full training set completed in **74.8 seconds** on a mid-tier CPU using all cores (`n_jobs=-1`).

### 4.8 Threshold Sweep & False Positive Mitigation

The default XGBoost probability threshold of 0.50 is unsuitable for live network monitoring environments where false positives cause analyst fatigue. The training notebook performs a **full threshold sweep** across the chronological test set:

| Threshold | FPR% | FNR% | F1 | Precision | Recall |
|---|---|---|---|---|---|
| 0.50 | 3.75 | 49.53 | 0.5725 | 0.6614 | 0.5047 |
| 0.60 | 0.78 | 59.47 | 0.5557 | 0.8834 | 0.4053 |
| 0.70 | 0.42 | 60.32 | 0.5568 | 0.9325 | 0.3968 |
| 0.80 | 0.32 | 63.10 | 0.5305 | 0.9429 | 0.3690 |
| **0.85** | **0.30** | **65.59** | **0.5043** | **0.9436** | **0.3441** |
| 0.90 | 0.26 | 68.67 | 0.4708 | 0.9467 | 0.3133 |

NetSentinel uses **BINARY_THRESHOLD = 0.85**. At this threshold:
- Only **0.30% of benign flows** are incorrectly flagged as malicious.
- When a flow IS flagged, there is a **94.36% chance it is truly malicious**.
- The tradeoff is a higher False Negative Rate (65.59%) — some attacks are missed. This is a deliberate design decision: in a real-time monitoring UI, **a 94% precision alarm** is far more actionable than a 66% precision alarm that overwhelms analysts with noise.

### 4.9 Final Evaluation Metrics (at threshold 0.85)

Test set evaluation on 6,644,685 unseen flows:
```
              precision    recall  f1-score   support

      Benign       0.91      1.00      0.95   5,803,192
      Attack       0.94      0.34      0.50     841,493

    accuracy                           0.91   6,644,685
   macro avg       0.93      0.67      0.73   6,644,685
weighted avg       0.92      0.91      0.90   6,644,685

ROC-AUC: 0.8288
```

The ROC-AUC of **0.8288** is particularly significant because it is computed against entirely unseen attack families (Botnet, DoS Hulk, DDoS LOIC-HTTP), confirming the model has learned generalizable behavioral patterns rather than attack-specific signatures.

### 4.10 SHAP Explainability

ML models are often criticized as "black boxes." NetSentinel integrates **SHAP (SHapley Additive exPlanations)** via a serialized `TreeExplainer` to provide per-flow attribution analysis.

SHAP decomposes the model's prediction for any individual flow into a sum of feature contributions:

```
Prediction = base_value + SHAP(Flow Byts/s) + SHAP(SYN Flag Cnt) + ... + SHAP(Fwd IAT Mean)
```

For example, a flow scored 97% malicious might produce:
- `SYN Flag Cnt` contribution: +0.45 (strong push toward malicious)
- `Fwd Pkt Len Mean` contribution: -0.12 (small push toward benign)
- `Flow Pkts/s` contribution: +0.31 (moderate push toward malicious)

The `explainer.pkl` artifact (12.0 MB) is the serialized SHAP TreeExplainer bound to the trained model. It can compute SHAP values for individual flows in microseconds, enabling future UI features to display per-flow explanations.

### 4.11 Serialized Artifact Set

All training outputs are serialized to `Offline2/artifacts/`:
| Artifact | Size | Purpose |
|---|---|---|
| `model.pkl` | 3.2 MB | Trained XGBoost binary classifier |
| `scaler.pkl` | ~2 KB | Fitted RobustScaler (25 features) |
| `explainer.pkl` | 12.0 MB | SHAP TreeExplainer for per-flow attribution |
| `feature_list.pkl` | ~1 KB | Ordered list of 25 feature names |

These four files are bundled into `NetSentinel.exe` via PyInstaller's `--add-data` mechanism and located at runtime using a multi-path search strategy (see Section 10.3).

---

## 5. Live Feature Extraction Pipeline

The gap between "trained on CSV data" and "inference on live packets" is one of the hardest engineering challenges in applied ML. CICFlowMeter features are computed over completed bidirectional flows, but NetSentinel must produce equivalent features from live, partially-completed network sessions.

This mapping is implemented in `ml_risk_engine/feature_extractor/extractor.py` — the `extract_features(session: dict) -> pd.DataFrame` function.

### Session Dictionary Structure

The `PacketCaptureEngine` builds a session dictionary per bidirectional flow containing raw counters accumulated in real-time:

```python
session = {
    "duration": float,          # seconds since first packet
    "packet_count": int,        # total packets both directions
    "bytes": int,               # total bytes both directions
    "fwd_pkts": int,            # forward packet count
    "bwd_pkts": int,            # backward packet count
    "fwd_bytes": int,           # forward total bytes
    "bwd_bytes": int,           # backward total bytes
    "fwd_pkt_len_max": int,
    "fwd_pkt_len_min": int,
    "fwd_pkt_len_sum": int,     # sum used to derive mean
    "bwd_pkt_len_max": int,
    "bwd_pkt_len_min": int,
    "bwd_pkt_len_sum": int,
    "fwd_iat_sum": float,       # sum of all forward inter-arrival times
    "fwd_iat_count": int,
    "bwd_iat_sum": float,
    "bwd_iat_count": int,
    "fwd_psh_count": int,
    "psh_count": int,
    "syn_count": int,
    "fin_count": int,
    "rst_count": int,
    "ack_count": int,
    "src_ip": str,
    "dst_ip": str,
}
```

### Derived Feature Calculations

```python
# Means derived from sums
fwd_pkt_len_mean = fwd_pkt_len_sum / fwd_pkts  (if fwd_pkts > 0)
bwd_pkt_len_mean = bwd_pkt_len_sum / bwd_pkts  (if bwd_pkts > 0)
flow_iat_mean    = (fwd_iat_sum + bwd_iat_sum) / (fwd_iat_count + bwd_iat_count)
fwd_iat_mean     = fwd_iat_sum / fwd_iat_count
bwd_iat_mean     = bwd_iat_sum / bwd_iat_count

# Rate features (with minimum duration guard to prevent Inf)
duration         = max(duration, 0.001)
flow_byts_s      = total_bytes / duration
flow_pkts_s      = total_pkts / duration

# Derived ratios
down_up_ratio    = bwd_bytes / max(fwd_bytes, 1)
fwd_seg_size_avg = fwd_bytes / max(fwd_pkts, 1)
bwd_seg_size_avg = bwd_bytes / max(bwd_pkts, 1)
```

### Sanitization Pass

After building the feature DataFrame, the extractor applies a final sanitization:
```python
df.replace([np.inf, -np.inf], np.nan, inplace=True)
df.fillna(0, inplace=True)
```

This guards against edge cases like zero-duration flows (which would otherwise produce `Inf` in rate features) and ensures the DataFrame is always valid input for the `RobustScaler.transform()` call.

The function returns a single-row `pd.DataFrame` with columns in exactly the order expected by the trained model, as defined by `FEATURES` — the same list used during `train.ipynb`.

---

*[Part 2 continues: Sections 6–12]*

---

## 6. Frontend Architecture

### 6.1 Technology Stack

| Layer | Technology | Version | Role |
|---|---|---|---|
| Framework | Next.js | 16 | Routing, build pipeline, static export |
| UI Library | React | 19 | Component rendering |
| Styling | Tailwind CSS | v4 | Utility-first styling |
| List Rendering | react-window | latest | DOM virtualization |
| Auto-sizing | react-virtualized-auto-sizer | latest | Dynamic container measurement |
| State | Zustand | latest | Global store, zero-boilerplate |
| Protocol | WebSocket (native browser API) | — | Real-time packet streaming |

The frontend is compiled into a **fully static SPA** using `next export`. No server-side rendering is used; all pages are pre-rendered into plain HTML/JS/CSS files placed in `frontend/out/`. This static bundle is bundled inside the PyInstaller executable and served via PyWebView's embedded Chromium engine.

### 6.2 DOM Virtualization via react-window

The most critical frontend engineering challenge: a network capture can accumulate hundreds of thousands of packet rows. Rendering even 10,000 `<div>` elements simultaneously would exhaust browser memory and lock the UI.

**react-window** solves this with a technique called **windowed rendering** (also called virtual scrolling):

1. The `FixedSizeList` component measures the visible container height using `react-virtualized-auto-sizer`.
2. It divides the container height by the fixed row height to calculate how many rows fit on screen (typically 25–35 rows).
3. Only those rows are mounted to the DOM at any given time.
4. As the user scrolls, the existing DOM elements are **recycled in-place** — their data props are updated, but no new elements are created or destroyed.

This delivers **O(1) rendering complexity** regardless of dataset size. Whether there are 100 packets or 1,000,000, the browser maintains exactly the same ~30 DOM nodes.

```
Without react-window:   100,000 packets → 100,000 <div>s → browser freeze
With react-window:      100,000 packets → 30 <div>s    → 60fps smooth
```

### 6.3 State Management via Zustand

Standard React state management patterns (`useState`, `useReducer`, `Context`) are inappropriate for high-frequency WebSocket data. The problem: every time new packets arrive, React re-renders all components subscribed to the shared context — including the Hex Viewer, Stats Panel, and Filter Bar — even if they don't need the new packet data.

**Zustand** solves this with granular subscriptions:

```javascript
// Each component subscribes only to what it needs
const packets     = useStore(s => s.packets);       // Packet Table only
const selectedPkt = useStore(s => s.selectedPacket); // Hex Viewer only
const stats       = useStore(s => s.stats);          // Stats Panel only
```

When the WebSocket pushes 200 new packets, only the component subscribed to `s.packets` re-renders. The Hex Viewer and Stats Panel remain frozen until their own slices change. This eliminates cascading re-renders and preserves CPU cycles for the rendering pipeline.

Zustand's store also operates **outside React's render cycle**, meaning the WebSocket `onmessage` handler can call `store.setState()` directly from a background callback without triggering synchronous rendering — batching is handled by React 19's automatic batching scheduler.

### 6.4 Component Ecosystem

**Packet Table**
The primary visualization component. Renders a virtualized list of flow rows, each displaying:
- Timestamp (HH:MM:SS.mmm)
- Source IP : Port
- Destination IP : Port
- Source MAC / Destination MAC (from Scapy L2 cache)
- Protocol (TCP / UDP / ICMP / ARP)
- Flow duration (ms)
- Total bytes
- ML Risk Score (0–100%) with color-coded badge (green/yellow/red)
- Risk label (Benign / Malicious)

Clicking a row populates the Hex Dump Viewer and the Flow Detail panel.

**Hex Dump Viewer**
Renders the raw byte payload of the selected packet in classic Wireshark-style layout:
- Left column: byte offset (0000, 0010, 0020…)
- Center column: space-separated hex pairs (e.g., `45 00 00 3c 1a 46`)
- Right column: ASCII representation (printable characters shown, non-printable shown as `.`)

**Stats Panel**
Displays aggregate capture statistics updated in real-time:
- Total flows captured
- Protocol distribution (TCP / UDP / ICMP / Other counts)
- Malicious flow count and percentage
- Capture duration elapsed

**Interface Selector**
On capture start, queries the backend for available network adapters via the WebSocket control plane (`get_interfaces` command). Displays adapter display name, IP address, and device path. The user selects one before starting capture.

**Filter Bar**
Houses both filter mechanisms (see Section 6.5).

### 6.5 Dual Filter Engine

NetSentinel implements filtering at two distinct levels:

**BPF Filter (Backend Level):**
Berkeley Packet Filter syntax applied directly at the network adapter level by `nfstream`. This filter is passed at capture start time:
```json
{ "type": "start", "interface": "\\Device\\NPF_...", "filter": "tcp port 80" }
```
The BPF filter is processed in the kernel (via Npcap) — packets that don't match are never captured, never processed by nfstream, and never sent over the WebSocket. This is the most efficient filtering available.

**UI Display Filter (Frontend Level):**
A real-time regex or string filter applied over the Zustand store's packet array on every render cycle. It does not interrupt the live capture stream — packets continue arriving and being stored; only the *rendered* rows are filtered. Example: typing `192.168.1.1` instantly hides all rows where neither src_ip nor dst_ip match, without any backend round-trip.

---

## 7. Backend Packet Capture Engine

### 7.1 Hybrid Strategy Overview

The `PacketCaptureEngine` class (`backend/capture.py`) is the performance core of NetSentinel. It resolves a fundamental incompatibility between two requirements:

1. **High-throughput flow statistics** — requires aggregating hundreds of packets per flow and computing statistical features (means, maxes, rates) efficiently.
2. **Layer 2 visibility** — requires inspecting raw Ethernet frames to obtain MAC addresses, which are stripped by Layer 3 flow engines.

The solution: two concurrent threads, each optimized for its specific task, sharing a thread-safe MAC cache.

### 7.2 Thread 1 — nfstream (Layer 3/4 Flow Engine)

`nfstream` is a Python wrapper around a C-based DPI engine. It operates as a **flow aggregator**: rather than yielding one Python object per packet, it accumulates all packets belonging to the same bidirectional flow (same src/dst IP/port tuple) and yields a single completed flow object when the flow terminates (FIN/RST) or times out.

**nfstream Configuration:**
```python
streamer = NFStreamer(
    source=interface,
    bpf_filter=bpf_filter,
    statistical_analysis=True,    # Compute flow statistics
    splt_analysis=0,              # Disable early-terminated flow analysis
    n_dissections=20,             # Protocol dissection depth
    idle_timeout=15,              # Emit idle flows after 15s of silence
    active_timeout=300,           # Force-emit flows lasting >5 minutes
)
```

nfstream processes packets in its C thread, accumulating byte counts, packet counts, IAT statistics, and TCP flags per flow. Python receives only the completed `NFlow` object — a namedtuple with 40+ statistical fields. This avoids the Python GIL bottleneck of per-packet processing.

The nfstream thread runs in `_sniff_loop_nfstream()`, which iterates the streamer's flow iterator and, for each emitted flow:
1. Converts the `NFlow` fields into the session dictionary format.
2. Looks up the MAC cache for the flow's IP pair.
3. Passes the enriched session to the `RiskPredictor.predict()` for ML scoring.
4. Enqueues the scored packet dict into the WebSocket batch buffer.

The thread respects `_stop_flag` and `_paused` threading Events for clean lifecycle management.

### 7.3 Thread 2 — Scapy (Layer 2 MAC Cache)

Because nfstream aggregates at Layer 3, it has no visibility into Ethernet frame headers. MAC addresses are essential for:
- Identifying physical devices even when IP addresses are dynamically assigned (DHCP)
- ARP spoofing detection
- Complete flow attribution in a switched network

The Scapy thread (`_sniff_loop_scapy_layer2()`) runs a parallel, lightweight sniff loop:

```python
sniff(
    iface=interface,
    prn=self._mac_callback,  # Called per Ethernet frame
    store=False,              # Don't accumulate in memory
    stop_filter=lambda _: self._stop_flag.is_set(),
)
```

The `_mac_callback` inspects each Ethernet frame for an IP layer and records:
```python
self._mac_cache[(src_ip, dst_ip)] = (src_mac, dst_mac)
```

The cache is a plain `dict` guarded by the existing `_lock`. Since MAC addresses for a given IP pair rarely change during a session, write contention is minimal. The nfstream thread performs read-only lookups — if a mapping is missing (race condition at flow start), the flow is emitted with empty MAC fields rather than blocking.

If Scapy is not installed (detected by the `HAS_SCAPY` flag at import time), the Layer 2 thread is silently skipped and the MAC fields are left empty — the system degrades gracefully.

### 7.4 Thread Safety Model

The engine uses Python's `threading` module with two `threading.Event` objects for lifecycle control:

- `_running`: Set when capture is active; cleared on stop.
- `_paused`: Set when capture is paused; nfstream thread checks this before yielding each flow to the callback (paused flows are discarded silently).
- `_stop_flag`: Signals both threads to terminate their loops.

Both capture threads are started as `daemon=True`, ensuring they are terminated automatically if the main process exits unexpectedly (e.g., window close) without requiring explicit cleanup calls.

The public API is fully thread-safe: `start()`, `stop()`, `pause()`, and `resume()` all acquire `_lock` before modifying state, preventing concurrent state corruption from the WebSocket command handler.

### 7.5 Windows Npcap Driver Integration

Windows 10/11 restricts raw socket access in user mode. Capturing promiscuous-mode traffic requires a kernel driver. NetSentinel mandates **Npcap** installed in **WinPcap API-compatible mode**.

The backend performs two pre-capture checks:

```python
def _is_windows_admin() -> bool:
    return bool(ctypes.windll.shell32.IsUserAnAdmin())

def _has_npcap() -> bool:
    return os.path.exists(r"C:\Windows\System32\Npcap\Packet.dll")
```

`Packet.dll` is the WinPcap-compatible shim that nfstream and Scapy both use as their kernel interface. Its presence at that path confirms Npcap is installed with API compatibility mode enabled.

If either check fails, the capture start is aborted and an error message is sent to the frontend via the WebSocket error channel.

---

## 8. WebSocket IPC Layer

### 8.1 asyncio Server

The backend's entry point (`main.py`) runs a `websockets.serve()` server inside a dedicated `asyncio` event loop thread. This is necessary because PyWebView (which runs the UI window) occupies the main thread on Windows.

```python
asyncio.set_event_loop(asyncio.new_event_loop())
server = await websockets.serve(handler, host, port)  # default: localhost:8765
```

The server accepts connections from the embedded Next.js frontend (running inside PyWebView's Chromium Edge context). Because both the server and client are on localhost, there is no network latency — the WebSocket operates over the loopback interface at memory speed.

### 8.2 Batch Broadcaster

If the network is carrying 10,000 packets per second and each packet triggered an individual WebSocket `send()` call, the async event loop would be overwhelmed with 10,000 coroutine dispatches per second. Each `send()` involves JSON serialization, TCP framing, and a loopback write — far too expensive at that rate.

The Batch Broadcaster solves this:

```python
PACKET_BATCH: List[Dict] = []
BATCH_LOCK = threading.Lock()
BATCH_INTERVAL = 0.1  # 100 milliseconds

async def batch_broadcaster():
    while True:
        await asyncio.sleep(BATCH_INTERVAL)
        with BATCH_LOCK:
            batch = PACKET_BATCH.copy()
            PACKET_BATCH.clear()
        if batch and CONNECTED_CLIENTS:
            payload = json.dumps({"type": "packets", "data": batch})
            await asyncio.gather(*[
                client.send(payload) for client in CONNECTED_CLIENTS
            ])
```

The nfstream thread pushes scored flow dicts into `PACKET_BATCH` via a thread-safe lock. Every 100ms, the broadcaster wakes, grabs the entire batch in one lock acquisition, serializes it as a single JSON array, and sends it to all connected clients simultaneously. A capture running at 5,000 flows/second sends only **10 WebSocket messages per second** instead of 5,000 — a 500x reduction in IPC overhead.

### 8.3 Control Plane Protocol

The WebSocket connection is fully bidirectional. The frontend sends JSON control messages:

**Client → Server:**
```json
{ "type": "get_interfaces" }
{ "type": "start", "interface": "\\Device\\NPF_{GUID}", "filter": "tcp" }
{ "type": "pause" }
{ "type": "resume" }
{ "type": "stop" }
```

**Server → Client:**
```json
{ "type": "interfaces", "data": [{"name": "...", "ip": "...", "display": "..."}, ...] }
{ "type": "packets",    "data": [<PacketData>, <PacketData>, ...] }
{ "type": "stats",      "data": { "total": 1500, "tcp": 900, "udp": 400, "icmp": 200 } }
{ "type": "status",     "state": "capturing" | "paused" | "stopped" | "idle" }
{ "type": "error",      "message": "Npcap not found at System32\\Npcap\\Packet.dll" }
```

Stats messages are sent periodically (every batch cycle) to update the Stats Panel without requiring a separate polling mechanism.

### 8.4 Session Manager

`session_manager.py` maintains a live dictionary of active flow sessions keyed by the 5-tuple `(src_ip, src_port, dst_ip, dst_port, protocol)`. When nfstream emits a flow, the session manager is responsible for:
- Tracking flow start time for duration calculation.
- Maintaining running counters (bytes, packets, flag counts) incrementally as new packets arrive within the same flow.
- Expiring old sessions that have been idle beyond a configurable timeout.

---

## 9. Attack Simulation & Validation Framework

To validate the ML engine's effectiveness without requiring actual malware, NetSentinel ships an integrated attack simulation framework.

### simulate_attack.py — High-Level Orchestrator

`simulate_attack.py` is the user-facing simulation script. It accepts a target IP, target port, and attack type via CLI arguments and dispatches the appropriate low-level simulation. Supported attack vectors:

**1. UDP Flood**
Fires rapid, large-payload UDP datagrams to the target port. This drives `Flow Byts/s` and `Flow Pkts/s` to extreme values, and `Fwd Pkt Len Max` / `Fwd Pkt Len Mean` to large sizes. Most DoS attack signatures trigger this feature combination.

**2. TCP SYN Flood**
Sends TCP segments with only the SYN flag set, using randomized spoofed source IPs. The target never completes the three-way handshake. This drives `SYN Flag Cnt` to very high values while `ACK Flag Cnt` remains near zero — a strong model signal.

**3. Xmas Tree Scan**
Sends TCP segments with PSH + URG + FIN all set simultaneously (the "Christmas Tree" because all flags are lit). This is an illegal TCP state used by reconnaissance tools. `PSH Flag Cnt` + `FIN Flag Cnt` + `RST Flag Cnt` in combination trigger the model.

**4. SSH Brute Force**
Generates a high volume of short-lived TCP connections to port 22. Each connection opens, sends a small authentication attempt, and immediately closes. This pattern produces many flows with: short `Flow Duration`, small `TotLen Fwd Pkts`, high `FIN Flag Cnt`, and low `Down/Up Ratio` (server rejects quickly, sends minimal data back).

**5. TCP Port Scan**
Sweeps sequential ports on the target host. Most ports return RST (port closed) or no response (firewalled). This produces: near-zero `Down/Up Ratio`, high `RST Flag Cnt`, many very short flows, and low `Bwd Pkt Len Mean`.

### attack.py — Low-Level Primitives

`attack.py` contains the raw socket and Scapy-based implementations used by `simulate_attack.py`. All attacks are targeted at `127.0.0.1` (loopback) by default, ensuring no actual network harm occurs during testing.

---

## 10. Build & Deployment Pipeline

Shipping a hybrid application (Python + Node.js + native window + ML artifacts + kernel driver dependency) to an end user as a single double-clickable installer requires a carefully orchestrated build pipeline.

### 10.1 PowerShell Build Automation — build-installer.ps1

The `build-installer.ps1` script automates the entire pipeline end-to-end. It is designed for one-click execution:
```powershell
.\build-installer.ps1
```

The script performs three sequential phases with error checking between each phase.

### 10.2 Next.js Static Export

```powershell
cd frontend
npm install
npm run build     # Runs next build + next export
```

Next.js compiles all TypeScript/JSX source files, applies Tailwind purging (removing unused CSS classes), code-splits JavaScript bundles, and outputs pre-rendered HTML pages to `frontend/out/`. This directory contains everything needed to render the application — no runtime Node.js server required.

The build configuration in `next.config.js` sets:
```javascript
output: 'export'       // Static export mode
trailingSlash: true    // Required for file-based routing in static mode
```

### 10.3 PyInstaller Freezing

```powershell
cd backend
pyinstaller backend.spec --clean
```

PyInstaller analyzes all Python `import` statements, traces dependencies transitively, and bundles:
- The CPython interpreter runtime (Python 3.10)
- All `import`ed libraries: `nfstream`, `scapy`, `xgboost`, `sklearn`, `numpy`, `pandas`, `websockets`, `webview`, `asyncio`
- The ML artifacts from `Offline2/artifacts/` (model.pkl, scaler.pkl, explainer.pkl, feature_list.pkl)
- The Next.js static build from `frontend/out/`

The `backend.spec` file configures the bundle as a **ONEDIR** deployment: a `NetSentinel/` directory containing `NetSentinel.exe` and an `_internal/` subdirectory with all dependencies.

**Critical Runtime Path Resolution:**
When frozen, Python's `sys.executable` points to `NetSentinel.exe` rather than `python.exe`, and relative paths break. The `RiskPredictor.reload()` method implements a **multi-path candidate search** at startup:

```python
if getattr(sys, 'frozen', False):
    candidates = [
        os.path.join(sys._MEIPASS, 'Offline2', 'artifacts'),
        os.path.join(os.path.dirname(sys.executable), '_internal', 'Offline2', 'artifacts'),
        os.path.join(os.path.dirname(sys.executable), 'Offline2', 'artifacts'),
    ]
else:
    candidates = [os.path.join(repo_root, 'Offline2', 'artifacts')]
```

It checks each path and uses the first one where `model.pkl` exists. If no model is found, it gracefully falls back to a **heuristic mock predictor** that flags flows with `Flow Pkts/s > 1000` as potentially malicious — ensuring the application remains functional even if artifacts are missing.

### 10.4 PyWebView Desktop Wrapper

`main.py` launches the UI window using `pywebview`:

```python
frontend_path = _resolve_frontend_entry()
window = webview.create_window(
    "NetSentinel",
    url=frontend_path,
    width=1400,
    height=900,
    min_size=(1024, 700),
)
webview.start()
```

PyWebView embeds the **Microsoft Edge WebView2** (Chromium-based) renderer on Windows 10/11, providing a full-fidelity browser engine for the React application. The window has no browser address bar or developer toolbar visible to end users — it looks and feels like a native desktop application.

`_resolve_frontend_entry()` searches multiple candidate paths for `index.html` to handle both development (source tree) and frozen (PyInstaller bundle) deployment.

The WebSocket server starts in a background thread before `webview.start()` is called, ensuring the backend is ready before the frontend's JavaScript attempts to connect.

### 10.5 NSIS Installer

```powershell
makensis installer\netsentinel.nsi
```

NSIS (Nullsoft Scriptable Install System) packages the PyInstaller `NetSentinel/` directory into a professional installer wizard (`NetSentinel-Setup.exe`):
- **Installation directory:** `C:\Program Files\NetSentinel\` (configurable)
- **Start Menu shortcut:** Created in the Start Menu under "NetSentinel"
- **Desktop shortcut:** Created on the user's Desktop
- **Windows Registry:** Adds an entry under `HKLM\SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\NetSentinel` for Add/Remove Programs integration
- **Uninstaller:** Generates `Uninstall.exe` that cleanly removes all installed files and registry keys

The installer displays a license agreement screen and an installation progress bar.

---

## 11. Operating System Security Integrations

### 11.1 UAC Elevation Check

Capturing packets in promiscuous mode requires kernel-level socket access, which Windows restricts to Administrator accounts. Attempting to bind a raw socket as a standard user fails silently or raises an `AccessDenied` exception.

NetSentinel performs this check at the very start of `main.py`, before any backend modules are imported:

```python
import ctypes

def _is_windows_admin() -> bool:
    try:
        return bool(ctypes.windll.shell32.IsUserAnAdmin())
    except Exception:
        return False

if os.name == 'nt' and not _is_windows_admin():
    ctypes.windll.user32.MessageBoxW(
        0,
        "NetSentinel requires Administrator privileges to capture network traffic.\n\n"
        "Please right-click the application and select 'Run as administrator'.",
        "Administrator Required",
        0x10  # MB_ICONERROR
    )
    sys.exit(1)
```

This intercepts the launch before any Python background threads start, any ports are bound, or any Windows resources are acquired. The native Win32 `MessageBoxW` dialog is used (rather than a Python GUI dialog) to ensure the message is visible even before the PyWebView window opens.

### 11.2 Global Singleton Mutex

If a user double-clicks the desktop shortcut while NetSentinel is already running, the second instance would:
1. Attempt to bind `localhost:8765`.
2. Receive `[WinError 10048] Only one usage of each socket address is permitted`.
3. Crash with a traceback.

NetSentinel prevents this using a **Windows Global Kernel Mutex**:

```python
import ctypes

MUTEX_NAME = "Global\\NetSentinel_Singleton_Mutex_v1"
mutex = ctypes.windll.kernel32.CreateMutexW(None, False, MUTEX_NAME)
last_error = ctypes.windll.kernel32.GetLastError()

if last_error == 183:  # ERROR_ALREADY_EXISTS
    ctypes.windll.user32.MessageBoxW(
        0,
        "NetSentinel is already running.\nCheck the taskbar or system tray.",
        "Already Running",
        0x40  # MB_ICONINFORMATION
    )
    sys.exit(0)
```

`CreateMutexW` with a `Global\` prefix creates a kernel object visible across all user sessions on the machine. If `GetLastError()` returns `ERROR_ALREADY_EXISTS` (183), another instance holds the mutex — the second instance shows an "Already Running" message and exits cleanly. The first instance's mutex handle is released automatically by the kernel when the process exits.

### 11.3 Logging Infrastructure

NetSentinel maintains dual logging (console + file):

```
logs/
├── netsentinel.log     # Main application log (backend/main.py events)
└── ml_predictor.log    # ML engine log (RiskPredictor events)
```

In frozen mode, the log directory is created adjacent to `NetSentinel.exe`. In development mode, logs appear in the repository root. The `_configure_logging()` function handles both cases:

```python
base_dir = os.path.dirname(sys.executable) if getattr(sys, "frozen", False) else REPO_ROOT
log_dir = os.path.join(base_dir, "logs")
os.makedirs(log_dir, exist_ok=True)
```

The `RiskPredictor` additionally writes to both `ml_predictor.log` and the main `netsentinel.log` (via `_append_main_log()`) to create a single unified audit trail of model loading, artifact path resolution, and prediction events.

Log format: `YYYY-MM-DD HH:MM:SS,mmm [LEVEL] Logger.Name - Message`

---

## 12. Conclusion & Future Roadmap

### Summary

NetSentinel demonstrates that machine learning-augmented network analysis can be made practical, real-time, and deployable on consumer hardware. The architectural decisions at each layer were driven by concrete engineering constraints:

- **Hybrid nfstream + Scapy capture** resolves the GIL throughput ceiling while preserving Layer 2 visibility.
- **100ms batch broadcasting** reduces WebSocket overhead by 500x without perceptible latency to the user.
- **DOM virtualization** with react-window ensures the UI remains at 60fps even after hours of continuous capture.
- **Chronological train/test split** ensures the ML model is evaluated against genuinely unseen attack families, providing a realistic measure of generalization.
- **0.85 probability threshold** reduces the false positive rate to 0.30% — making every malicious alert highly actionable.
- **PyInstaller + NSIS packaging** delivers a zero-dependency end-user installer.

The result is a platform where a security analyst can install, launch, and immediately see live traffic with ML risk scores — without configuring Python environments, installing dependencies, or writing configuration files.

### Future Roadmap

**1. Offline PCAP Analysis**
Enable ingestion of historical `.pcap` or `.pcapng` files through a file picker dialog. The existing nfstream engine already supports file-based capture (`source=filepath`). This would allow retrospective ML analysis of forensic traffic captures.

**2. GPU Inference Acceleration**
The current XGBoost inference runs on CPU. For extremely high-throughput environments (100+ Gbps links), migrating to RAPIDS cuML XGBoost would leverage GPU parallelism, pushing inference capacity from ~50,000 flows/sec to >500,000 flows/sec.

**3. Cross-Platform Support**
The Windows-specific components (Npcap check, UAC elevation via `ctypes.windll`, Win32 MessageBox) can be conditionally wrapped. The underlying stack (nfstream, Scapy, Python, Next.js) is cross-platform. Supporting `libpcap` on Linux would enable deployment on Raspberry Pi-based network sensors.

**4. Active Threat Blocking**
Extending the platform with an optional "block on detection" mode: when a flow breaches the 85% malicious threshold, the backend could invoke the Windows Firewall API (`netsh advfirewall firewall add rule`) to add a block rule for the source IP. This would be strictly opt-in and require an additional user confirmation dialog.

**5. SHAP Visualization in UI**
Exposing the `explainer.pkl` SHAP TreeExplainer through the flow detail panel: for any selected malicious flow, display a bar chart of the top 5 contributing features and their SHAP values, giving analysts immediate insight into *why* the model flagged the traffic.

**6. Historical Dashboard**
Persisting flow records to a local SQLite database and providing a historical analytics dashboard — time-series charts of malicious flow rates, top flagged source IPs over time, and protocol distribution trends.

---

*End of Report. NetSentinel v1.0 — May 2026*

