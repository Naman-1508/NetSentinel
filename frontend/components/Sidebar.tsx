"use client";

import React from "react";
import { usePacketStore } from "../store/packetStore";
import { WsConnectionState } from "../hooks/usePacketCapture";

interface StatRecord {
  label: string;
  value: number;
  total: number;
  color: string;
}

function MiniBarChart({ data }: { data: StatRecord[] }) {
  return (
    <div className="flex w-full h-1.5 overflow-hidden bg-[var(--surface-2)] rounded-full mb-4 mt-2">
      {data.map((stat) => {
        const pct = stat.total > 0 ? (stat.value / stat.total) * 100 : 0;
        if (pct === 0) return null;
        return (
          <div
            key={stat.label}
            style={{ width: `${pct}%`, backgroundColor: stat.color }}
            className="h-full transition-all duration-500 first:rounded-l-full last:rounded-r-full"
            title={`${stat.label}: ${stat.value} (${pct.toFixed(1)}%)`}
          />
        );
      })}
    </div>
  );
}

function StatRow({ stat }: { stat: StatRecord }) {
  const pct = stat.total > 0 ? (stat.value / stat.total) * 100 : 0;
  return (
    <div className="flex items-center justify-between py-1.5 px-2 rounded-md hover:bg-[var(--surface-hover)] transition-colors cursor-default">
      <div className="flex items-center gap-2.5">
        <div className="w-2 h-2 rounded-full" style={{ backgroundColor: stat.color }} />
        <span className="text-[12px] font-medium text-[var(--text-secondary)]">{stat.label}</span>
      </div>
      <div className="flex items-center gap-3">
        <span className="text-[11px] text-[var(--text-muted)] font-mono-data w-10 text-right">{pct.toFixed(1)}%</span>
        <span className="text-[12px] font-mono-data text-[var(--text-primary)] font-semibold w-16 text-right tabular-nums">{stat.value.toLocaleString()}</span>
      </div>
    </div>
  );
}

interface SidebarProps {
  connectionState: WsConnectionState;
}

export default function Sidebar({ connectionState }: SidebarProps) {
  const stats = usePacketStore((s) => s.stats);
  const packetRate = usePacketStore((s) => s.packetRate);
  const captureState = usePacketStore((s) => s.captureState);

  const totalOther = Math.max(0, stats.total - stats.tcp - stats.udp - stats.icmp);

  const protocolData: StatRecord[] = [
    { label: "TCP",   value: stats.tcp,   total: stats.total, color: "#6366f1" },
    { label: "UDP",   value: stats.udp,   total: stats.total, color: "#f59e0b" },
    { label: "ICMP",  value: stats.icmp,  total: stats.total, color: "#f43f5e" },
    { label: "OTHER", value: totalOther,  total: stats.total, color: "#a78bfa" },
  ];

  const isCapturing = captureState === "capturing";
  const isPaused    = captureState === "paused";

  return (
    <div className="h-full flex flex-col p-4 overflow-y-auto bg-[var(--surface-1)] gap-4">
      
      {/* Header */}
      <h2 className="text-[11px] font-semibold text-[var(--text-tertiary)] uppercase tracking-wider flex items-center gap-2 pb-3 border-b border-[var(--border-subtle)]">
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="text-[var(--accent-light)]">
          <path d="M22 12h-4l-3 9L9 3l-3 9H2"/>
        </svg>
        Network Telemetry
      </h2>

      {/* Capture Status Badge */}
      <div className={`card-inset px-3 py-2.5 flex items-center gap-3 ${isCapturing ? 'border border-[var(--success)]/30' : ''}`}
           style={isCapturing ? { boxShadow: '0 0 16px rgba(16, 217, 130, 0.08)' } : {}}>
        <div className={`w-2.5 h-2.5 rounded-full flex-shrink-0 ${isCapturing ? 'bg-[var(--success)] animate-pulse-dot' : isPaused ? 'bg-[var(--warning)]' : 'bg-[var(--text-muted)]'}`} />
        <div>
          <div className="text-[10px] text-[var(--text-muted)] font-mono-data uppercase tracking-wider">Capture Engine</div>
          <div className={`text-[12px] font-semibold font-mono-data ${isCapturing ? 'text-[var(--success)]' : isPaused ? 'text-[var(--warning)]' : 'text-[var(--text-tertiary)]'}`}>
            {captureState === 'idle' ? 'STANDBY' : captureState.toUpperCase()}
          </div>
        </div>
        {isCapturing && (
          <div className="ml-auto text-[10px] font-mono-data text-[var(--success)] font-bold tracking-wider">REC</div>
        )}
      </div>

      {/* Total Packets Card */}
      <div className="card-inset p-4">
        <div className="text-[10px] text-[var(--text-muted)] font-mono-data uppercase tracking-wider mb-1">Total Frames</div>
        <div className="text-3xl font-display font-bold text-[var(--text-primary)] tracking-tight flex items-center gap-2 mb-4">
          {stats.total.toLocaleString()}
        </div>

        <div className="grid grid-cols-2 gap-3 pt-3 border-t border-[var(--border-subtle)]">
          <div>
            <div className="text-[10px] text-[var(--text-muted)] font-mono-data uppercase tracking-wider mb-1">Throughput</div>
            <div className="text-[14px] font-mono-data font-semibold text-[var(--info)] flex items-baseline gap-1">
              {packetRate.toLocaleString()} <span className="text-[10px] text-[var(--text-muted)] font-normal">pkt/s</span>
            </div>
          </div>
          <div>
            <div className="text-[10px] text-[var(--text-muted)] font-mono-data uppercase tracking-wider mb-1">Backend</div>
            <div className={`text-[11px] font-semibold font-mono-data mt-0.5 ${connectionState === 'connected' ? 'text-[var(--success)]' : 'text-[var(--danger)]'}`}>
              {connectionState.toUpperCase()}
            </div>
          </div>
        </div>
      </div>

      {/* Protocol Distribution */}
      <div className="card-inset p-4">
        <div className="flex justify-between items-center mb-1">
           <div className="text-[11px] text-[var(--text-tertiary)] font-medium uppercase tracking-wider text-[10px]">Protocol Vector</div>
           <div className="text-[11px] text-[var(--accent-light)] font-mono-data">{stats.total > 0 ? '100%' : '—'}</div>
        </div>
        
        <MiniBarChart data={protocolData} />
        
        <div className="flex flex-col gap-0.5">
          {protocolData.map((stat) => (
            <StatRow key={stat.label} stat={stat} />
          ))}
        </div>
      </div>

      {/* Footer */}
      <div className="mt-auto pt-2 text-center border-t border-[var(--border-subtle)]">
        <div className="text-[10px] font-mono-data text-[var(--text-muted)] tracking-widest uppercase">NetSentinel // v2.1.0</div>
      </div>
    </div>
  );
}
