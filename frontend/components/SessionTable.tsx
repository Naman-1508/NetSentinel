"use client";

import React, { useRef, memo, useMemo } from "react";
import { FixedSizeList, ListChildComponentProps } from "react-window";
import { AutoSizer } from "react-virtualized-auto-sizer";
import { PROTOCOL_COLORS, PROTOCOL_BG } from "../types/packet";
import { useSessionStore } from "../store/sessionStore";
import { SessionData } from "../types/session";

const COLUMNS = [
  { label: "Status",      width: 90,  key: "status",   align: "left" },
  { label: "Protocol",    width: 90,  key: "protocol", align: "left" },
  { label: "Source",      width: 200, key: "src",      align: "left" },
  { label: "Destination", width: 200, key: "dst",      align: "left" },
  { label: "Duration",    width: 80,  key: "duration", align: "right" },
  { label: "Packets",     width: 80,  key: "packets",  align: "right" },
  { label: "Bytes",       width: 90,  key: "bytes",    align: "right" },
  { label: "Tx Rate",     width: 90,  key: "brate",    align: "right" },
];

const ROW_HEIGHT = 44;

interface RowData {
  sessions: SessionData[];
  selectedId: string | null;
  onSelectSession: (id: string | null) => void;
}

type RowProps = ListChildComponentProps<RowData>;

const SessionRow = memo(({ index, style, data }: RowProps) => {
  const { sessions, selectedId, onSelectSession } = data;
  const s = sessions[index];
  if (!s) return null;

  const isSelected = s.id === selectedId;
  const protoColor = PROTOCOL_COLORS[s.protocol] ?? "#6b7280";

  const src = s.src_port ? `${s.src_ip}:${s.src_port}` : s.src_ip;
  const dst = s.dst_port ? `${s.dst_ip}:${s.dst_port}` : s.dst_ip;
  
  const isActive = s.status === "Active";

  return (
    <div
      style={{
        ...style,
        top: `${parseFloat(style.top as string) + 4}px`, 
        height: `${ROW_HEIGHT - 4}px`, 
        backgroundColor: isSelected ? "var(--accent-dim)" : "var(--surface-1)",
        border: isSelected ? "1px solid rgba(99, 102, 241, 0.3)" : "1px solid var(--border-subtle)",
        cursor: "pointer",
        display: "flex",
        alignItems: "center",
        userSelect: "none",
        borderRadius: "10px",
        margin: "0 8px",
        width: `calc(100% - 16px)`,
        transition: "all 0.15s ease",
      }}
      className={`text-[11px] font-mono-data hover:bg-[var(--surface-hover)] hover:border-[var(--border-medium)] group ${isSelected ? 'z-10' : 'z-0'}`}
      onClick={() => onSelectSession(s.id)}
    >
      <span style={{ width: 90, flexShrink: 0, paddingLeft: 12 }}>
         <span className={`pill text-[9px] font-semibold
           ${isActive 
             ? "bg-emerald-500/10 text-emerald-400 border border-emerald-500/30" 
             : "bg-[var(--surface-2)] text-[var(--text-muted)] border border-[var(--border-subtle)]"}`}>
           {isActive && <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse-dot" />}
           {s.status}
         </span>
      </span>
      
      <span style={{ width: 90, flexShrink: 0, paddingRight: 8 }} className="flex items-center">
        <span 
          className="pill text-[10px] font-semibold"
          style={{ 
            color: protoColor, 
            backgroundColor: `${protoColor}15`,
          }}
        >
          {s.protocol}
        </span>
      </span>

      <span style={{ width: 200, flexShrink: 0, color: "var(--text-primary)", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
        {src}
      </span>
      <span style={{ width: 200, flexShrink: 0, color: "var(--text-secondary)", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
        {dst}
      </span>
      
      <span style={{ width: 80, flexShrink: 0, color: "var(--text-tertiary)", textAlign: "right", paddingRight: 16 }}>
        {s.duration.toFixed(1)}<span className="text-[9px] text-[var(--text-muted)] ml-0.5">s</span>
      </span>
      <span style={{ width: 80, flexShrink: 0, color: "var(--text-tertiary)", textAlign: "right", paddingRight: 16 }}>
        {s.packet_count}
      </span>
      <span style={{ width: 90, flexShrink: 0, color: "var(--text-tertiary)", textAlign: "right", paddingRight: 16 }}>
        {s.bytes} <span className="text-[9px] text-[var(--text-muted)]">B</span>
      </span>
      <span style={{ flex: 1, paddingRight: 16, color: "var(--accent-light)", textAlign: "right" }} className="font-semibold">
        {s.byte_rate.toFixed(0)} <span className="text-[9px] font-normal text-[var(--text-muted)] ml-0.5">B/s</span>
      </span>
    </div>
  );
});
SessionRow.displayName = "SessionRow";

export default function SessionTable() {
  const sessionsList = useSessionStore((s) => s.sessionsList);
  const selectedSessionId = useSessionStore((s) => s.selectedSessionId);
  const selectSession = useSessionStore((s) => s.selectSession);

  const listRef = useRef<FixedSizeList<RowData>>(null);

  const itemData: RowData = useMemo(() => ({
    sessions: sessionsList,
    selectedId: selectedSessionId,
    onSelectSession: selectSession,
  }), [sessionsList, selectedSessionId, selectSession]);

  return (
    <div style={{ display: "flex", flexDirection: "column", height: "100%" }} className="bg-[var(--bg-app)]">
      {/* Header row */}
      <div
        style={{
          display: "flex",
          alignItems: "center",
          height: 32,
          flexShrink: 0,
        }}
        className="text-[11px] font-medium text-[var(--text-tertiary)] select-none border-b border-[var(--border-subtle)] bg-[var(--surface-1)] px-2 tracking-wide"
      >
        {COLUMNS.map((col) => (
          <span
            key={col.key}
            style={{
              width: col.width === -1 ? undefined : col.width,
              flex: col.width === -1 ? 1 : undefined,
              flexShrink: 0,
              paddingLeft: col.key === "status" ? 12 : 0,
              paddingRight: col.align === "right" ? 16 : 0,
              color: "var(--text-tertiary)",
              textAlign: (col.align as any) || "left",
              overflow: "hidden",
              textOverflow: "ellipsis",
              whiteSpace: "nowrap",
            }}
          >
            {col.label}
          </span>
        ))}
      </div>

      {/* Virtualized rows */}
      <div style={{ flex: 1, minHeight: 0 }} className="relative">
        {sessionsList.length === 0 ? (
          <div
            style={{ display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", height: "100%", gap: 16 }}
            className="text-[var(--text-muted)]"
          >
            <div className="w-14 h-14 rounded-xl bg-[var(--surface-2)] border border-[var(--border-subtle)] flex items-center justify-center">
              <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" className="text-[var(--text-tertiary)]">
                <circle cx="12" cy="12" r="10"/><path d="M12 8v4l3 3"/>
              </svg>
            </div>
            <div className="text-center">
              <div className="text-sm font-semibold mb-1 text-[var(--text-secondary)]">No Active Sessions</div>
              <div className="text-xs">Sessions appear automatically during capture.</div>
            </div>
          </div>
        ) : (
          <AutoSizer
            renderProp={({ height, width }) => (
              <FixedSizeList<RowData>
                ref={listRef}
                height={height ?? 400}
                width={width ?? 800}
                itemCount={sessionsList.length}
                itemSize={ROW_HEIGHT}
                itemData={itemData}
                overscanCount={20}
                className="pb-8 pt-2"
              >
                {SessionRow}
              </FixedSizeList>
            )}
          />
        )}
      </div>
    </div>
  );
}
