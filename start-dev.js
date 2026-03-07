const { spawn } = require("child_process");
const http = require("http");

const isWin = process.platform === "win32";
const npmCmd = isWin ? "npm.cmd" : "npm";
const pythonCmd = isWin ? "python" : "python3";

function waitForServer(url, timeout = 30000) {
    return new Promise((resolve, reject) => {
        const startTime = Date.now();
        const interval = setInterval(() => {
            if (Date.now() - startTime > timeout) {
                clearInterval(interval);
                reject(new Error("Timeout waiting for Next.js server"));
            }
            http.get(url, (res) => {
                if (res.statusCode === 200) {
                    clearInterval(interval);
                    resolve();
                }
            }).on("error", () => { });
        }, 1000);
    });
}

console.log("Starting Next.js frontend...");
const nextProcess = spawn(npmCmd, ["run", "dev"], {
    cwd: "frontend",
    stdio: "inherit",
    shell: isWin
});

waitForServer("http://localhost:3000")
    .then(() => {
        console.log("Next.js ready. Launching Python backend and ML Risk Engine...");

        // 1. Launch DeepShark Backend
        const pyProcess = spawn(pythonCmd, ["main.py", "--dev"], {
            cwd: "backend",
            stdio: "inherit",
            shell: isWin
        });

        // 2. Launch ML Risk Engine
        const mlCmd = isWin ? "uvicorn" : "uvicorn"; // pip installs uvicorn to path
        const mlProcess = spawn(mlCmd, ["api.server:app", "--port", "8000", "--host", "127.0.0.1"], {
            cwd: "ml_risk_engine", // Run from inside ML directory to fix python imports
            stdio: "inherit",
            shell: isWin
        });

        pyProcess.on("close", () => {
            console.log("Backend closed. Exiting...");
            mlProcess.kill();
            nextProcess.kill();
            process.exit(0);
        });

        mlProcess.on("close", () => {
            console.log("ML Engine closed.");
        });
    })
    .catch((err) => {
        console.error("Failed to start:", err);
        nextProcess.kill();
        process.exit(1);
    });

process.on("SIGINT", () => {
    nextProcess.kill();
    // Assuming python processes will be killed by SIGINT too, 
    // but try/catch kill them just in case if variables were at root scope
    process.exit(0);
});
