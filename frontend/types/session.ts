import { Protocol } from "./packet";

export interface SessionData {
    id: string; // The 5-tuple key
    src_ip: string;
    dst_ip: string;
    src_port: number | null;
    dst_port: number | null;
    protocol: Protocol;
    packet_count: number;
    bytes: number;
    start_time: number; // Unix timestamp in seconds
    last_seen: number;  // Unix timestamp in seconds
    duration: number;   // Duration in seconds
    syn_count: number;
    ack_count: number;
    fin_count: number;
    rst_count: number;
    status: "Active" | "Closed";
    packet_rate: number; // Packets per second
    byte_rate: number;   // Bytes per second
}

export interface SessionUpdateBatch {
    updated: SessionData[];
    closed: SessionData[];
}
