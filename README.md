<div align="center">
  <img src="frontend/public/icon.png" width="128" height="128" alt="PacketCapture Logo" />
  <h1>PacketCapture</h1>
  <p>A high-performance, real-time network packet analyzer with a Wireshark-inspired interface, built on a modern hybrid stack.</p>
</div>

---

## ⚡ Features

- **Real-Time Capture:** Live packet streaming from network interfaces using WebSockets.
- **Deep Packet Inspection:** Scapy-powered backend parses layers (Ethernet, IPv4/IPv6, TCP, UDP, ICMP, DNS, Raw Payloads).
- **Wireshark-style Interface:** Dark-themed, high-density React UI with a fully virtualized packet table capable of handling thousands of rows without lag.
- **Hex Dump Viewer:** Inspect the raw hexadecimal bytes and ASCII payloads of any selected packet.
- **Dual Filtering System:**
  - **BPF Capture Filter:** High-performance adapter-level filtering (e.g., `tcp port 80`) to drop irrelevant packets before processing.
  - **Display Filter/Find:** Instant UI-level search (e.g., `192.168.1.1` or `HTTP`) without stopping the live capture.
- **Session Management:** Save captured traffic to standard `.pcap` files and load existing `.pcap` files for offline analysis.
- **Zero-UAC Desktop Launch (Windows):** The final installer utilizes a Windows Task Scheduler trick (identical to Wireshark) to launch the app elevated automatically—no annoying UAC prompts on every launch!

---

## 🏗️ Architecture

PacketCapture is structured as a monorepo containing three main components:

1. **Frontend (`/frontend`)**
   - Built with **Next.js (React)**, **TypeScript**, and **Tailwind CSS**.
   - Uses **Zustand** for high-performance state management and `react-window` for list virtualization.
   - Exported as a purely static HTML/JS/CSS site (`next build && next export`).

2. **Backend (`/backend`)**
   - Built with **Python** and **Scapy**.
   - Handles the raw socket capture loop in a dedicated background thread.
   - Parses packets and streams them via `websockets` (asyncio) to the frontend.

3. **Desktop Wrapper (`/electron`)**
   - Built with **Electron** and **electron-builder**.
   - Hosts the static Next.js frontend in a Chromium window and manages the lifecycle of the hidden Python backend executable.

---

## 🚀 Getting Started (Development)

Want to run the app locally from source? Follow these steps:

### Prerequisites (Windows)
1. **Node.js** (v18+)
2. **Python** (3.10+)
3. [**Npcap**](https://npcap.com/) — **Required!** Install Npcap in "WinPcap API-compatible Mode" to enable raw socket packet capturing on Windows.

### 1. Setup Backend
The backend uses Python to sniff packets.
```bash
cd backend
python -m venv venv
venv\Scripts\activate       # Activate virtual environment
pip install -r requirements.txt
```

### 2. Setup Frontend
The frontend is a standard Next.js application.
```bash
cd frontend
npm install
```

### 3. Run Locally
You must run the Python backend as an **Administrator**, or Scapy will fail to attach to network adapters.

**Terminal 1 (Admin):**
```bash
cd backend
venv\Scripts\activate
python main.py
```

**Terminal 2:**
```bash
cd frontend
npm run dev
```
Open your browser to `http://localhost:3000` to see the live app!

---

## 📦 Building the Executable Installer

If you want to package the app into a shareable `.exe` Windows Installer, the project uses a custom build pipeline combining `PyInstaller`, `Next.js Export`, and `NSIS`.

1. **Build the Frontend (Static Export):**
   ```bash
   cd frontend
   npm run build
   ```

2. **Compile the Python Backend:**
   ```bash
   cd backend
   venv\Scripts\activate
   pyinstaller backend.spec --distpath dist --workpath build --noconfirm
   ```

3. **Package Electron & Compile NSIS Installer:**
   ```bash
   # From the project root
   npm run dist
   ```
   *Note: Our custom `installer.nsi` script requires the `makensis` executable (usually cached by electron-builder in `%LOCALAPPDATA%\electron-builder\Cache\nsis\...\makensis.exe`).*

The final portable installer will be located at `dist/PacketCapture-Setup-1.0.0.exe`.

---

## 🛑 Git & Cache Files

If you are cloning this repository, note that we have a single, consolidated `.gitignore` in the root directory designed to keep the repo clean of:
- **Build Artifacts:** `dist/` installer binaries, `backend/build/`, `frontend/out/`, and `frontend/.next/`.
- **Dependencies:** `node_modules/` and Python `venv/` or `__pycache__/`.
- **User Data:** Environment files (`.env`) and any downloaded or recorded packet captures (`.pcap`, `.pcapng`).

## License

This project is licensed under the MIT License.
