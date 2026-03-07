"use client";

import React, { useMemo } from "react";
import { usePacketStore } from "../store/packetStore";

const BYTES_PER_ROW = 16;

function generateMockHex(seed: number, length: number): Uint8Array {
  const buf = new Uint8Array(Math.min(length, 256));
  let x = seed * 1664525 + 1013904223;
  for (let i = 0; i < buf.length; i++) {
    x = (x * 1664525 + 1013904223) >>> 0;
    buf[i] = x & 0xff;
  }
  return buf;
}

function toHex(byte: number) {
  return byte.toString(16).padStart(2, "0");
}

function toAscii(byte: number) {
  return byte >= 0x20 && byte <= 0x7e ? String.fromCharCode(byte) : ".";
}

export default function HexViewer() {
  const pkt = usePacketStore((s) => s.selectedPacket);

  const bytes = useMemo(() => {
    if (!pkt) return null;
    return generateMockHex(pkt.id, pkt.length);
  }, [pkt]);

  if (!pkt || !bytes) {
    return (
      <div className="flex items-center justify-center h-full text-[var(--text-muted)] font-mono-data p-4">
        <span className="text-[13px]">No packet selected</span>
      </div>
    );
  }

  const rows: Array<{ offset: number; hex: string[]; ascii: string[] }> = [];
  for (let i = 0; i < bytes.length; i += BYTES_PER_ROW) {
    const slice = bytes.slice(i, i + BYTES_PER_ROW);
    rows.push({
      offset: i,
      hex: Array.from(slice).map(toHex),
      ascii: Array.from(slice).map(toAscii),
    });
  }

  return (
    <div className="h-full overflow-auto bg-[var(--bg-app)] text-[var(--text-secondary)] p-4 select-text font-mono-data text-[11px] leading-[1.7]">
      <div className="flex flex-col">
        {rows.map((row) => {
          const paddedHex = [...row.hex];
          while (paddedHex.length < BYTES_PER_ROW) paddedHex.push("  ");

          return (
            <div
              key={row.offset}
              className="flex items-center hover:bg-[var(--surface-hover)] rounded transition-colors"
            >
              {/* Offset */}
              <div className="w-12 flex-shrink-0 text-[var(--text-muted)] select-none">
                {row.offset.toString(16).padStart(4, "0")}
              </div>

              {/* Hex bytes */}
              <div className="flex-1 flex text-[var(--text-primary)] ml-4 pr-8">
                <div className="flex gap-2 w-[140px]">
                  {paddedHex.slice(0, 8).map((h, i) => (
                    <span key={i} className="w-[14px] text-center">
                      {h}
                    </span>
                  ))}
                </div>
                
                <div className="flex gap-2 w-[140px] ml-4">
                  {paddedHex.slice(8, 16).map((h, i) => (
                    <span key={i} className="w-[14px] text-center">
                      {h}
                    </span>
                  ))}
                </div>
              </div>

              {/* ASCII */}
              <div className="flex-shrink-0 flex text-[var(--text-tertiary)] ml-4 tracking-widest">
                {row.ascii.map((ch, i) => (
                  <span
                    key={i}
                    className={ch === "." ? "text-[var(--text-muted)]" : "text-[var(--accent-light)]"}
                  >
                    {ch}
                  </span>
                ))}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
