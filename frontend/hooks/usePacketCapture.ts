"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { WsMessage, WsControlMessage, WS_URL } from "../types/packet";
import { usePacketStore } from "../store/packetStore";
import { useSessionStore } from "../store/sessionStore";

export type WsConnectionState =
    | "connecting"
    | "connected"
    | "disconnected"
    | "error";

const RECONNECT_DELAY_MS = 3000;

export function usePacketCapture() {
    const wsRef = useRef<WebSocket | null>(null);
    const reconnectTimer = useRef<ReturnType<typeof setTimeout> | null>(null);
    const [connectionState, setConnectionState] =
        useState<WsConnectionState>("disconnected");

    const {
        addPackets,
        setStats,
        setCaptureState,
        setInterfaces,
        setPacketRate,
    } = usePacketStore();

    const { updateSessions } = useSessionStore();

    // Packet rate tracking
    const lastCountRef = useRef(0);
    const lastTimeRef = useRef(Date.now());

    const sendMessage = useCallback((msg: WsControlMessage) => {
        if (wsRef.current?.readyState === WebSocket.OPEN) {
            wsRef.current.send(JSON.stringify(msg));
        }
    }, []);

    const connect = useCallback(() => {
        if (
            wsRef.current &&
            (wsRef.current.readyState === WebSocket.OPEN ||
                wsRef.current.readyState === WebSocket.CONNECTING)
        ) {
            return;
        }

        setConnectionState("connecting");
        const ws = new WebSocket(WS_URL);
        wsRef.current = ws;

        ws.onopen = () => {
            setConnectionState("connected");
            if (reconnectTimer.current) {
                clearTimeout(reconnectTimer.current);
                reconnectTimer.current = null;
            }
        };

        ws.onmessage = (event) => {
            try {
                const msg: WsMessage = JSON.parse(event.data as string);
                handleMessage(msg);
            } catch (e) {
                console.error("WS parse error:", e);
            }
        };

        ws.onerror = () => {
            setConnectionState("error");
        };

        ws.onclose = () => {
            setConnectionState("disconnected");
            wsRef.current = null;
            // Auto-reconnect
            reconnectTimer.current = setTimeout(() => {
                connect();
            }, RECONNECT_DELAY_MS);
        };
    }, []); // eslint-disable-line react-hooks/exhaustive-deps

    const handleMessage = useCallback(
        (msg: WsMessage) => {
            switch (msg.type) {
                case "interfaces":
                    setInterfaces(msg.data, msg.default);
                    break;
                case "packets": {
                    addPackets(msg.data);
                    // Update packet rate
                    const now = Date.now();
                    const elapsed = (now - lastTimeRef.current) / 1000;
                    if (elapsed >= 1) {
                        const store = usePacketStore.getState();
                        const diff = store.stats.total - lastCountRef.current;
                        setPacketRate(Math.round(diff / elapsed));
                        lastCountRef.current = store.stats.total;
                        lastTimeRef.current = now;
                    }
                    break;
                }
                case "stats":
                    setStats(msg.data);
                    break;
                case "status":
                    setCaptureState(msg.state);
                    break;
                case "error":
                    console.error("Server error:", msg.message);
                    break;
                case "sessions":
                    updateSessions(msg.data);
                    break;
            }
        },
        [addPackets, setStats, setCaptureState, setInterfaces, setPacketRate, updateSessions]
    );

    // Connect on mount, cleanup on unmount
    useEffect(() => {
        connect();
        return () => {
            if (reconnectTimer.current) clearTimeout(reconnectTimer.current);
            if (wsRef.current) {
                wsRef.current.onclose = null; // prevent reconnect on intentional close
                wsRef.current.close();
            }
        };
    }, [connect]);

    const startCapture = useCallback(
        (iface: string) => {
            useSessionStore.getState().clearSessions();
            usePacketStore.getState().resetStats();
            usePacketStore.getState().clearPackets();
            sendMessage({ type: "start", interface: iface });
        },
        [sendMessage]
    );

    const pauseCapture = useCallback(() => {
        sendMessage({ type: "pause" });
    }, [sendMessage]);

    const resumeCapture = useCallback(() => {
        sendMessage({ type: "resume" });
    }, [sendMessage]);

    const stopCapture = useCallback(() => {
        sendMessage({ type: "stop" });
    }, [sendMessage]);

    const refreshInterfaces = useCallback(() => {
        sendMessage({ type: "get_interfaces" });
    }, [sendMessage]);

    return {
        connectionState,
        startCapture,
        pauseCapture,
        resumeCapture,
        stopCapture,
        refreshInterfaces,
    };
}
