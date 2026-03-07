// Shared TypeScript types for the packet capture tool.
// Used by all frontend components and hooks.

export type Protocol = "TCP" | "UDP" | "ICMP" | "ARP" | "DNS" | "TLSv1.2" | "TLSv1.3" | "OTHER";

export type CaptureState = "idle" | "capturing" | "paused" | "stopped";

export interface PacketData {
  id: number;
  timestamp: string;
  src_ip: string;
  dst_ip: string;
  src_port: number | null;
  dst_port: number | null;
  protocol: Protocol;
  tcp_flags: string | null;
  length: number;
  info: string;
}

export interface NetworkInterface {
  name: string;
  ip: string;
  display: string;
  description?: string;
}

export interface CaptureStats {
  total: number;
  tcp: number;
  udp: number;
  icmp: number;
}

// WebSocket message union type — discriminated by `type`
export type WsMessage =
  | { type: "interfaces"; data: NetworkInterface[]; default: string }
  | { type: "packets"; data: PacketData[] }
  | { type: "stats"; data: CaptureStats }
  | { type: "status"; state: CaptureState }
  | { type: "error"; message: string }
  | { type: "sessions"; data: { updated: any[], closed: any[] } }; // Will type cast in hook

// Control messages sent from client to server
export type WsControlMessage =
  | { type: "start"; interface: string }
  | { type: "pause" }
  | { type: "resume" }
  | { type: "stop" }
  | { type: "get_interfaces" };

export const PROTOCOL_COLORS: Record<Protocol, string> = {
  "TCP": "#3b82f6",     // blue-500
  "UDP": "#f59e0b",     // amber-500
  "ICMP": "#eab308",    // yellow-500
  "ARP": "#10b981",     // emerald-500
  "DNS": "#8b5cf6",     // violet-500
  "TLSv1.2": "#ef4444", // red-500
  "TLSv1.3": "#ef4444", // red-500
  "OTHER": "#6b7280",   // gray-500
};

export const PROTOCOL_BG: Record<Protocol, string> = {
  "TCP": "rgba(59,130,246,0.12)",
  "UDP": "rgba(245,158,11,0.12)",
  "ICMP": "rgba(234,179,8,0.12)",
  "ARP": "rgba(16,185,129,0.12)",
  "DNS": "rgba(139,92,246,0.12)",
  "TLSv1.2": "rgba(239,68,68,0.12)",
  "TLSv1.3": "rgba(239,68,68,0.12)",
  "OTHER": "rgba(107,114,128,0.08)",
};

export const MAX_PACKETS = 2000;
export const WS_URL = process.env.NEXT_PUBLIC_WS_URL ?? "ws://localhost:8765";
