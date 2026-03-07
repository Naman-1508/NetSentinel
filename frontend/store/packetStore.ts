import { create } from "zustand";
import {
    PacketData,
    CaptureStats,
    CaptureState,
    NetworkInterface,
    MAX_PACKETS,
} from "../types/packet";

const ZERO_STATS: CaptureStats = { total: 0, tcp: 0, udp: 0, icmp: 0 };

interface PacketStore {
    // Packets
    packets: PacketData[];
    addPackets: (newPackets: PacketData[]) => void;
    clearPackets: () => void;

    // Selection
    selectedPacket: PacketData | null;
    selectPacket: (pkt: PacketData | null) => void;

    // Stats — displayed to user (= raw backend stats minus offset set at last clear)
    stats: CaptureStats;
    statsOffset: CaptureStats;   // snapshot at last clear
    setStats: (raw: CaptureStats) => void;
    resetStats: () => void;

    // Capture state
    captureState: CaptureState;
    setCaptureState: (s: CaptureState) => void;

    // Interfaces
    interfaces: NetworkInterface[];
    defaultInterface: string;
    selectedInterface: string;
    setInterfaces: (ifaces: NetworkInterface[], defaultIface: string) => void;
    setSelectedInterface: (iface: string) => void;

    // Auto-scroll
    autoScroll: boolean;
    toggleAutoScroll: () => void;

    // Packet rate
    packetRate: number;
    setPacketRate: (rate: number) => void;

    // Filters
    bpfFilter: string;
    setBpfFilter: (filter: string) => void;
    displayFilter: string;
    setDisplayFilter: (filter: string) => void;
}

export const usePacketStore = create<PacketStore>((set) => ({
    // Packets
    packets: [],
    addPackets: (newPackets) =>
        set((state) => {
            const combined = [...state.packets, ...newPackets];
            const sliced =
                combined.length > MAX_PACKETS
                    ? combined.slice(combined.length - MAX_PACKETS)
                    : combined;
            return { packets: sliced };
        }),

    // Clear: snapshot current raw stats as offset so future backend updates
    // are displayed relative to 0 again.
    clearPackets: () => {
        set((state) => ({
            packets: [],
            selectedPacket: null,
            packetRate: 0,
            statsOffset: {
                total: state.stats.total + state.statsOffset.total,
                tcp: state.stats.tcp + state.statsOffset.tcp,
                udp: state.stats.udp + state.statsOffset.udp,
                icmp: state.stats.icmp + state.statsOffset.icmp,
            },
            stats: { ...ZERO_STATS },
        }));
    },

    // Selection
    selectedPacket: null,
    selectPacket: (pkt) => set({ selectedPacket: pkt }),

    // Stats — subtract clear offset so counter shows 0 after Clear
    stats: { ...ZERO_STATS },
    statsOffset: { ...ZERO_STATS },
    setStats: (raw) =>
        set((state) => ({
            stats: {
                total: Math.max(0, raw.total - state.statsOffset.total),
                tcp: Math.max(0, raw.tcp - state.statsOffset.tcp),
                udp: Math.max(0, raw.udp - state.statsOffset.udp),
                icmp: Math.max(0, raw.icmp - state.statsOffset.icmp),
            },
        })),
    // Reset both stats and offset to zero for a fresh capture session
    resetStats: () => set({ stats: { ...ZERO_STATS }, statsOffset: { ...ZERO_STATS } }),

    // Capture state
    captureState: "idle",
    setCaptureState: (s) => set({ captureState: s }),

    // Interfaces — keep selected interface if it still exists in the refreshed list
    interfaces: [],
    defaultInterface: "",
    selectedInterface: "",
    setInterfaces: (ifaces, defaultIface) =>
        set((state) => ({
            interfaces: ifaces,
            defaultInterface: defaultIface,
            // Keep current selection if it's still in the new list, else use default
            selectedInterface: ifaces.some((i) => i.name === state.selectedInterface)
                ? state.selectedInterface
                : defaultIface,
        })),
    setSelectedInterface: (iface) => set({ selectedInterface: iface }),

    // Auto-scroll
    autoScroll: true,
    toggleAutoScroll: () => set((s) => ({ autoScroll: !s.autoScroll })),

    // Packet rate
    packetRate: 0,
    setPacketRate: (rate) => set({ packetRate: rate }),

    // Filters
    bpfFilter: "",
    setBpfFilter: (f) => set({ bpfFilter: f }),
    displayFilter: "",
    setDisplayFilter: (f) => set({ displayFilter: f }),
}));
