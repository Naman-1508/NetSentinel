"""
Packet/Flow capture engine - Hybrid approach:
- nfstream for Layer 3+ (IP flows, TCP, UDP, ICMP)
- Scapy for Layer 2 (MAC addresses, ARP detection)

Provides thread-safe start/stop/pause/resume functionality.
"""
import threading
import logging
import os
import ctypes
import traceback
import time
from typing import Optional, Callable, Dict
from nfstream import NFStreamer

try:
    from scapy.all import sniff, ARP, Ether, IP
    HAS_SCAPY = True
except ImportError:
    HAS_SCAPY = False

logger = logging.getLogger(__name__)


def _is_windows_admin() -> bool:
    if os.name != "nt":
        return True
    try:
        return bool(ctypes.windll.shell32.IsUserAnAdmin())
    except Exception:
        return False


def _has_npcap() -> bool:
    if os.name != "nt":
        return True
    return os.path.exists(r"C:\Windows\System32\Npcap\Packet.dll")


class PacketCaptureEngine:
    """
    Thread-safe packet capture engine using hybrid approach:
    - nfstream for Layer 3+ (IP flows)
    - Scapy for Layer 2 (MAC addresses, ARP)
    """

    def __init__(self, packet_callback: Callable, error_callback: Optional[Callable[[str], None]] = None):
        """
        Args:
            packet_callback: Called with each parsed packet/flow dict.
        """
        self._callback = packet_callback
        self._sniffer_thread: Optional[threading.Thread] = None
        self._scapy_thread: Optional[threading.Thread] = None
        self._error_callback = error_callback
        self._running = threading.Event()
        self._paused = threading.Event()
        self._stop_flag = threading.Event()
        self._interface: str = ""
        self._bpf_filter: str = ""
        self._lock = threading.Lock()
        
        # MAC cache: (src_ip, dst_ip) -> (src_mac, dst_mac)
        self._mac_cache: Dict[tuple, tuple] = {}

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
            self._bpf_filter = bpf_filter
            self._stop_flag.clear()
            self._paused.clear()
            self._running.set()

            # Start nfstream thread for Layer 3+
            self._sniffer_thread = threading.Thread(
                target=self._sniff_loop_nfstream,
                name="NFStreamThread",
                daemon=True
            )
            self._sniffer_thread.start()

            # Start Scapy thread for Layer 2 (MAC capture)
            if HAS_SCAPY:
                self._scapy_thread = threading.Thread(
                    target=self._sniff_loop_scapy_layer2,
                    name="ScapyLayer2Thread",
                    daemon=True
                )
                self._scapy_thread.start()
                logger.info(f"Scapy Layer 2 sniffer started for MAC address capture")

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
        """Pause packet processing."""
        if self._running.is_set():
            self._paused.set()
            logger.info("Capture paused.")

    def resume(self) -> None:
        """Resume packet processing."""
        if self._running.is_set():
            self._paused.clear()
            logger.info("Capture resumed.")

    def _sniff_loop_scapy_layer2(self) -> None:
        """Scapy sniffer for Layer 2 MAC address capture only."""
        logger.info(f"Scapy Layer 2 sniffer started on {self._interface!r}")
        try:
            def packet_handler(pkt):
                if self._stop_flag.is_set():
                    return False
                if self._paused.is_set():
                    return True
                
                try:
                    # Capture MAC addresses from Ethernet layer
                    if Ether in pkt:
                        eth = pkt[Ether]
                        
                        # Extract IPs if available
                        if IP in pkt:
                            ip = pkt[IP]
                            src_ip = ip.src
                            dst_ip = ip.dst
                            key = (src_ip, dst_ip)
                            
                            # Cache MACs for this flow
                            self._mac_cache[key] = (eth.src, eth.dst)
                        
                        # Log ARP packets separately
                        if ARP in pkt:
                            arp = pkt[ARP]
                            logger.warning(f"ARP packet detected: {arp.psrc} ({eth.src}) -> {arp.pdst}")
                    
                except Exception as e:
                    logger.debug(f"Error in Layer 2 capture: {e}")
                
                return True

            sniff(
                iface=self._interface,
                prn=packet_handler,
                filter=self._bpf_filter if getattr(self, '_bpf_filter', "") else None,
                store=False,
                stopperTimeout=1
            )
        except Exception as e:
            logger.warning(f"Scapy Layer 2 sniffer error: {e}")
        finally:
            logger.info("Scapy Layer 2 sniffer terminated.")

    def _sniff_loop_nfstream(self) -> None:
        """Internal: run nfstream streamer for Layer 3+ flows."""
        logger.info(f"NFStream sniffer thread started on {self._interface!r}")

        try:
            if os.name == "nt" and not _has_npcap():
                raise RuntimeError(
                    "Npcap is not installed. Install Npcap (WinPcap API-compatible mode), then restart NetSentinel."
                )

            # Allow loopback capture for non-admin development/testing.
            if os.name == "nt" and not _is_windows_admin():
                iface_lower = str(self._interface).lower() if getattr(self, '_interface', None) else ''
                if not (iface_lower.startswith('\\device\\npf_loopback') or 'loopback' in iface_lower):
                    raise PermissionError(
                        "Administrator privileges are required for live capture on Windows. "
                        "Right-click NetSentinel.exe and choose 'Run as administrator'."
                    )

            streamer = None
            last_error = None
            # Some Windows Wi-Fi adapters reject promiscuous mode; retry without it.
            for promisc in (True, False):
                try:
                    streamer = NFStreamer(
                        source=self._interface,
                        bpf_filter=self._bpf_filter if getattr(self, '_bpf_filter', "") else None,
                        promiscuous_mode=promisc,
                        snapshot_length=1536,
                        idle_timeout=5,
                        active_timeout=15,
                        accounting_mode=3,
                        statistical_analysis=True
                    )
                    logger.info(f"NFStreamer initialized on {self._interface!r} (promiscuous_mode={promisc})")
                    break
                except Exception as init_exc:
                    last_error = init_exc
                    logger.warning(f"NFStreamer init failed (promiscuous_mode={promisc}): {init_exc}")

            if streamer is None:
                raise RuntimeError(f"Failed to initialize capture on {self._interface!r}: {last_error}")
            
            for flow in streamer:
                if self._stop_flag.is_set():
                    break
                if self._paused.is_set():
                    continue

                proto_map = {6: "TCP", 17: "UDP", 1: "ICMP"}
                # Robust attribute extraction to support multiple nfstream versions
                def _get_attr(obj, *names, default=None):
                    for n in names:
                        if not isinstance(n, str):
                            continue
                        v = getattr(obj, n, None)
                        if v is not None:
                            return v
                    return default

                try:
                    protocol = proto_map.get(_get_attr(flow, 'protocol', 'proto'), "OTHER")

                    flags_val = _get_attr(
                        flow,
                        'bidirectional_tcp_flags',
                        'bidirectional_flags',
                        'tcp_flags',
                        'flags',
                        0,
                    )

                    active_flags = []
                    # If flags_val is an int bitmask
                    if isinstance(flags_val, int):
                        if flags_val & 1: active_flags.append("FIN")
                        if flags_val & 2: active_flags.append("SYN")
                        if flags_val & 4: active_flags.append("RST")
                        if flags_val & 8: active_flags.append("PSH")
                        if flags_val & 16: active_flags.append("ACK")
                        if flags_val & 32: active_flags.append("URG")
                    else:
                        # Try to interpret textual flags (e.g. 'S' or 'SYN,ACK')
                        s = str(flags_val).upper()
                        if 'FIN' in s or 'F' in s: active_flags.append('FIN')
                        if 'SYN' in s or 'S' in s: active_flags.append('SYN')
                        if 'RST' in s or 'R' in s: active_flags.append('RST')
                        if 'PSH' in s: active_flags.append('PSH')
                        if 'ACK' in s or 'A' in s: active_flags.append('ACK')
                        if 'URG' in s or 'U' in s: active_flags.append('URG')

                    tcp_flags = ", ".join(active_flags) if active_flags else "None"

                    last_seen_ms = _get_attr(flow, 'bidirectional_last_seen_ms', 'last_seen_ms', 'last_seen', default=time.time() * 1000)
                    try:
                        ts = float(last_seen_ms) / 1000.0
                    except Exception:
                        ts = time.time()

                    length = _get_attr(flow, 'bidirectional_bytes', 'bytes', 'total_bytes', 'flow_bytes', 0)
                    packet_count = _get_attr(flow, 'bidirectional_packets', 'packets', 'packet_count', 1)

                    src_ip = _get_attr(flow, 'src_ip', 'ip', '')
                    dst_ip = _get_attr(flow, 'dst_ip', 'dst', '')

                    # Look up MACs from Scapy cache
                    src_mac = ""
                    dst_mac = ""
                    mac_key = (src_ip, dst_ip)
                    if mac_key in self._mac_cache:
                        src_mac, dst_mac = self._mac_cache[mac_key]

                    parsed = {
                        "timestamp": f"{ts:.6f}",
                        "src_ip": src_ip,
                        "dst_ip": dst_ip,
                        "src_port": _get_attr(flow, 'src_port', 'sport', None),
                        "dst_port": _get_attr(flow, 'dst_port', 'dport', None),
                        "src_mac": src_mac,
                        "dst_mac": dst_mac,
                        "protocol": protocol,
                        "tcp_flags": tcp_flags,
                        "length": int(length) if isinstance(length, (int, float)) else 0,
                        "packet_count": int(packet_count) if isinstance(packet_count, (int, float)) else 1,
                        "info": f"Flow with {int(packet_count) if isinstance(packet_count, (int, float)) else 1} packets",
                    }

                    # Log emitted flow for debugging
                    try:
                        logger.info(
                            "Emitting flow: %s -> %s packets=%s src_mac=%s dst_mac=%s",
                            parsed.get("src_ip"),
                            parsed.get("dst_ip"),
                            parsed.get("packet_count"),
                            parsed.get("src_mac"),
                            parsed.get("dst_mac"),
                        )
                    except Exception:
                        logger.exception("Failed to log emitted flow")

                    self._callback(parsed)
                except Exception as pf_exc:
                    try:
                        logger.error("Failed to parse flow object: %s", pf_exc)
                        flow_dict = getattr(flow, "__dict__", None)
                        if isinstance(flow_dict, dict):
                            keys = list(flow_dict.keys())[:10]
                        else:
                            keys = [type(flow).__name__]
                        logger.debug("Flow sample attrs: %s", keys)
                    except Exception:
                        logger.exception("Failed while logging bad flow")
                    continue
                
        except Exception as e:
            logger.error(f"Sniffer error: {e}")
            logger.debug(traceback.format_exc())
            if self._error_callback:
                self._error_callback(str(e))
        finally:
            self._running.clear()
            logger.info("Sniffer thread terminated.")
