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
        console.log("Next.js ready. Launching Python backend...");
        const pyProcess = spawn(pythonCmd, ["main.py", "--dev"], {
            cwd: "backend",
            stdio: "inherit",
            shell: isWin
        });

        pyProcess.on("close", () => {
            console.log("Backend closed. Exiting...");
            nextProcess.kill();
            process.exit(0);
        });
    })
    .catch((err) => {
        console.error("Failed to start:", err);
        nextProcess.kill();
        process.exit(1);
    });

process.on("SIGINT", () => {
    nextProcess.kill();
    process.exit(0);
});
