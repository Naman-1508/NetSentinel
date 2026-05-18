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
import multiprocessing
from collections import defaultdict, deque
from typing import Set, Dict, Any, List

import webview
import websockets
from websockets import WebSocketServerProtocol

from capture import PacketCaptureEngine
from interfaces import get_interfaces, get_default_interface, resolve_capture_interface
from session_manager import SessionManager


REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ML_ROOT = os.path.join(REPO_ROOT, "ml_risk_engine")

if getattr(sys, 'frozen', False):
    # Frozen single-exe: _MEIPASS contains all bundled modules.
    # We must add _MEIPASS to sys.path so 'import api.server', 'import realtime_monitor' etc. work.
    _meipass = getattr(sys, '_MEIPASS', os.path.dirname(sys.executable))
    if _meipass not in sys.path:
        sys.path.insert(0, _meipass)
else:
    if REPO_ROOT not in sys.path:
        sys.path.insert(0, REPO_ROOT)
    if ML_ROOT not in sys.path:
        sys.path.insert(0, ML_ROOT)


def _resolve_frontend_entry() -> str:
    """Return the absolute path to the bundled frontend index.html."""
    if getattr(sys, 'frozen', False):
        base_candidates = [
            getattr(sys, '_MEIPASS', os.path.dirname(sys.executable)),
            os.path.dirname(sys.executable),
        ]
    else:
        base_candidates = [REPO_ROOT]

    rel_candidates = [
        os.path.join('frontend', 'out', 'index.html'),
        os.path.join('out', 'index.html'),
        'index.html',
    ]

    for base_dir in base_candidates:
        for rel_path in rel_candidates:
            candidate = os.path.join(base_dir, rel_path)
            if os.path.exists(candidate):
                return candidate

    checked_paths = [os.path.join(base, rel) for base in base_candidates for rel in rel_candidates]
    raise FileNotFoundError(
        "Frontend bundle not found. Checked: " + ", ".join(checked_paths)
    )

# ─── Logging ───────────────────────────────────────────────────────────────-
def _configure_logging() -> None:
    """Configure console + file logging; when frozen, write logs next to the EXE."""
    level = logging.INFO
    fmt = "%(asctime)s [%(levelname)s] %(name)s - %(message)s"
    handlers = [logging.StreamHandler()]

    try:
        base_dir = os.path.dirname(sys.executable) if getattr(sys, "frozen", False) else REPO_ROOT
        log_dir = os.path.join(base_dir, "logs")
        os.makedirs(log_dir, exist_ok=True)
        log_file = os.path.join(log_dir, "netsentinel.log")
        fh = logging.FileHandler(log_file, encoding="utf-8")
        handlers.append(fh)
    except Exception:
        # If file logging fails, continue with console only
        pass

    logging.basicConfig(level=level, format=fmt, handlers=handlers)


_configure_logging()
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

ml_server_thread = None
WS_LOOP = None


def _start_ml_engine() -> None:
    """Run the ML FastAPI app inside this process as a background service."""
    global ml_server_thread

    if ml_server_thread and ml_server_thread.is_alive():
        return

    def run_ml_server() -> None:
        try:
            import uvicorn
            from api.server import app

            config = uvicorn.Config(
                app,
                host="127.0.0.1",
                port=8000,
                log_level="info",
                access_log=False,
            )
            server = uvicorn.Server(config)
            server.run()
        except Exception as exc:
            logger.error(f"Failed to start ML engine: {exc}")

    ml_server_thread = threading.Thread(target=run_ml_server, daemon=True)
    ml_server_thread.start()
    logger.info("ML engine started inside the NetSentinel backend process.")


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
        count = parsed.get("packet_count", 1)
        stats["total"] += count
        if proto == "TCP":
            stats["tcp"] += count
        elif proto == "UDP":
            stats["udp"] += count
        elif proto == "ICMP":
            stats["icmp"] += count

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

        try:
            logger.info("Broadcasting %d packets to %d clients", len(batch), len(CONNECTED_CLIENTS))
        except Exception:
            logger.exception("Failed to log batch broadcast info")

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

def on_capture_error(message: str) -> None:
    """Send capture failures to all clients so UI does not fail silently."""
    logger.error(f"Capture engine error: {message}")

    if WS_LOOP is None:
        return

    try:
        asyncio.run_coroutine_threadsafe(
            broadcast(json.dumps({"type": "error", "message": f"Capture failed: {message}"})),
            WS_LOOP,
        )
        asyncio.run_coroutine_threadsafe(
            broadcast(json.dumps({"type": "status", "state": "stopped"})),
            WS_LOOP,
        )
    except Exception as exc:
        logger.error(f"Failed to forward capture error to UI: {exc}")


engine = PacketCaptureEngine(on_packet_captured, error_callback=on_capture_error)


async def send_status(ws: WebSocketServerProtocol, state: str) -> None:
    await _safe_send(ws, json.dumps({"type": "status", "state": state}))


async def send_error(ws: WebSocketServerProtocol, message: str) -> None:
    await _safe_send(ws, json.dumps({"type": "error", "message": message}))


# ─── Connection Handler ───────────────────────────────────────────────────────

async def handler(ws: WebSocketServerProtocol) -> None:
    """Handle a single WebSocket connection."""
    global packet_id_counter
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
                interface = resolve_capture_interface(interface)
                if engine.is_running:
                    engine.stop()
                    await asyncio.sleep(0.2)
                # Reset stats and ID counter
                with stats_lock:
                    for k in stats:
                        stats[k] = 0
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
    global WS_LOOP
    loop = asyncio.get_running_loop()
    WS_LOOP = loop

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
    multiprocessing.freeze_support()

    parser = argparse.ArgumentParser(description="Packet Capture WebSocket Server")
    parser.add_argument("--host", default="localhost", help="Bind host (default: localhost)")
    parser.add_argument("--port", type=int, default=8765, help="Bind port (default: 8765)")
    parser.add_argument("--dev", action="store_true", help="Run in dev mode (localhost:3000)")
    args = parser.parse_args()

    # --- Single-instance on Windows (prevent multiple launches) ---
    def _ensure_single_instance() -> None:
        if not getattr(sys, 'frozen', False) or os.name != 'nt':
            return
        try:
            import ctypes
            kernel32 = ctypes.WinDLL('kernel32', use_last_error=True)
            mutex_name = 'Global\\NetSentinel_Singleton_Mutex_v1'
            handle = kernel32.CreateMutexW(None, ctypes.c_bool(False), mutex_name)
            if not handle:
                return
            ERROR_ALREADY_EXISTS = 183
            if ctypes.get_last_error() == ERROR_ALREADY_EXISTS:
                # If another instance is running, notify and exit
                try:
                    ctypes.windll.user32.MessageBoxW(0, 'NetSentinel is already running.', 'NetSentinel', 0x40)
                except Exception:
                    pass
                sys.exit(0)
        except Exception:
            # If single-instance enforcement fails, continue silently
            return

    _ensure_single_instance()

    # --- Require Administrator for live capture when running as EXE ---
    def _require_admin_or_exit() -> None:
        if os.name != 'nt' or not getattr(sys, 'frozen', False):
            return
        try:
            import ctypes
            if not ctypes.windll.shell32.IsUserAnAdmin():
                msg = (
                    "NetSentinel requires Administrator privileges to capture live network traffic.\n"
                    "Please run the program as Administrator (right-click → Run as administrator)."
                )
                try:
                    ctypes.windll.user32.MessageBoxW(0, msg, 'NetSentinel', 0x30)
                except Exception:
                    pass
                sys.exit(1)
        except Exception:
            return

    _require_admin_or_exit()

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

    # --- Launch ML Engine in-process ---
    _start_ml_engine()

    # Give WS server a moment to bind
    time.sleep(0.5)

    if args.dev:
        url = "http://localhost:3000"
    else:
        try:
            url = _resolve_frontend_entry()
        except FileNotFoundError as exc:
            logger.error(str(exc))
            raise

    window = webview.create_window("NetSentinel", url, width=1280, height=800)
    
    try:
        webview.start()
    except KeyboardInterrupt:
        logger.info("Server stopped by user.")
    finally:
        if engine.is_running:
            engine.stop()
