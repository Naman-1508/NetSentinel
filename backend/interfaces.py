"""Network interface discovery helpers with Windows-friendly adapter details."""
from typing import List, Dict, Any
import json
import logging
import os
import socket
import subprocess
import time

import psutil

logger = logging.getLogger(__name__)

_WIN_ADAPTER_CACHE: Dict[str, Any] = {"ts": 0.0, "data": {}}
_WIN_CACHE_TTL_SECONDS = 5.0


def _is_windows() -> bool:
    return os.name == "nt"


def _load_windows_adapter_details() -> Dict[str, Dict[str, Any]]:
    """Fetch Name -> adapter details from PowerShell Get-NetAdapter."""
    if not _is_windows():
        return {}

    now = time.time()
    if now - _WIN_ADAPTER_CACHE["ts"] < _WIN_CACHE_TTL_SECONDS:
        return _WIN_ADAPTER_CACHE["data"]

    ps_cmd = (
        "Get-NetAdapter | Select-Object Name, InterfaceDescription, Status, MacAddress, InterfaceGuid "
        "| ConvertTo-Json -Compress"
    )

    try:
        # Run PowerShell hidden to avoid spawning visible console windows
        run_kwargs = dict(
            args=["powershell", "-NoProfile", "-Command", ps_cmd],
            capture_output=True,
            text=True,
            timeout=3,
            check=False,
            stdin=subprocess.DEVNULL,
        )
        if os.name == "nt":
            # CREATE_NO_WINDOW prevents a new console window from appearing
            run_kwargs["creationflags"] = subprocess.CREATE_NO_WINDOW

        result = subprocess.run(**run_kwargs)
        if result.returncode != 0 or not result.stdout.strip():
            return {}

        parsed = json.loads(result.stdout)
        adapters = parsed if isinstance(parsed, list) else [parsed]

        details: Dict[str, Dict[str, Any]] = {}
        for adapter in adapters:
            name = str(adapter.get("Name", "")).strip()
            if not name:
                continue
            details[name] = {
                "description": str(adapter.get("InterfaceDescription", "")).strip(),
                "status": str(adapter.get("Status", "")).strip(),
                "mac": str(adapter.get("MacAddress", "")).strip(),
                "guid": str(adapter.get("InterfaceGuid", "")).strip(),
            }

        _WIN_ADAPTER_CACHE["ts"] = now
        _WIN_ADAPTER_CACHE["data"] = details
        return details
    except Exception as exc:
        logger.debug(f"Failed to query Get-NetAdapter: {exc}")
        return {}


def _extract_ipv4(addrs: List[Any]) -> str:
    for addr in addrs:
        if addr.family == socket.AF_INET and addr.address:
            return addr.address
    return "N/A"


def _is_virtual_or_loopback(name: str, description: str) -> bool:
    text = f"{name} {description}".lower()
    markers = [
        "loopback",
        "vethernet",
        "virtual",
        "vmware",
        "hyper-v",
        "bluetooth",
        "teredo",
        "isatap",
        "wsl",
        "docker",
        "npcap",
    ]
    return any(marker in text for marker in markers)


def _interface_score(item: Dict[str, str]) -> int:
    score = 0
    if item.get("description", "").lower().startswith("up"):
        score += 40
    ip = item.get("ip", "N/A")
    if ip not in ("N/A", "0.0.0.0") and not ip.startswith("169.254"):
        score += 40

    display_l = item.get("display", "").lower()
    if "wi-fi" in display_l or "wifi" in display_l or "wireless" in display_l:
        score += 20
    if "ethernet" in display_l:
        score += 15

    if _is_virtual_or_loopback(item.get("name", ""), item.get("display", "")):
        score -= 40

    return score


def _load_scapy_iface_map() -> Dict[str, str]:
    """Return a mapping of OS interface name -> pcap device name using scapy when available.
    On Windows `get_windows_if_list()` contains WinPcap-friendly names; on other OSes we
    map the logical interface name to itself.
    """
    try:
        import scapy.all as scapy
    except Exception:
        return {}

    try:
        mapping: Dict[str, str] = {}
        # scapy.conf.ifaces keys are libpcap device names (\Device\NPF_{...}) on Windows
        if hasattr(scapy, 'conf') and hasattr(scapy.conf, 'ifaces'):
            for npf_name, iface in scapy.conf.ifaces.items():
                try:
                    logical = getattr(iface, 'name', None) or getattr(iface, 'description', None)
                    mac = getattr(iface, 'mac', None)
                    ip = getattr(iface, 'ip', None)
                except Exception:
                    logical = None
                    mac = None
                    ip = None

                if logical:
                    mapping[logical] = npf_name
                if mac:
                    mapping[mac.lower()] = npf_name
                if ip:
                    mapping[ip] = npf_name

        # For unix-like fallback, map interface name to itself
        elif hasattr(scapy, 'get_if_list'):
            for n in scapy.get_if_list():
                mapping[n] = n

        return mapping
    except Exception:
        return {}

def get_interfaces() -> List[Dict[str, str]]:
    """Return list of available network interfaces with addresses and friendly names."""
    interfaces = []
    try:
        if_addrs = psutil.net_if_addrs()
        if_stats = psutil.net_if_stats()
        win_details = _load_windows_adapter_details()

        for iface_name, addrs in sorted(if_addrs.items(), key=lambda kv: kv[0].lower()):
            ip = _extract_ipv4(addrs)
            stats = if_stats.get(iface_name)
            is_up = stats.isup if stats else False
            state = "Up" if is_up else "Down"

            extra = win_details.get(iface_name, {})
            hw_desc = extra.get("description", "")
            if hw_desc:
                display_base = f"{hw_desc} [{iface_name}]"
            else:
                display_base = iface_name

            display = f"{display_base} ({ip})" if ip != "N/A" and ip != "0.0.0.0" else display_base

            interfaces.append({
                "name": iface_name,
                "ip": ip,
                "display": display,
                "description": state,
            })

        # Try to augment with scapy pcap device names when available
        scapy_map = _load_scapy_iface_map()
        for item in interfaces:
            # Prefer exact name mapping, otherwise try to match keywords
            pcap = scapy_map.get(item['name'])
            if not pcap:
                # try matching short descriptors
                for k, v in scapy_map.items():
                    if k.lower() in item['display'].lower() or item['name'].lower() in k.lower():
                        pcap = v
                        break
            item['pcap_name'] = pcap or item['name']

        interfaces.sort(key=_interface_score, reverse=True)
    except Exception as e:
        logger.error(f"Failed to enumerate interfaces via psutil: {e}")
        interfaces = [{"name": "lo", "ip": "127.0.0.1", "display": "Loopback (127.0.0.1)", "description": "Loopback"}]

    return interfaces

def get_default_interface() -> str:
    """Return the default interface name based on routing or first available."""
    try:
        interfaces = get_interfaces()
        if interfaces:
            return interfaces[0]["name"]
    except Exception:
        logger.debug("Could not compute default interface.")
    return ""


def resolve_capture_interface(selected: str) -> str:
    """Resolve a possibly stale UI value back to a real interface name."""
    if not selected:
        return get_default_interface()

    interfaces = get_interfaces()
    names = {item["name"] for item in interfaces}
    # If the selected value is already a pcap device, return it
    for item in interfaces:
        if selected == item.get('pcap_name'):
            return selected

    if selected in names:
        # Return the pcap device for that interface if available
        for item in interfaces:
            if item['name'] == selected:
                return item.get('pcap_name') or selected

    selected_l = selected.lower()
    for item in interfaces:
        if selected_l in item["display"].lower() or selected_l in item["name"].lower():
            return item.get('pcap_name') or item["name"]

    return selected
