import { create } from "zustand";
import { SessionData, SessionUpdateBatch } from "../types/session";

interface SessionStore {
    // Session dictionaries mapped by session ID
    activeSessions: Record<string, SessionData>;
    closedSessions: Record<string, SessionData>;

    // Arrays for easy UI rendering
    sessionsList: SessionData[];

    // Selected session for detailed view
    selectedSessionId: string | null;
    selectSession: (id: string | null) => void;

    // Actions
    updateSessions: (batch: SessionUpdateBatch) => void;
    clearSessions: () => void;
}

export const useSessionStore = create<SessionStore>((set) => ({
    activeSessions: {},
    closedSessions: {},
    sessionsList: [],

    selectedSessionId: null,
    selectSession: (id) => set({ selectedSessionId: id }),

    updateSessions: (batch) => set((state) => {
        const nextActive = { ...state.activeSessions };
        const nextClosed = { ...state.closedSessions };

        // 1. Process updated/new sessions
        for (const s of batch.updated) {
            nextActive[s.id] = s;
        }

        // 2. Process closed sessions
        for (const s of batch.closed) {
            if (nextActive[s.id]) {
                delete nextActive[s.id];
            }
            nextClosed[s.id] = s;
        }

        // Ensure max session limit to avoid memory leak 
        // We'll keep all active, but cap closed sessions to e.g. 5000.
        const closedKeys = Object.keys(nextClosed);
        if (closedKeys.length > 5000) {
            // Remove the oldest ones (based on start_time or just loosely by key insertion order)
            // Sorting is expensive, we can just slice keys
            const keysToRemove = closedKeys.slice(0, closedKeys.length - 5000);
            for (const k of keysToRemove) {
                delete nextClosed[k];
            }
        }

        // Build combined array for rendering, active first then closed, sorted by last_seen descending
        const combined = [...Object.values(nextActive), ...Object.values(nextClosed)];
        combined.sort((a, b) => b.last_seen - a.last_seen);

        return {
            activeSessions: nextActive,
            closedSessions: nextClosed,
            sessionsList: combined
        };
    }),

    clearSessions: () => set({
        activeSessions: {},
        closedSessions: {},
        sessionsList: [],
        selectedSessionId: null
    })
}));
