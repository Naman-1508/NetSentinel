/**
 * Electron Main Process — PacketCapture
 *
 * KEY FIX: Next.js static export uses absolute paths like /_next/static/...
 * These don't work with file:// (/ means filesystem root).
 * We register a custom 'app://' protocol that maps requests to frontend/out/.
 *
 * Dev:  loads http://localhost:3000
 * Prod: starts backend.exe, loads via app://localhost/index.html
 */

const { app, BrowserWindow, dialog, shell, protocol } = require("electron");
const path = require("path");
const { spawn, execSync, spawnSync } = require("child_process");

const isDev = !app.isPackaged;

// ── Custom protocol — MUST be registered before app is ready ─────────────────
// Maps app://localhost/path → frontend/out/path
protocol.registerSchemesAsPrivileged([
    {
        scheme: "app",
        privileges: {
            secure: true,
            standard: true,        // enables absolute URL resolution (/_next/ works)
            supportFetchAPI: true,
            corsEnabled: true,
        },
    },
]);

// ── UAC Admin Elevation (production Windows only) ─────────────────────────────
if (!isDev && process.platform === "win32") {
    let elevated = false;
    try { execSync("net session", { stdio: "ignore" }); elevated = true; } catch { }
    if (!elevated) {
        spawn(
            "powershell.exe",
            ["-Command", `Start-Process -FilePath "${process.execPath}" -Verb RunAs`],
            { detached: true, stdio: "ignore", windowsHide: true }
        ).unref();
        app.exit(0);
    }
}

// ── Globals ───────────────────────────────────────────────────────────────────
let mainWindow = null;
let pythonProcess = null;
let isQuitting = false;

// ── Kill ALL backend.exe processes by image name (handles PyInstaller onefile) ─
// PyInstaller --onefile extracts to a temp dir and spawns a *child* process,
// so the PID we hold is the launcher — the real Python runtime has a different
// PID.  Killing by image name + /T (tree) catches both reliably.
function killBackendByName() {
    if (process.platform !== "win32") return;
    try {
        // /F  = force   /IM = image name   /T = kill whole process tree
        spawnSync("taskkill", ["/F", "/IM", "backend.exe", "/T"], {
            stdio: "ignore",
            windowsHide: true,
        });
    } catch { /* ignore – process may not exist */ }
}

// ── Backend ───────────────────────────────────────────────────────────────────
function startBackend() {
    const backendDir = isDev
        ? path.join(__dirname, "..", "backend")
        : path.join(process.resourcesPath, "backend");

    const cmd = isDev
        ? (process.platform === "win32" ? "python" : "python3")
        : path.join(backendDir, "backend.exe");
    const args = isDev ? [path.join(backendDir, "main.py")] : [];

    // Kill any leftover backend.exe from a previous crashed/killed instance
    // so the port (8765) is free before we start a new one.
    if (!isDev && process.platform === "win32") {
        killBackendByName();
    }

    console.log(`[Electron] Starting backend: ${cmd}`);

    pythonProcess = spawn(cmd, args, {
        cwd: backendDir,
        stdio: ["ignore", "pipe", "pipe"],
        windowsHide: true,
    });
    pythonProcess.stdout.on("data", d => process.stdout.write(`[Backend] ${d}`));
    pythonProcess.stderr.on("data", d => process.stderr.write(`[Backend] ${d}`));
    pythonProcess.on("close", code => {
        console.log(`[Backend] exit ${code}`);
        pythonProcess = null;
        // If we're in the middle of quitting and the backend finally died, finish.
        if (isQuitting) app.exit(0);
    });
    pythonProcess.on("error", err => {
        dialog.showErrorBox("Backend Error",
            `Could not start the capture backend.\n\n${err.message}\n\n` +
            (isDev ? "Ensure Python is installed." : "Try reinstalling the app."));
    });
}

function killBackend() {
    if (pythonProcess) {
        const pid = pythonProcess.pid;
        pythonProcess.removeAllListeners(); // stop our close handler from double-firing
        pythonProcess = null;

        if (pid && process.platform === "win32") {
            // Kill the launcher PID tree first
            try {
                spawnSync("taskkill", ["/F", "/T", "/PID", pid.toString()], {
                    stdio: "ignore",
                    windowsHide: true,
                });
            } catch { }
        } else if (pid) {
            try { process.kill(-pid, "SIGTERM"); } catch { }
        }
    }

    // Also nuke by name — catches any leftover PyInstaller child processes
    killBackendByName();
}

// ── Window ────────────────────────────────────────────────────────────────────
function createWindow() {
    mainWindow = new BrowserWindow({
        width: 1440, height: 900,
        minWidth: 960, minHeight: 600,
        title: "PacketCapture",
        backgroundColor: "#0a0d12",
        webPreferences: {
            preload: path.join(__dirname, "preload.js"),
            nodeIntegration: false,
            contextIsolation: true,
            webSecurity: true,
        },
        show: false,
    });

    if (isDev) {
        // Dev: load from Next.js dev server
        mainWindow.loadURL("http://localhost:3000");
    } else {
        // Production: load via custom protocol so /_next/ paths work
        mainWindow.loadURL("app://localhost/index.html");
    }

    mainWindow.once("ready-to-show", () => mainWindow.show());
    mainWindow.webContents.setWindowOpenHandler(({ url }) => {
        shell.openExternal(url);
        return { action: "deny" };
    });
    mainWindow.on("closed", () => { mainWindow = null; });
}

// ── Lifecycle ─────────────────────────────────────────────────────────────────
app.whenReady().then(() => {
    // Register the custom protocol — maps app://localhost/* → frontend/out/*
    const outDir = path.join(app.getAppPath(), "frontend", "out");
    console.log(`[Electron] Serving frontend from: ${outDir}`);

    protocol.registerFileProtocol("app", (request, callback) => {
        const urlObj = new URL(request.url);
        let filePath = decodeURIComponent(urlObj.pathname);

        // Default: serve index.html for root
        if (!filePath || filePath === "/") filePath = "/index.html";

        const fullPath = path.join(outDir, filePath);
        callback({ path: fullPath });
    });

    startBackend();
    setTimeout(createWindow, 1500);

    app.on("activate", () => {
        if (!BrowserWindow.getAllWindows().length) createWindow();
    });
});

app.on("before-quit", (e) => {
    if (isQuitting) return; // already handled

    if (pythonProcess) {
        // Prevent default quit — we'll call app.exit(0) once backend dies
        e.preventDefault();
        isQuitting = true;
        killBackend();

        // Safety net: force-exit after 3 s even if backend didn't ack
        setTimeout(() => app.exit(0), 3000);
    } else {
        isQuitting = true;
        killBackendByName(); // clean up orphans just in case
    }
});

app.on("window-all-closed", () => {
    if (process.platform !== "darwin") app.quit();
});
