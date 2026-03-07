"use client";

import React from "react";
import { PacketData, PROTOCOL_COLORS } from "../types/packet";
import { usePacketStore } from "../store/packetStore";

interface SectionProps {
  title: string;
  fields: Record<string, string | number | null | undefined>;
  open?: boolean;
}

function DetailTreeSection({ title, fields, open = true }: SectionProps) {
  const [isOpen, setIsOpen] = React.useState(open);

  return (
    <div className="mb-1 font-mono-data text-[11.5px]">
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="flex items-center gap-2 w-full text-left outline-none py-1 px-2 rounded-md hover:bg-[var(--surface-hover)] transition-colors group"
      >
        <span className="w-3 text-center text-[var(--text-muted)] transition-transform inline-block" style={{ transform: isOpen ? "rotate(90deg)" : "rotate(0deg)" }}>
          <svg width="8" height="8" viewBox="0 0 24 24" fill="currentColor"><path d="M5 3l14 9-14 9V3z"/></svg>
        </span>
        <span className="font-medium text-[var(--text-primary)] group-hover:text-[var(--accent-light)] transition-colors">
          {title}
        </span>
      </button>

      {isOpen && (
        <div className="pl-7 py-1 flex flex-col gap-0.5 fade-in">
          {Object.entries(fields).map(([k, v]) => (
            <div key={k} className="flex gap-2 py-0.5 px-2 rounded hover:bg-[var(--surface-hover)] transition-colors cursor-default">
              <span className="text-[var(--text-tertiary)]">{k}:</span>
              <span className="text-[var(--text-primary)] break-all whitespace-pre-wrap">
                {v === null || v === undefined ? (
                  <span className="text-[var(--text-muted)] italic select-none">null</span>
                ) : (
                  String(v)
                )}
              </span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

function formatTimestamp(ts: string): string {
  const sec = parseFloat(ts);
  const date = new Date(sec * 1000);
  return `${date.toUTCString()} - Epoch: ${ts}`;
}

export default function PacketDetailPane() {
  const pkt: PacketData | null = usePacketStore((s) => s.selectedPacket);

  if (!pkt) {
    return (
      <div className="flex flex-col items-center justify-center h-full text-[var(--text-muted)] p-6 text-center">
        <div className="text-[13px]">Select a packet to view details</div>
      </div>
    );
  }

  const frameTitle = `Frame ${pkt.id}: ${pkt.length} bytes on wire (${pkt.length * 8} bits)`;
  const frameFields: Record<string, string | number | null> = {
    "Interface": "eth0 (assumed)",
    "Arrival Time": formatTimestamp(pkt.timestamp)
  };

  const ethernetTitle = `Ethernet II, Src: (${pkt.src_ip}), Dst: (${pkt.dst_ip})`;
  const ethernetFields: Record<string, string | number | null> = {
    "Destination": pkt.dst_ip,
    "Source": pkt.src_ip,
    "Type": pkt.protocol === "ARP" ? "ARP (0x0806)" : "IPv4 (0x0800)",
  };

  const ipTitle = `Internet Protocol Version 4, Src: ${pkt.src_ip}, Dst: ${pkt.dst_ip}`;
  const ipFields: Record<string, string | number | null> = {
    "Version": 4,
    "Header Length": "20 bytes (5)",
    "Total Length": pkt.length,
    "Protocol": pkt.protocol,
  };

  const transportTitle = pkt.protocol === "UDP" || pkt.protocol === "DNS" ? 
    `User Datagram Protocol, Src Port: ${pkt.src_port}, Dst Port: ${pkt.dst_port}` :
    pkt.protocol === "TCP" || pkt.protocol.startsWith("TLS") ? 
    `Transmission Control Protocol, Src Port: ${pkt.src_port}, Dst Port: ${pkt.dst_port}` :
    `Protocol Data: ${pkt.protocol}`;

  const transportFields: Record<string, string | number | null> = {};
  if (pkt.src_port) transportFields["Source Port"] = pkt.src_port;
  if (pkt.dst_port) transportFields["Destination Port"] = pkt.dst_port;
  if (pkt.tcp_flags) transportFields["Flags"] = pkt.tcp_flags;
  if (pkt.info) transportFields["Info"] = pkt.info;

  return (
    <div className="h-full bg-[var(--bg-app)] text-[var(--text-secondary)] overflow-y-auto p-3 select-text">
       <DetailTreeSection title={frameTitle} fields={frameFields} open={true} />
       <DetailTreeSection title={ethernetTitle} fields={ethernetFields} open={true} />
       <DetailTreeSection title={ipTitle} fields={ipFields} open={true} />
       <DetailTreeSection title={transportTitle} fields={transportFields} open={true} />
       
       {(pkt.protocol === "DNS" || pkt.protocol.startsWith("TLS")) && (
          <DetailTreeSection title={`${pkt.protocol} Layer Details`} fields={{ "Raw Payload": pkt.info }} open={false} />
       )}
    </div>
  );
}
