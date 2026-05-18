"use client";

import React, { useState } from "react";
import Link from "next/link";
import { usePacketCapture } from "../hooks/usePacketCapture";
import Toolbar from "../components/Toolbar";
import PacketTable from "../components/PacketTable";
import PacketDetailPane from "../components/PacketDetailPane";
import HexViewer from "../components/HexViewer";
import Sidebar from "../components/Sidebar";
import SessionTable from "../components/SessionTable";
import SessionDetailPane from "../components/SessionDetailPane";

type ActiveTab = "packets" | "sessions";

export default function Home() {
  const [activeTab, setActiveTab] = useState<ActiveTab>("packets");

  const {
    connectionState,
    startCapture,
    pauseCapture,
    resumeCapture,
    stopCapture,
    refreshInterfaces,
  } = usePacketCapture();

  return (
    <div className="flex flex-col h-screen w-screen bg-[var(--bg-app)] text-[var(--text-primary)] overflow-hidden font-sans">
      
      {/* ── Header ── */}
      <header className="h-12 flex-shrink-0 bg-[var(--surface-1)] flex items-center px-5 border-b border-[var(--border-subtle)]">
        {/* Logo */}
        <div className="flex items-center gap-2.5 w-56">
          <div className="w-7 h-7 rounded-lg bg-[var(--accent-primary)] flex items-center justify-center flex-shrink-0 text-[var(--bg-app)] shadow-[0_0_15px_var(--accent-primary)] border border-[var(--accent-primary)]">
             <svg width="16" height="16" viewBox="0 0 24 24" fill="none"><path d="M12 2L2 7l10 5 10-5-10-5zM2 17l10 5 10-5M2 12l10 5 10-5" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/></svg>
          </div>
          <h1 className="text-sm font-bold tracking-wide text-transparent bg-clip-text bg-gradient-to-r from-[var(--text-primary)] to-[var(--text-secondary)] font-display flex items-center gap-1 drop-shadow-md">
            Net<span className="text-[var(--accent-primary)]">Sentinel</span>
          </h1>
          <span className="text-[10px] font-mono-data text-[var(--accent-primary)] bg-[var(--surface-2)] px-1.5 py-0.5 rounded border border-[var(--accent-primary)]/30 shadow-[0_0_8px_var(--accent-primary)] shadow-opacity-20">v2.1</span>
        </div>

        {/* Tabs */}
        <nav className="flex-1 flex h-full items-end justify-center px-4 gap-1">
          <button
            onClick={() => setActiveTab("packets")}
            className={`px-5 h-9 text-[12px] font-semibold rounded-t-lg border-b-2 transition-all flex items-center gap-2 ${
              activeTab === "packets"
                ? "text-[var(--accent-light)] border-[var(--accent-primary)] bg-[var(--surface-2)]"
                : "text-[var(--text-tertiary)] border-transparent hover:text-[var(--text-secondary)]"
            }`}
          >
            <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M2.5 2v6h13V2l-13 0zM12.5 10v6h9v-6l-9 0zM2.5 18v4h16v-4l-16 0z"/></svg>
            Packets
          </button>
          <button
            onClick={() => setActiveTab("sessions")}
            className={`px-5 h-9 text-[12px] font-semibold rounded-t-lg border-b-2 transition-all flex items-center gap-2 ${
              activeTab === "sessions"
                ? "text-[var(--accent-light)] border-[var(--accent-primary)] bg-[var(--surface-2)]"
                : "text-[var(--text-tertiary)] border-transparent hover:text-[var(--text-secondary)]"
            }`}
          >
            <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M8 6h13M8 12h13M8 18h13M3 6h.01M3 12h.01M3 18h.01"/></svg>
            Sessions
          </button>
          <Link href="/security" className="ml-4 px-5 h-9 text-[12px] font-semibold rounded-t-lg border-b-2 transition-all flex items-center gap-2 text-[var(--danger)] border-[var(--danger)]/30 hover:border-[var(--danger)] bg-[var(--danger)]/5 hover:bg-[var(--surface-2)]">
            <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/></svg>
            Security ML Engine
          </Link>
        </nav>

        {/* Connection Status */}
        <div className="flex items-center gap-3">
          <div className="pill bg-[var(--surface-2)] border border-[var(--border-subtle)]">
            <span className={`h-2 w-2 rounded-full transition-colors ${
              connectionState === 'connected' ? 'bg-[var(--success)] animate-pulse-dot' 
              : connectionState === 'connecting' ? 'bg-[var(--warning)]' 
              : 'bg-[var(--danger)]'
            }`}/>
            <span className="text-[11px] font-medium text-[var(--text-secondary)] font-mono-data">
              {connectionState === 'connected' ? 'LIVE' : connectionState === 'connecting' ? 'INIT...' : 'OFFLINE'}
            </span>
          </div>
        </div>
      </header>

      {/* ── Toolbar ── */}
      <div className="flex-shrink-0 h-12 bg-[var(--surface-1)] border-b border-[var(--border-subtle)] px-5 flex items-center">
        <Toolbar
          connectionState={connectionState}
          onStart={startCapture}
          onPause={pauseCapture}
          onResume={resumeCapture}
          onStop={stopCapture}
          onRefreshInterfaces={refreshInterfaces}
        />
      </div>

      {/* ── Main Workspace ── */}
      <div className="flex-1 flex min-h-0">
        
        {/* Content area */}
        <div className="flex-1 min-w-0 flex flex-col">
          
          {/* ── PACKETS TAB ── */}
          {activeTab === "packets" && (
            <>
              {/* Packet Table */}
              <div className="flex-[3] min-h-[30%] border-b border-[var(--border-subtle)] flex flex-col min-w-0 overflow-hidden">
                <PacketTable />
              </div>

              {/* Bottom: Detail + Hex */}
              <div className="flex-[2] min-h-[25%] flex min-w-0 overflow-hidden">
                
                {/* Detail Tree */}
                <div className="flex-1 min-w-0 flex flex-col border-r border-[var(--border-subtle)]">
                  <div className="h-8 bg-[var(--surface-1)] border-b border-[var(--border-subtle)] flex items-center px-4 gap-2">
                    <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="text-[var(--text-muted)]"><path d="M3 9l9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/><polyline points="9 22 9 12 15 12 15 22"/></svg>
                    <span className="text-[11px] font-medium text-[var(--text-tertiary)]">Packet Details</span>
                  </div>
                  <div className="flex-1 overflow-auto bg-[var(--bg-app)]">
                    <PacketDetailPane />
                  </div>
                </div>

                {/* Hex Dump */}
                <div className="w-[55%] flex-shrink-0 flex flex-col min-w-0">
                  <div className="h-8 bg-[var(--surface-1)] border-b border-[var(--border-subtle)] flex items-center px-4 justify-between">
                    <div className="flex items-center gap-2">
                      <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="text-[var(--text-muted)]"><rect x="3" y="3" width="18" height="18" rx="2"/><path d="M3 9h18M3 15h18M9 3v18"/></svg>
                      <span className="text-[11px] font-medium text-[var(--text-tertiary)]">Hex Dump</span>
                    </div>
                    <span className="text-[10px] text-[var(--text-muted)] font-mono-data">RAW BYTES</span>
                  </div>
                  <div className="flex-1 overflow-auto bg-[var(--bg-app)]">
                    <HexViewer />
                  </div>
                </div>
              </div>
            </>
          )}

          {/* ── SESSIONS TAB ── */}
          {activeTab === "sessions" && (
            <>
              {/* Session Table */}
              <div className="flex-[3] min-h-[30%] border-b border-[var(--border-subtle)] flex flex-col min-w-0 overflow-hidden">
                <SessionTable />
              </div>

              {/* Session Detail */}
              <div className="flex-[2] min-h-[25%] flex flex-col min-w-0 overflow-hidden">
                <div className="h-8 bg-[var(--surface-1)] border-b border-[var(--border-subtle)] flex items-center px-4 gap-2">
                  <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="text-[var(--text-muted)]"><circle cx="12" cy="12" r="10"/><path d="M12 8v4l3 3"/></svg>
                  <span className="text-[11px] font-medium text-[var(--text-tertiary)]">Session Inspector</span>
                </div>
                <div className="flex-1 overflow-auto">
                  <SessionDetailPane />
                </div>
              </div>
            </>
          )}
        </div>

        {/* Right Sidebar */}
        <div className="w-[272px] flex-shrink-0 flex flex-col min-h-0 bg-[var(--surface-1)] border-l border-[var(--border-subtle)]">
          <Sidebar connectionState={connectionState} />
        </div>

      </div>

      {/* ── Status Bar ── */}
      <footer className="h-7 flex-shrink-0 bg-[var(--surface-1)] border-t border-[var(--border-subtle)] flex items-center px-5 justify-between text-[11px] text-[var(--text-muted)] select-none font-mono-data">
         <div className="flex items-center gap-5">
            <span className="flex items-center gap-1.5">
              <span className="w-1.5 h-1.5 rounded-full bg-[var(--info)]"/>
              SYS LOAD: NOMINAL
            </span>
            <span className="flex items-center gap-1.5">
              <span className="w-1.5 h-1.5 rounded-full bg-[var(--success)]"/>
              CAPTURE_THREAD: IDLE
            </span>
         </div>
         <div className="flex items-center gap-4 text-[var(--text-muted)]">
            <span>127.0.0.1 — NetSentinel v2.1</span>
         </div>
      </footer>
    </div>
  );
}
