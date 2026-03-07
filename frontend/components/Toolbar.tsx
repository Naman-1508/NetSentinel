"use client";

import React from "react";
import { usePacketStore } from "../store/packetStore";
import { WsConnectionState } from "../hooks/usePacketCapture";

// Clean minimal icons
const PlayIcon = () => <svg width="14" height="14" viewBox="0 0 24 24" fill="currentColor"><path d="M5 3l14 9-14 9V3z" /></svg>;
const StopIcon = () => <svg width="12" height="12" viewBox="0 0 24 24" fill="currentColor"><path d="M4 4h16v16H4z" /></svg>;
const RefreshIcon = () => <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M21 2v6h-6"/><path d="M3 12a9 9 0 1 0 2.13-5.88L21 8"/></svg>;
const ClearIcon = () => <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><circle cx="12" cy="12" r="10"></circle><line x1="4.93" y1="4.93" x2="19.07" y2="19.07"></line></svg>;
const FilterIcon = () => <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><polygon points="22 3 2 3 10 12.46 10 19 14 21 14 12.46 22 3"/></svg>;

interface ToolbarProps {
  connectionState: WsConnectionState;
  onStart: (iface: string) => void;
  onPause: () => void;
  onResume: () => void;
  onStop: () => void;
  onRefreshInterfaces: () => void;
}

export default function Toolbar({
  connectionState,
  onStart,
  onPause,
  onResume,
  onStop,
  onRefreshInterfaces,
}: ToolbarProps) {
  const captureState = usePacketStore((s) => s.captureState);
  const interfaces = usePacketStore((s) => s.interfaces);
  const selectedInterface = usePacketStore((s) => s.selectedInterface);
  const autoScroll = usePacketStore((s) => s.autoScroll);
  const setSelectedInterface = usePacketStore((s) => s.setSelectedInterface);
  const clearPackets = usePacketStore((s) => s.clearPackets);
  const toggleAutoScroll = usePacketStore((s) => s.toggleAutoScroll);
  const displayFilter = usePacketStore((s) => s.displayFilter);
  const setDisplayFilter = usePacketStore((s) => s.setDisplayFilter);

  const isConnected = connectionState === "connected";
  const isIdle = captureState === "idle" || captureState === "stopped";
  const isCapturing = captureState === "capturing";
  const isPaused = captureState === "paused";

  return (
    <div className="flex items-center gap-3 w-full h-full text-[12px] font-medium min-w-0">
      
      {/* ── Start / Stop ── */}
      <div className="flex items-center gap-2 flex-shrink-0">
        <button
          disabled={!isConnected || (!isIdle && !isPaused) || !selectedInterface}
          onClick={() => isPaused ? onResume() : onStart(selectedInterface)}
          className={`btn ${isConnected && (isIdle || isPaused) && selectedInterface
            ? "btn-primary"
            : "btn-primary opacity-40 cursor-not-allowed"}`}
        >
          <PlayIcon /> Start
        </button>
        <button
          disabled={isIdle}
          onClick={onStop}
          className={`btn ${!isIdle
            ? "btn-danger"
            : "btn-danger opacity-40 cursor-not-allowed"}`}
        >
          <StopIcon /> Stop
        </button>
      </div>

      {/* Separator */}
      <div className="w-px h-5 bg-[var(--border-subtle)]" />

      {/* ── Quick Actions ── */}
      <div className="flex items-center gap-1 text-[var(--text-secondary)] flex-shrink-0">
        <button onClick={onRefreshInterfaces} disabled={!isConnected} className="btn-ghost btn p-2 rounded-lg" title="Refresh interfaces">
          <RefreshIcon />
        </button>
        <button onClick={clearPackets} className="btn-ghost btn p-2 rounded-lg" title="Clear packets">
          <ClearIcon />
        </button>
      </div>

      <div className="w-px h-5 bg-[var(--border-subtle)]" />

      {/* ── Interface Select ── */}
      <div className="flex-shrink-0 flex items-center gap-2">
        <span className="text-[var(--text-muted)] text-[11px] font-medium">Interface</span>
        <select
          value={selectedInterface}
          onChange={(e) => setSelectedInterface(e.target.value)}
          className="bg-[var(--surface-2)] text-[var(--text-primary)] border border-[var(--border-subtle)] font-mono-data px-2.5 py-1.5 outline-none cursor-pointer w-[190px] rounded-lg text-[12px] focus:border-[var(--accent-primary)] focus:ring-1 focus:ring-[var(--accent-dim)] transition-all hover:bg-[var(--surface-3)]"
          disabled={isCapturing || isPaused}
          title="Select network interface"
        >
          {interfaces.length === 0 ? (
            <option value="">No interfaces found</option>
          ) : (
             interfaces.map((iface) => (
              <option key={iface.name} value={iface.name} className="bg-[var(--surface-1)] text-[var(--text-primary)]">
                {iface.display}
              </option>
            ))
          )}
        </select>
      </div>

      <div className="w-px h-5 bg-[var(--border-subtle)]" />

      {/* ── Filter Bar ── */}
      <div className="flex-1 flex items-center relative min-w-0 h-[34px] border border-[var(--border-subtle)] bg-[var(--surface-2)] rounded-lg focus-within:border-[var(--accent-primary)] focus-within:ring-1 focus-within:ring-[var(--accent-dim)] transition-all">
         <div className="pl-3 pr-2 text-[var(--text-muted)]">
            <FilterIcon />
         </div>
         <input
           type="text"
           placeholder="Filter packets (e.g. ip.addr == 192.168.1.1)"
           value={displayFilter}
           onChange={(e) => setDisplayFilter(e.target.value)}
           className="flex-1 bg-transparent border-none outline-none text-[var(--text-primary)] font-mono-data text-[12px] py-1 placeholder-[var(--text-muted)] truncate"
         />
         {displayFilter && (
            <button
               onClick={() => setDisplayFilter('')}
               className="px-3 text-[var(--text-muted)] hover:text-[var(--danger)] transition-colors"
            >
              ✕
            </button>
         )}
      </div>

       <div className="w-px h-5 bg-[var(--border-subtle)]" />
       
       {/* Auto-scroll Toggle */}
       <button
          onClick={toggleAutoScroll}
          className={`flex-shrink-0 pill text-[11px] cursor-pointer transition-all border
            ${autoScroll
              ? "bg-[var(--accent-primary)] text-white border-[var(--accent-primary)]"
              : "bg-[var(--surface-2)] text-[var(--text-tertiary)] border-[var(--border-subtle)] hover:text-[var(--text-secondary)] hover:border-[var(--border-medium)]"}`}
        >
          Auto-scroll
        </button>

    </div>
  );
}
