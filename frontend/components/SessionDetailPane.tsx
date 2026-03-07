"use client";

import React from "react";
import { PROTOCOL_COLORS } from "../types/packet";
import { useSessionStore } from "../store/sessionStore";
import { SessionData } from "../types/session";

interface SectionProps {
  title: string;
  fields: Record<string, string | number | null | undefined>;
  color?: string;
  icon?: React.ReactNode;
  open?: boolean;
}

function DetailSection({ title, fields, color = "var(--text-tertiary)", icon, open = true }: SectionProps) {
  const [isOpen, setIsOpen] = React.useState(open);

  return (
    <div className="mb-3">
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="w-full flex items-center gap-2 mb-2 group outline-none hover:bg-[var(--surface-hover)] rounded-md px-1 py-0.5 transition-colors"
      >
        <span
          className="w-3 h-3 flex items-center justify-center transition-transform duration-200"
          style={{ transform: isOpen ? "rotate(90deg)" : "rotate(0deg)", color }}
        >
          <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round"><polygon points="5 3 19 12 5 21 5 3"/></svg>
        </span>
        <div className="flex items-center gap-1.5">
          {icon && <span style={{ color }}>{icon}</span>}
          <span className="text-[11px] font-semibold uppercase tracking-wider" style={{ color }}>
            {title}
          </span>
        </div>
        <div className="flex-1 h-px bg-[var(--border-subtle)] group-hover:bg-[var(--border-medium)] transition-colors" />
      </button>

      {isOpen && (
        <div className="pl-5 pr-2 fade-in">
          <div className="border-l-2 border-[var(--border-subtle)] pl-3 py-1 space-y-1.5 font-mono-data text-[11.5px]">
            {Object.entries(fields).map(([k, v]) => (
              <div key={k} className="flex gap-4 group/row items-center hover:bg-[var(--surface-hover)] rounded px-1 transition-colors">
                <span className="text-[var(--text-muted)] w-32 flex-shrink-0 group-hover/row:text-[var(--text-tertiary)] transition-colors">{k}:</span>
                <span className="text-[var(--text-primary)] font-medium break-all whitespace-pre-wrap">
                  {v === null || v === undefined ? (
                    <span className="text-[var(--text-muted)] italic select-none">null</span>
                  ) : (
                    String(v)
                  )}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

function formatTimestamp(ts: number): string {
  const date = new Date(ts * 1000);
  return `${date.toISOString().replace("T", " ").slice(0, -1)} Z`;
}

function MetricCard({ label, value, color }: { label: string, value: React.ReactNode, color: string }) {
  return (
    <div className="flex-1 card-inset p-3 group">
      <div className="text-[10px] font-medium uppercase tracking-wider text-[var(--text-muted)] mb-1">{label}</div>
      <div className="text-base font-display font-semibold text-[var(--text-primary)] truncate">{value}</div>
    </div>
  );
}

export default function SessionDetailPane() {
  const selectedSessionId = useSessionStore((s) => s.selectedSessionId);
  const activeSessions = useSessionStore((s) => s.activeSessions);
  const closedSessions = useSessionStore((s) => s.closedSessions);
  
  const s: SessionData | undefined = selectedSessionId 
    ? (activeSessions[selectedSessionId] || closedSessions[selectedSessionId]) 
    : undefined;

  if (!s) {
    return (
      <div className="flex flex-col items-center justify-center h-full text-[var(--text-muted)] p-6 text-center gap-3">
        <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1" strokeLinecap="round" strokeLinejoin="round" className="opacity-30">
          <circle cx="12" cy="12" r="10"/><path d="M12 8v4l3 3"/>
        </svg>
        <span className="text-xs">Select a session to view details.</span>
      </div>
    );
  }

  const protocolColor = PROTOCOL_COLORS[s.protocol] ?? "#6b7280";
  const isActive = s.status === "Active";

  const timeFields: Record<string, string | number | null> = {
    "Start Time":     formatTimestamp(s.start_time),
    "Last seen":      formatTimestamp(s.last_seen),
    "Duration":       `${s.duration.toFixed(3)} seconds`,
  };

  const transportFields: Record<string, React.ReactNode | string | number | null> = {};
  if (s.protocol === "TCP") {
    transportFields["Connection Setup (SYN)"] = <span className={s.syn_count > 0 ? "text-emerald-400 font-bold" : ""}>{s.syn_count}</span>;
    transportFields["Acknowledge (ACK)"] = <span className={s.ack_count > 0 ? "text-sky-400 font-bold" : ""}>{s.ack_count}</span>;
    transportFields["Graceful Close (FIN)"] = <span className={s.fin_count > 0 ? "text-amber-400 font-bold" : ""}>{s.fin_count}</span>;
    transportFields["Force Reset (RST)"] = <span className={s.rst_count > 0 ? "text-rose-400 font-bold" : ""}>{s.rst_count}</span>;
  }

  return (
    <div className="h-full bg-[var(--bg-app)] text-[var(--text-secondary)] overflow-y-auto p-4">
      
      {/* Session Header Card */}
      <div className="card p-4 mb-5">
         <div className="flex flex-col gap-3">
           <div className="flex items-center gap-2">
             <span className={`pill text-[10px] font-semibold
               ${isActive ? "bg-emerald-500/10 text-emerald-400 border border-emerald-500/30" : "bg-[var(--surface-2)] text-[var(--text-muted)] border border-[var(--border-subtle)]"}`}>
               {isActive && <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse-dot" />}
               {s.status}
             </span>
             <span className="pill text-[10px] font-semibold border border-[var(--border-subtle)]" style={{ color: protocolColor, backgroundColor: `${protocolColor}15` }}>
               {s.protocol}
             </span>
           </div>
           
           <div className="grid grid-cols-[1fr_auto_1fr] items-center gap-3 mt-1">
             <div className="text-right">
                <div className="text-[10px] text-[var(--text-muted)] font-medium uppercase tracking-wider mb-1">Source</div>
                <div className="font-mono-data text-[13px] text-[var(--text-primary)]">{s.src_ip}</div>
                {s.src_port && <div className="text-xs text-[var(--accent-light)] font-mono-data">:{s.src_port}</div>}
             </div>
             <div className="flex flex-col items-center px-2">
                <div className="h-px w-8 bg-[var(--border-medium)] relative">
                  <div className="absolute right-0 top-1/2 -translate-y-1/2 w-1.5 h-1.5 rotate-45 border-t border-r border-[var(--text-muted)]" />
                </div>
             </div>
             <div className="text-left">
                <div className="text-[10px] text-[var(--text-muted)] font-medium uppercase tracking-wider mb-1">Destination</div>
                <div className="font-mono-data text-[13px] text-[var(--text-primary)]">{s.dst_ip}</div>
                {s.dst_port && <div className="text-xs text-[var(--info)] font-mono-data">:{s.dst_port}</div>}
             </div>
           </div>
         </div>
      </div>

      <div className="flex gap-2 mb-6">
        <MetricCard label="Volume" value={<>{s.packet_count} <span className="text-[10px] text-[var(--text-muted)]">pkts</span></>} color="#8b5cf6" />
        <MetricCard label="Data" value={<>{s.bytes} <span className="text-[10px] text-[var(--text-muted)]">B</span></>} color="#3b82f6" />
        <MetricCard label="Speed" value={<>{s.byte_rate.toFixed(0)} <span className="text-[10px] text-[var(--text-muted)]">B/s</span></>} color="#10b981" />
      </div>

      <DetailSection
        title="Session Chronology"
        icon={<svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/></svg>}
        fields={timeFields}
        color="#f59e0b"
      />
      
      {s.protocol === "TCP" && (
        <DetailSection
          title="TCP State Machine"
          icon={<svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/></svg>}
          fields={transportFields as Record<string, any>}
          color={protocolColor}
        />
      )}
    </div>
  );
}
