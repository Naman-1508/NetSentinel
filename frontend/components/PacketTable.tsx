"use client";

import React, { useEffect, useRef, memo } from "react";
import { FixedSizeList, ListChildComponentProps } from "react-window";
import { AutoSizer } from "react-virtualized-auto-sizer";
import { PacketData, PROTOCOL_COLORS } from "../types/packet";
import { usePacketStore } from "../store/packetStore";

const COLUMNS = [
  { label: "No.",         width: 60,  key: "id",        align: "left" },
  { label: "Time",        width: 120, key: "timestamp", align: "left" },
  { label: "Source",      width: 180, key: "src",       align: "left" },
  { label: "Destination", width: 180, key: "dst",       align: "left" },
  { label: "Protocol",    width: 90,  key: "protocol",  align: "left" },
  { label: "Length",      width: 80,  key: "length",    align: "left" },
  { label: "Info",        width: -1,  key: "info",      align: "left" },
];

const ROW_HEIGHT = 28;

interface RowData {
  packets: PacketData[];
  selectedId: number | null;
  onSelectPacket: (pkt: PacketData) => void;
}

type RowProps = ListChildComponentProps<RowData>;

const PacketRow = memo(({ index, style, data }: RowProps) => {
  const { packets, selectedId, onSelectPacket } = data;
  const pkt = packets[index];
  if (!pkt) return null;

  const isSelected = pkt.id === selectedId;
  const isAltRow = index % 2 === 0;

  const bgColor = isSelected 
    ? "rgba(99, 102, 241, 0.12)" 
    : isAltRow 
      ? "var(--surface-1)" 
      : "transparent";

  const borderLeft = isSelected ? "2px solid var(--accent-primary)" : "2px solid transparent";

  // Protocol pill colors
  const protoColor = PROTOCOL_COLORS[pkt.protocol] ?? "#6b7280";

  const src = pkt.src_port ? `${pkt.src_ip}:${pkt.src_port}` : pkt.src_ip;
  const dst = pkt.dst_port ? `${pkt.dst_ip}:${pkt.dst_port}` : pkt.dst_ip;
  const ts = parseFloat(pkt.timestamp).toFixed(6);

  const textColor = isSelected ? "var(--text-primary)" : "var(--text-secondary)";
  const idColor = isSelected ? "var(--text-primary)" : "var(--text-muted)";

  return (
    <div
      style={{
        ...style,
        backgroundColor: bgColor,
        borderLeft,
        display: "flex",
        alignItems: "center",
        cursor: "pointer",
        userSelect: "none",
        width: "100%",
        borderBottom: "1px solid var(--border-subtle)",
        transition: "background-color 0.1s ease",
      }}
      className="font-mono-data hover:bg-[var(--surface-hover)] group"
      onClick={() => onSelectPacket(pkt)}
    >
      <span style={{ width: COLUMNS[0].width, flexShrink: 0, paddingLeft: 12, color: idColor }}>{pkt.id}</span>
      <span style={{ width: COLUMNS[1].width, flexShrink: 0, color: textColor }}>{ts}</span>
      
      <span style={{ width: COLUMNS[2].width, flexShrink: 0, color: "var(--text-primary)", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap", paddingRight: 8 }}>
        {src}
      </span>
      <span style={{ width: COLUMNS[3].width, flexShrink: 0, color: "var(--text-primary)", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap", paddingRight: 8 }}>
        {dst}
      </span>

      <span style={{ width: COLUMNS[4].width, flexShrink: 0, paddingRight: 8 }} className="flex items-center">
        <span 
          className="px-2 py-0.5 rounded-full text-[10px] font-semibold"
          style={{ 
            color: protoColor, 
            backgroundColor: `${protoColor}18`,
          }}
        >
          {pkt.protocol}
        </span>
      </span>

      <span style={{ width: COLUMNS[5].width, flexShrink: 0, color: textColor, paddingRight: 8 }}>
        {pkt.length}
      </span>
      <span style={{ flex: 1, color: "var(--text-secondary)", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap", paddingRight: 12 }}>
        {pkt.info}
      </span>
    </div>
  );
});
PacketRow.displayName = "PacketRow";

export default function PacketTable() {
  const packets = usePacketStore((s) => s.packets);
  const displayFilter = usePacketStore((s) => s.displayFilter);
  const selectedPacket = usePacketStore((s) => s.selectedPacket);
  const autoScroll = usePacketStore((s) => s.autoScroll);
  const selectPacket = usePacketStore((s) => s.selectPacket);

  const filteredPackets = React.useMemo(() => {
    if (!displayFilter) return packets;
    const lowerFilter = displayFilter.toLowerCase();
    return packets.filter(p => {
      if (p.src_ip.toLowerCase().includes(lowerFilter)) return true;
      if (p.dst_ip.toLowerCase().includes(lowerFilter)) return true;
      if (p.protocol.toLowerCase().includes(lowerFilter)) return true;
      if (p.info.toLowerCase().includes(lowerFilter)) return true;
      return false;
    });
  }, [packets, displayFilter]);

  const listRef = useRef<FixedSizeList<RowData>>(null);

  useEffect(() => {
    if (autoScroll && filteredPackets.length > 0 && listRef.current) {
      listRef.current.scrollToItem(filteredPackets.length - 1, "end");
    }
  }, [filteredPackets.length, autoScroll]);

  const itemData: RowData = {
    packets: filteredPackets,
    selectedId: selectedPacket?.id ?? null,
    onSelectPacket: selectPacket,
  };

  return (
    <div style={{ display: "flex", flexDirection: "column", height: "100%", width: "100%" }} className="bg-[var(--bg-app)]">
      
      {/* Header row */}
      <div
        style={{
          display: "flex",
          alignItems: "center",
          height: 32,
          flexShrink: 0,
        }}
        className="text-[11px] font-medium text-[var(--text-tertiary)] select-none border-b border-[var(--border-subtle)] bg-[var(--surface-1)] tracking-wide"
      >
        {COLUMNS.map((col) => (
          <span
            key={col.key}
            style={{
              width: col.width === -1 ? undefined : col.width,
              flex: col.width === -1 ? 1 : undefined,
              flexShrink: 0,
              paddingLeft: col.key === "id" ? 14 : 0,
              paddingRight: col.align === "right" ? 16 : 0,
              textAlign: (col.align as any) || "left",
              overflow: "hidden",
            }}
          >
            {col.label}
          </span>
        ))}
      </div>

      {/* Virtualized rows */}
      <div style={{ flex: 1, minHeight: 0, minWidth: 0 }} className="relative">
        {packets.length === 0 ? (
          <div
            style={{ display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", height: "100%", gap: 16 }}
            className="text-[var(--text-muted)]"
          >
            <div className="w-14 h-14 rounded-xl bg-[var(--surface-2)] border border-[var(--border-subtle)] flex items-center justify-center">
              <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" className="text-[var(--text-tertiary)]">
                <path d="M2.5 2v6h13V2l-13 0zM12.5 10v6h9v-6l-9 0zM2.5 18v4h16v-4l-16 0z" strokeLinecap="round" strokeLinejoin="round"/>
              </svg>
            </div>
            <div className="text-center">
              <div className="text-sm font-semibold mb-1 text-[var(--text-secondary)]">No packets captured</div>
              <div className="text-xs text-[var(--text-muted)]">Select an interface and click Start to begin capturing.</div>
            </div>
          </div>
        ) : (
          <AutoSizer
            renderProp={({ height, width }) => (
              <FixedSizeList<RowData>
                ref={listRef}
                height={height ?? 400}
                width={width ?? 800}
                itemCount={filteredPackets.length}
                itemSize={ROW_HEIGHT}
                itemData={itemData}
                overscanCount={20}
              >
                {PacketRow}
              </FixedSizeList>
            )}
          />
        )}
      </div>
    </div>
  );
}
