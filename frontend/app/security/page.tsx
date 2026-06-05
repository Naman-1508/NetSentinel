"use client";

import React, { useEffect, useState, useRef } from "react";
import Link from "next/link";

interface RiskPrediction {
  timestamp: string;
  session_id: string;
  src_ip: string;
  dst_ip: string;
  src_port: number;
  dst_port: number;
  protocol: string;
  packet_count: number;
  bytes: number;
  duration: number;
  prediction: string;
  binary_prediction?: string;
  risk_score: number;
  explanation?: string;
  correlation_alerts?: { type: string; explanation: string; risk_score: number }[];
}

function getBinaryVerdict(flow: Pick<RiskPrediction, "prediction" | "binary_prediction">): "BENIGN" | "MALICIOUS" {
  const raw = (flow.binary_prediction ?? flow.prediction ?? "").toString().trim().toLowerCase();
  return raw === "benign" ? "BENIGN" : "MALICIOUS";
}

export default function SecurityDashboard() {
  const [flows, setFlows] = useState<RiskPrediction[]>([]);
  const [maliciousFlows, setMaliciousFlows] = useState<RiskPrediction[]>([]);
  const [wsState, setWsState] = useState<"connecting" | "connected" | "disconnected" | "error">("disconnected");
  
  // Stats
  const [totalFlows, setTotalFlows] = useState(0);
  const [maliciousCount, setMaliciousCount] = useState(0);
  const [avgRisk, setAvgRisk] = useState(0);
  
  const wsRef = useRef<WebSocket | null>(null);

  // Initialize and WS connection
  useEffect(() => {
    // 1. Fetch recent flows to populate initial table
    fetch("http://localhost:8000/api/recent-flows")
      .then(res => res.json())
      .then(data => {
        if (Array.isArray(data)) {
          setFlows(data.slice(0, 100));
          const mal = data.filter(f => getBinaryVerdict(f) === "MALICIOUS");
          setMaliciousFlows(mal.slice(0, 500));
          setTotalFlows(data.length);
          setMaliciousCount(mal.length);
          if (data.length > 0) {
            setAvgRisk(data.reduce((acc, f) => acc + f.risk_score, 0) / data.length);
          }
        }
      })
      .catch(err => console.error("Could not fetch recent flows", err));

    // 2. Connect to live WebSocket stream
    const connectWs = () => {
      setWsState("connecting");
      const ws = new WebSocket("ws://localhost:8000/ws/live-flows");
      wsRef.current = ws;

      ws.onopen = () => setWsState("connected");
      
      ws.onmessage = (event) => {
        try {
          const payload = JSON.parse(event.data);
          
          setTotalFlows(prev => prev + 1);
          setAvgRisk(prev => prev * 0.95 + payload.risk_score * 0.05);

          const isMalicious = getBinaryVerdict(payload) === "MALICIOUS";
          
          if (isMalicious) {
             setMaliciousCount(prev => prev + 1);
             setMaliciousFlows(prev => [payload, ...prev].slice(0, 500));
          }

          setFlows(prev => [payload, ...prev].slice(0, 100));
        } catch (e) {
          console.error("Failed to parse ML stream message", e);
        }
      };
      
      ws.onclose = () => {
        setWsState("disconnected");
        // Reconnect after 3s
        setTimeout(connectWs, 3000);
      };
      
      ws.onerror = () => setWsState("error");
    };

    connectWs();

    return () => {
      if (wsRef.current) {
        wsRef.current.onclose = null;
        wsRef.current.close();
      }
    };
  }, []);

  const resetFeed = () => {
    setFlows([]);
    setMaliciousFlows([]);
    setTotalFlows(0);
    setMaliciousCount(0);
    setAvgRisk(0);
  };

  return (
    <div className="flex flex-col h-screen w-screen bg-[var(--bg-app)] text-[var(--text-primary)] overflow-hidden font-sans">
      
      {/* ── Header ── */}
      <header className="h-12 flex-shrink-0 bg-[var(--surface-1)] flex items-center px-5 border-b border-[var(--border-subtle)]">
        <div className="flex items-center gap-2.5 w-56">
          <div className="w-7 h-7 rounded-lg bg-[var(--danger)] flex items-center justify-center flex-shrink-0 text-white shadow-[0_0_15px_var(--danger)] border border-[var(--danger)]">
             <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/></svg>
          </div>
          <h1 className="text-sm font-bold tracking-wide text-transparent bg-clip-text bg-gradient-to-r from-[var(--text-primary)] to-[var(--text-secondary)] font-display flex items-center gap-1 drop-shadow-md">
            NetSentinel <span className="text-[var(--danger)] drop-shadow-[0_0_5px_var(--danger)]">IDS</span>
          </h1>
        </div>

        {/* Tabs */}
        <nav className="flex-1 flex h-full items-end justify-center px-4 gap-1">
          <Link href="/" className="px-5 h-9 text-[12px] font-semibold rounded-t-lg border-b-2 transition-all flex items-center gap-2 text-[var(--text-tertiary)] border-transparent hover:text-[var(--text-secondary)]">
            <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M2.5 2v6h13V2l-13 0zM12.5 10v6h9v-6l-9 0zM2.5 18v4h16v-4l-16 0z"/></svg>
            Capture Studio
          </Link>
          <div className="px-5 h-9 text-[12px] font-semibold rounded-t-lg border-b-2 transition-all flex items-center gap-2 text-[var(--danger)] border-[var(--danger)] bg-[var(--surface-2)]">
            <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/></svg>
            Security ML Engine
          </div>
        </nav>

        {/* ML Status & Controls */}
        <div className="flex items-center gap-3 w-72 justify-end">
          <button 
            onClick={resetFeed}
            className="px-3 py-1 text-[11px] font-semibold rounded bg-[var(--surface-2)] border border-[var(--border-subtle)] text-[var(--text-secondary)] hover:bg-[var(--surface-hover)] hover:text-[var(--text-primary)] transition-colors flex items-center gap-1.5"
            title="Clear all flow history"
          >
            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"><path d="M3 12a9 9 0 1 0 9-9 9.75 9.75 0 0 0-6.74 2.74L3 8"/><path d="M3 3v5h5"/></svg>
            Reset
          </button>
          
          <div className="pill bg-[var(--surface-2)] border border-[var(--border-subtle)]">
            <span className={`h-2 w-2 rounded-full transition-colors ${
              wsState === 'connected' ? 'bg-[var(--success)] animate-pulse-dot' 
              : wsState === 'connecting' ? 'bg-[var(--warning)]' 
              : 'bg-[var(--danger)]'
            }`}/>
            <span className="text-[11px] font-medium text-[var(--text-secondary)] font-mono-data">
              {wsState === 'connected' ? 'ML ENGINE ONLINE' : wsState === 'connecting' ? 'INIT...' : 'ENGINE OFFLINE'}
            </span>
          </div>
        </div>
      </header>

      {/* ── Main Workspace ── */}
      <div className="flex-1 flex min-h-0 bg-[var(--bg-app)] gap-4 p-4">
        
        {/* Left Col: Table */}
        <div className="flex-[3] flex flex-col min-w-0 bg-[var(--surface-1)] border border-[var(--border-subtle)] rounded-xl overflow-hidden shadow-lg">
          <div className="h-12 border-b border-[var(--border-subtle)] flex items-center px-4 justify-between bg-[var(--surface-2)]">
             <h2 className="text-[12px] font-semibold text-[var(--text-primary)] flex items-center gap-2">
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><polyline points="22 12 18 12 15 21 9 3 6 12 2 12"/></svg>
                Live Flow Inspection
             </h2>
             <span className="text-[10px] text-[var(--text-muted)] font-mono-data">SHOWING LAST 100 SESSIONS</span>
          </div>
          
          <div className="flex-1 overflow-auto">
            <table className="w-full text-[11px] font-mono-data text-left">
               <thead className="bg-[var(--surface-2)] text-[var(--text-tertiary)] sticky top-0 z-10 border-b border-[var(--border-subtle)]">
                 <tr>
                   <th className="py-2.5 px-3 font-medium tracking-wide">Flow Key</th>
                   <th className="py-2.5 px-3 font-medium tracking-wide">Protocol</th>
                   <th className="py-2.5 px-3 font-medium tracking-wide text-right">Packets</th>
                   <th className="py-2.5 px-3 font-medium tracking-wide text-right">Bytes</th>
                   <th className="py-2.5 px-4 font-medium tracking-wide text-center">ML Prediction</th>
                 </tr>
               </thead>
               <tbody>
                  {flows.length === 0 && (
                     <tr><td colSpan={5} className="text-center py-8 text-[var(--text-muted)]">No flows inspected yet.</td></tr>
                  )}
                  {flows.map((f, i) => (
                    (() => {
                      const verdict = getBinaryVerdict(f);
                      const isMalicious = verdict === "MALICIOUS";
                      return (
                    <tr key={f.session_id + i} className="border-b border-[var(--border-subtle)]/50 hover:bg-[var(--surface-hover)]">
                       <td className="py-2.5 px-3">
                         <div className="text-[var(--text-primary)]">{f.src_ip}<span className="text-[var(--text-muted)]">:{f.src_port || '*'}</span></div>
                         <div className="text-[var(--text-secondary)] mt-0.5">→ {f.dst_ip}<span className="text-[var(--text-muted)]">:{f.dst_port || '*'}</span></div>
                       </td>
                       <td className="py-2.5 px-3">
                          <span className="pill text-[9px] bg-[var(--surface-2)] border border-[var(--border-subtle)]">{f.protocol}</span>
                       </td>
                       <td className="py-2.5 px-3 text-right text-[var(--text-secondary)]">{f.packet_count.toLocaleString()}</td>
                       <td className="py-2.5 px-3 text-right text-[var(--text-secondary)]">{f.bytes.toLocaleString()}</td>
                       <td className="py-2.5 px-4">
                          <div className="flex items-center justify-center gap-2">
                              <div className={`px-2 py-0.5 rounded text-[10px] font-semibold ${
                              isMalicious ? 'bg-[var(--danger)]/15 text-[var(--danger)] border border-[var(--danger)]/30' : 'bg-[var(--success)]/15 text-[var(--success)] border border-[var(--success)]/30'
                              }`}>
                              {verdict}
                             </div>
                             <div className="text-[9px] text-[var(--text-secondary)]">{(f.risk_score * 100).toFixed(0)}%</div>
                             <div className="w-10 h-1.5 bg-[var(--surface-2)] rounded-full overflow-hidden">
                              <div className={`h-full ${isMalicious ? 'bg-[var(--danger)]' : 'bg-[var(--success)]'}`} style={{ width: `${f.risk_score * 100}%` }}/>
                             </div>
                          </div>
                       </td>
                    </tr>
                       );
                      })()
                  ))}
               </tbody>
            </table>
          </div>
        </div>

        {/* Right Col: Stats & Alerts */}
        <div className="flex-1 flex flex-col min-w-0 min-w-[320px] gap-4">
          
          {/* Quick Stats Grid */}
          <div className="grid grid-cols-2 gap-3">
            <div className="card p-3">
               <div className="text-[10px] text-[var(--text-muted)] font-mono-data tracking-wider uppercase mb-2">Total Analyzed</div>
               <div className="text-2xl font-display font-semibold text-[var(--text-primary)]">{totalFlows}</div>
            </div>
            <div className="card p-3 border-[var(--danger)] shadow-[0_0_15px_rgba(244,63,94,0.06)]">
               <div className="text-[10px] text-[var(--danger)] font-mono-data tracking-wider uppercase mb-2">Malicious Count</div>
               <div className="text-2xl font-display font-semibold text-[var(--danger)]">{maliciousCount}</div>
            </div>
          </div>

          <div className="card p-3">
             <div className="text-[10px] text-[var(--text-muted)] font-mono-data tracking-wider uppercase mb-2">System Risk Level (AvG)</div>
             <div className="flex items-center gap-3">
                <div className="text-3xl font-display font-semibold text-[var(--text-primary)]">{(avgRisk * 100).toFixed(1)}%</div>
                <div className="flex-1 h-2 bg-[var(--surface-2)] rounded-full overflow-hidden">
                   <div className="h-full bg-gradient-to-r from-[var(--success)] to-[var(--danger)]" style={{ width: `${avgRisk * 100}%` }}/>
                </div>
             </div>
          </div>

           {/* Prediction Feed */}
          <div className="flex-1 card flex flex-col min-h-0 bg:[var(--surface-1)]">
             <div className="h-10 border-b border-[var(--danger)]/30 flex items-center px-4 bg-[var(--danger)]/5 text-[var(--danger)] font-semibold text-[11px] uppercase tracking-wider">
               <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3" className="mr-2"><path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/></svg>
              ML Verdict Feed
             </div>
             <div className="flex-1 overflow-auto p-2 space-y-2">
               {maliciousFlows.length === 0 && (
                   <div className="text-center p-4 text-[var(--text-muted)] text-xs mt-4">
                   No malicious flows received yet.
                   </div>
                )}
                {maliciousFlows.map((f, i) => (
                  (() => {
                    const verdict = getBinaryVerdict(f);
                    return (
                   <div key={i} className="bg-[var(--surface-2)] border border-[var(--danger)]/20 p-2.5 rounded-lg flex flex-col gap-1 shadow-sm">
                      <div className="flex justify-between items-start">
                     <span className={`text-[10px] font-mono-data font-bold text-[var(--danger)]`}>
                      MALICIOUS FLOW
                     </span>
                         <span className="text-[9px] text-[var(--text-muted)] font-mono-data uppercase">{(f.risk_score * 100).toFixed(0)}% CONFIDENCE</span>
                      </div>
                      <div className="text-[11px] font-mono-data text-[var(--text-primary)] mt-1">
                         {f.src_ip} <span className="text-[var(--text-tertiary)] hover:text-white transition-colors">→</span> {f.dst_ip}
                      </div>
                      <div className="flex gap-2 mt-1">
                         <span className="pill text-[8px] bg-transparent border border-[var(--border-subtle)] text-[var(--text-secondary)]">{f.protocol} / {f.bytes}B</span>
                         <span className={`pill text-[8px] bg-[var(--danger)]/10 border border-[var(--danger)]/30 text-[var(--danger)]`}>
                           {verdict}
                         </span>
                      </div>
                      
                      <div className="mt-2 pt-2 border-t border-[var(--border-subtle)]/50 text-[10px] text-[var(--text-secondary)]">
                        Binary verdict: {verdict}
                      </div>
                   </div>
                    );
                  })()
                 ))}
              </div>
          </div>

        </div>
      </div>
    </div>
  );
}
