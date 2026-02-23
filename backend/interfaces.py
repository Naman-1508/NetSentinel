"""
Network interface discovery module.
Lists all available network interfaces with their IP addresses and friendly names.
"""
from typing import List, Dict
import logging

logger = logging.getLogger(__name__)


def get_interfaces() -> List[Dict[str, str]]:
    """Return list of available network interfaces with addresses and friendly names."""
    interfaces = []
    try:
        from scapy.all import conf

        # conf.ifaces is a NetworkInterfaceDict; each entry has .name, .description, .ip
        for iface_name, iface in conf.ifaces.items():
            try:
                ip = getattr(iface, "ip", None) or ""
                # Friendly description (e.g. "Wi-Fi", "Ethernet") — Windows only
                description = getattr(iface, "description", None) or ""
                # network_name is the NPF GUID name (used by Scapy for sniff())
                network_name = getattr(iface, "network_name", None) or iface_name

                # Build a human-readable label
                if description and ip and ip != "0.0.0.0":
                    display = f"{description} ({ip})"
                elif description:
                    display = description
                elif ip and ip != "0.0.0.0":
                    display = f"{network_name} ({ip})"
                else:
                    display = network_name

                interfaces.append({
                    "name": network_name,   # used by Scapy for capture
                    "ip": ip if ip and ip != "0.0.0.0" else "N/A",
                    "display": display,     # shown in the UI dropdown
                    "description": description,
                })
            except Exception:
                interfaces.append({
                    "name": iface_name,
                    "ip": "N/A",
                    "display": iface_name,
                    "description": "",
                })

    except Exception as e:
        logger.error(f"Failed to enumerate interfaces via conf.ifaces: {e}")
        # Fallback: use get_if_list()
        try:
            from scapy.all import get_if_list, get_if_addr
            for iface in get_if_list():
                try:
                    addr = get_if_addr(iface)
                    ip_str = addr if addr and addr != "0.0.0.0" else "N/A"
                    interfaces.append({
                        "name": iface,
                        "ip": ip_str,
                        "display": f"{iface} ({ip_str})" if ip_str != "N/A" else iface,
                        "description": "",
                    })
                except Exception:
                    interfaces.append({"name": iface, "ip": "N/A", "display": iface, "description": ""})
        except Exception as e2:
            logger.error(f"Fallback interface listing also failed: {e2}")
            interfaces = [{"name": "lo", "ip": "127.0.0.1", "display": "Loopback (127.0.0.1)", "description": "Loopback"}]

    return interfaces


def get_default_interface() -> str:
    """Return the default interface name (network_name for Scapy)."""
    try:
        from scapy.all import conf
        iface = conf.iface
        # On Windows, conf.iface is an interface object — get its network_name
        return getattr(iface, "network_name", str(iface))
    except Exception:
        return ""
