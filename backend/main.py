"""
WebSocket server for real-time packet streaming.
Entry point for the backend.

Usage (run as Administrator on Windows):
    python main.py [--host 0.0.0.0] [--port 8765]

Protocol:
  Client → Server messages (JSON):
    { "type": "start",   "interface": "<iface_name>" }
    { "type": "pause"  }
    { "type": "resume" }
    { "type": "stop"   }
    { "type": "get_interfaces" }

  Server → Client messages (JSON):
    { "type": "interfaces", "data": [{"name": "..", "ip": "..", "display": ".."}, ...] }
    { "type": "packets",    "data": [<PacketData>, ...] }
    { "type": "stats",      "data": { "total": N, "tcp": N, "udp": N, "icmp": N } }
    { "type": "status",     "state": "capturing" | "paused" | "stopped" | "idle" }
    { "type": "error",      "message": "..." }
"""

import asyncio
import json
import logging
import threading
import time
import argparse
import sys
import os
from collections import defaultdict, deque
from typing import Set, Dict, Any, List

import webview
import websockets
from websockets.server import WebSocketServerProtocol

from capture import PacketCaptureEngine
from interfaces import get_interfaces, get_default_interface
from session_manager import SessionManager

# ─── Logging ────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
)
logger = logging.getLogger("PacketCapture.Server")

# ─── Global State ───────────────────────────────────────────────────────────
CONNECTED_CLIENTS: Set[WebSocketServerProtocol] = set()
CLIENTS_LOCK = threading.Lock()

# Batch buffer — packets are accumulated and flushed every BATCH_INTERVAL seconds
PACKET_BATCH: List[Dict] = []
BATCH_LOCK = threading.Lock()
BATCH_INTERVAL = 0.1  # 100 ms

# Stats counters
stats: Dict[str, int] = {"total": 0, "tcp": 0, "udp": 0, "icmp": 0}
stats_lock = threading.Lock()

# Packet ID counter
packet_id_counter = 0
id_lock = threading.Lock()

# Session tracking
session_manager = SessionManager()


def _next_id() -> int:
    global packet_id_counter
    with id_lock:
        packet_id_counter += 1
        return packet_id_counter


def on_packet_captured(parsed: Dict) -> None:
    """Called from capture thread — update stats and enqueue for batch send."""
    global stats, PACKET_BATCH

    proto = parsed.get("protocol", "OTHER")

    with stats_lock:
        stats["total"] += 1
        if proto == "TCP":
            stats["tcp"] += 1
        elif proto == "UDP":
            stats["udp"] += 1
        elif proto == "ICMP":
            stats["icmp"] += 1

    parsed["id"] = _next_id()

    # Pass to session manager
    session_manager.process_packet(parsed)

    with BATCH_LOCK:
        PACKET_BATCH.append(parsed)


# ─── Async Batch Broadcaster ─────────────────────────────────────────────────

async def batch_broadcaster(loop: asyncio.AbstractEventLoop) -> None:
    """Periodically flush packet batch to all connected clients."""
    while True:
        await asyncio.sleep(BATCH_INTERVAL)
        with BATCH_LOCK:
            if not PACKET_BATCH:
                continue
            batch = PACKET_BATCH.copy()
            PACKET_BATCH.clear()

        if not batch:
            continue

        message = json.dumps({"type": "packets", "data": batch})
        await broadcast(message)


async def stats_broadcaster() -> None:
    """Every second, send current stats to all clients."""
    while True:
        await asyncio.sleep(1.0)
        with stats_lock:
            current_stats = dict(stats)
        msg = json.dumps({"type": "stats", "data": current_stats})
        await broadcast(msg)


async def session_broadcaster() -> None:
    """Every second, send batch of added/updated and closed sessions to all clients."""
    while True:
        await asyncio.sleep(1.0)
        updates = session_manager.get_batch_updates()
        if updates["updated"] or updates["closed"]:
            msg = json.dumps({"type": "sessions", "data": updates})
            await broadcast(msg)


async def broadcast(message: str) -> None:
    """Send a message to all connected WebSocket clients."""
    with CLIENTS_LOCK:
        clients = set(CONNECTED_CLIENTS)
    if not clients:
        return
    # Use gather to send concurrently; ignore individual client failures
    results = await asyncio.gather(
        *[_safe_send(client, message) for client in clients],
        return_exceptions=True,
    )


async def _safe_send(ws: WebSocketServerProtocol, message: str) -> None:
    """Send to a single client, removing it if connection is closed."""
    try:
        await ws.send(message)
    except (websockets.exceptions.ConnectionClosed, Exception):
        with CLIENTS_LOCK:
            CONNECTED_CLIENTS.discard(ws)


# ─── Capture Engine (singleton) ──────────────────────────────────────────────

engine = PacketCaptureEngine(on_packet_captured)


async def send_status(ws: WebSocketServerProtocol, state: str) -> None:
    await _safe_send(ws, json.dumps({"type": "status", "state": state}))


async def send_error(ws: WebSocketServerProtocol, message: str) -> None:
    await _safe_send(ws, json.dumps({"type": "error", "message": message}))


# ─── Connection Handler ───────────────────────────────────────────────────────

async def handler(ws: WebSocketServerProtocol) -> None:
    """Handle a single WebSocket connection."""
    addr = ws.remote_address
    logger.info(f"Client connected: {addr}")

    with CLIENTS_LOCK:
        CONNECTED_CLIENTS.add(ws)

    # Send interface list immediately on connection
    try:
        interfaces = get_interfaces()
        default_iface = get_default_interface()
        await ws.send(json.dumps({
            "type": "interfaces",
            "data": interfaces,
            "default": default_iface,
        }))
    except Exception as e:
        logger.warning(f"Failed to send interfaces: {e}")

    try:
        async for raw_msg in ws:
            try:
                msg = json.loads(raw_msg)
            except json.JSONDecodeError:
                await send_error(ws, "Invalid JSON message")
                continue

            msg_type = msg.get("type", "")
            logger.info(f"[{addr}] Received: {msg_type}")

            if msg_type == "start":
                interface = msg.get("interface", "")
                bpf_filter = msg.get("filter", "")  # Get optional BPF filter
                if not interface:
                    # use default
                    interface = get_default_interface()
                if engine.is_running:
                    engine.stop()
                    await asyncio.sleep(0.2)
                # Reset stats and ID counter
                with stats_lock:
                    for k in stats:
                        stats[k] = 0
                global packet_id_counter
                packet_id_counter = 0
                session_manager.clear()
                engine.start(interface, bpf_filter=bpf_filter)
                await broadcast(json.dumps({"type": "status", "state": "capturing"}))

            elif msg_type == "pause":
                engine.pause()
                await broadcast(json.dumps({"type": "status", "state": "paused"}))

            elif msg_type == "resume":
                engine.resume()
                await broadcast(json.dumps({"type": "status", "state": "capturing"}))

            elif msg_type == "stop":
                engine.stop()
                await broadcast(json.dumps({"type": "status", "state": "stopped"}))

            elif msg_type == "get_interfaces":
                interfaces = get_interfaces()
                default_iface = get_default_interface()
                await ws.send(json.dumps({
                    "type": "interfaces",
                    "data": interfaces,
                    "default": default_iface,
                }))

            else:
                await send_error(ws, f"Unknown message type: {msg_type!r}")

    except websockets.exceptions.ConnectionClosedOK:
        logger.info(f"Client disconnected cleanly: {addr}")
    except websockets.exceptions.ConnectionClosedError as e:
        logger.warning(f"Client connection error {addr}: {e}")
    except Exception as e:
        logger.error(f"Unexpected error handling {addr}: {e}")
    finally:
        with CLIENTS_LOCK:
            CONNECTED_CLIENTS.discard(ws)
        logger.info(f"Client removed: {addr}")


# ─── Entry Point ─────────────────────────────────────────────────────────────

async def main(host: str, port: int) -> None:
    loop = asyncio.get_running_loop()

    logger.info(f"Starting WebSocket server on ws://{host}:{port}")
    logger.info("Press Ctrl+C to stop.")

    async with websockets.serve(
        handler,
        host,
        port,
        ping_interval=20,
        ping_timeout=10,
        max_size=2 ** 20,  # 1 MB max message
    ):
        # Start background broadcast tasks
        await asyncio.gather(
            batch_broadcaster(loop),
            stats_broadcaster(),
            session_broadcaster(),
            asyncio.Future(),  # Run forever
        )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Packet Capture WebSocket Server")
    parser.add_argument("--host", default="localhost", help="Bind host (default: localhost)")
    parser.add_argument("--port", type=int, default=8765, help="Bind port (default: 8765)")
    parser.add_argument("--dev", action="store_true", help="Run in dev mode (localhost:3000)")
    args = parser.parse_args()

    def run_ws():
        # Setup new event loop for this background thread
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(main(args.host, args.port))
        except Exception as e:
            logger.error(f"WS error: {e}")

    ws_thread = threading.Thread(target=run_ws, daemon=True)
    ws_thread.start()

    # --- Launch ML Engine ---
    ml_process = None
    if not args.dev:
        # In production, look for the bundled ml_engine.exe next to our backend.exe
        if getattr(sys, 'frozen', False):
            base_dir = os.path.dirname(sys.executable)
        else:
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            
        ml_exe = os.path.join(base_dir, "ml_risk_engine", "dist", "ml_engine", "ml_engine.exe")
        
        # NSIS puts everything in $INSTDIR, so ml_engine.exe is also at root often, lets check both
        root_ml_exe = os.path.join(base_dir, "ml_engine", "ml_engine.exe")
        direct_ml_exe = os.path.join(base_dir, "ml_engine.exe")

        ml_path = None
        for p in [ml_exe, root_ml_exe, direct_ml_exe]:
            if os.path.exists(p):
                ml_path = p
                break
                
        if ml_path:
            logger.info(f"Starting ML Engine: {ml_path}")
            import subprocess
            try:
                # We spawn it and don't block. We kill it at exit.
                # Do not use DEVNULL for stdout/stderr as it can crash frozen uvicorn on Windows
                creationflags = 0x08000000 if sys.platform == "win32" else 0 # CREATE_NO_WINDOW
                ml_process = subprocess.Popen([ml_path], creationflags=creationflags)
            except Exception as e:
                logger.error(f"Failed to start ML engine: {e}")
        else:
            logger.warning("ML Engine executable not found. Security dashboard will show offline.")

    # Give WS server a moment to bind
    time.sleep(0.5)

    if args.dev:
        url = "http://localhost:3000"
    else:
        # In production, look for the Next.js static exported 'out' directory
        if getattr(sys, 'frozen', False):
            base_dir = os.path.dirname(sys.executable)
        else:
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            
        out_dir = os.path.join(base_dir, "frontend", "out")
        if os.path.exists(out_dir):
            url = os.path.join(out_dir, "index.html")
        else:
            url = os.path.join(base_dir, "out", "index.html") # PyInstaller relative directory search

    window = webview.create_window("Packet Capture Engine", url, width=1280, height=800)
    
    try:
        webview.start()
    except KeyboardInterrupt:
        logger.info("Server stopped by user.")
    finally:
        if ml_process:
            ml_process.terminate()
            ml_process.wait()
        if engine.is_running:
            engine.stop()
