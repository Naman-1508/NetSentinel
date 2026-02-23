/**
 * Electron Preload Script
 *
 * Runs in the renderer process with Node.js access but exposes
 * only what's needed via contextBridge (currently nothing extra
 * since the app communicates via WebSocket, not IPC).
 */

const { contextBridge } = require("electron");

// Expose a minimal API surface if needed in the future
contextBridge.exposeInMainWorld("electronAPI", {
    platform: process.platform,
});
