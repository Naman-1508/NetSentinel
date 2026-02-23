"""
Packet capture engine using Scapy's AsyncSniffer.
Provides thread-safe start/stop/pause/resume functionality.
"""
import threading
import queue
import logging
import time
from typing import Optional, Callable

logger = logging.getLogger(__name__)

# How many packets to buffer before dropping (backpressure)
MAX_QUEUE_SIZE = 10000


class PacketCaptureEngine:
    """
    Thread-safe packet capture engine.
    Uses Scapy's sniff() in a dedicated background thread.
    """

    def __init__(self, packet_callback: Callable):
        """
        Args:
            packet_callback: Called with each parsed packet dict.
        """
        self._callback = packet_callback
        self._sniffer_thread: Optional[threading.Thread] = None
        self._running = threading.Event()
        self._paused = threading.Event()
        self._stop_flag = threading.Event()
        self._interface: str = ""
        self._lock = threading.Lock()

    @property
    def is_running(self) -> bool:
        return self._running.is_set()

    @property
    def is_paused(self) -> bool:
        return self._paused.is_set()

    def start(self, interface: str, bpf_filter: str = "") -> None:
        """Start capturing on the given interface."""
        with self._lock:
            if self._running.is_set():
                logger.warning("Capture already running; stop first.")
                return

            self._interface = interface
            self._bpf_filter = bpf_filter  # New: store BPF filter
            self._stop_flag.clear()
            self._paused.clear()
            self._running.set()

            self._sniffer_thread = threading.Thread(
                target=self._sniff_loop,
                name="PacketSnifferThread",
                daemon=True
            )
            self._sniffer_thread.start()
            logger.info(f"Capture started on interface: {interface!r} with filter: {bpf_filter!r}")

    def stop(self) -> None:
        """Stop capturing."""
        with self._lock:
            if not self._running.is_set():
                return
            self._stop_flag.set()
            self._paused.clear()
            self._running.clear()
            logger.info("Capture stop requested.")

    def pause(self) -> None:
        """Pause packet processing (sniffer keeps running, packets are dropped)."""
        if self._running.is_set():
            self._paused.set()
            logger.info("Capture paused.")

    def resume(self) -> None:
        """Resume packet processing."""
        if self._running.is_set():
            self._paused.clear()
            logger.info("Capture resumed.")

    def _sniff_loop(self) -> None:
        """Internal: run Scapy sniffer in a loop until stop is requested."""
        from scapy.all import sniff
        from parser import parse_packet

        logger.info(f"Sniffer thread started on {self._interface!r}")

        def _process(pkt):
            """Called by Scapy for each captured packet."""
            if self._stop_flag.is_set():
                return
            if self._paused.is_set():
                return  # Drop packet while paused
            try:
                parsed = parse_packet(pkt)
                if parsed:
                    self._callback(parsed)
            except Exception as e:
                logger.debug(f"Packet processing error: {e}")

        def _stop_filter(_pkt):
            return self._stop_flag.is_set()

        try:
            sniff(
                iface=self._interface if self._interface else None,
                filter=self._bpf_filter if getattr(self, '_bpf_filter', "") else None,
                prn=_process,
                stop_filter=_stop_filter,
                store=False,  # Never store packets in memory
            )
        except Exception as e:
            logger.error(f"Sniffer error: {e}")
        finally:
            self._running.clear()
            logger.info("Sniffer thread terminated.")
