# Build NetSentinel — Full Production Build Script
# Run this from the root of the project as Administrator
# Usage: powershell -ExecutionPolicy Bypass -File build-installer.ps1

$ErrorActionPreference = "Stop"
$ROOT = Split-Path -Parent $MyInvocation.MyCommand.Path

function Log($msg) { Write-Host "[BUILD] $msg" -ForegroundColor Cyan }
function Err($msg) { Write-Host "[ERROR] $msg" -ForegroundColor Red; exit 1 }

# ─── 1. Find NSIS ───────────────────────────────────────────────────────────
$nsisPath = $null
$candidates = @(
    "C:\Program Files (x86)\NSIS\makensis.exe",
    "C:\Program Files\NSIS\makensis.exe",
    "$env:LOCALAPPDATA\Programs\NSIS\makensis.exe"
)
foreach ($p in $candidates) { if (Test-Path $p) { $nsisPath = $p; break } }
if (-not $nsisPath) {
    # Try PATH
    $found = Get-Command makensis -ErrorAction SilentlyContinue
    if ($found) { $nsisPath = $found.Source }
}
if (-not $nsisPath) { Err "NSIS not found. Install from https://nsis.sourceforge.io/" }
Log "NSIS found: $nsisPath"

# ─── 2. Build Backend (PyInstaller) ─────────────────────────────────────────
Log "Building Python backend with PyInstaller..."
Set-Location "$ROOT\backend"
python -m PyInstaller backend.spec --distpath dist --workpath build --noconfirm
if ($LASTEXITCODE -ne 0) { Err "Backend build failed!" }
Log "Backend built: backend\dist\backend.exe"

# ─── 3. Build ML Risk Engine (PyInstaller) ──────────────────────────────────
Log "Building ML Risk Engine with PyInstaller..."
Set-Location "$ROOT\ml_risk_engine"
python -m PyInstaller ml_engine.spec --noconfirm
if ($LASTEXITCODE -ne 0) { Err "ML Engine build failed!" }
Log "ML Engine built: ml_risk_engine\dist\ml_engine\"

# ─── 4. Build Frontend (Next.js static export) ──────────────────────────────
Log "Building Next.js frontend..."
Set-Location "$ROOT\frontend"
npm run build
if ($LASTEXITCODE -ne 0) { Err "Frontend build failed!" }
Log "Frontend built: frontend\out\"

# ─── 5. Verify artifacts exist ──────────────────────────────────────────────
Set-Location $ROOT
if (-not (Test-Path "backend\dist\NetSentinel.exe")) { Err "Missing backend\dist\NetSentinel.exe" }
if (-not (Test-Path "ml_risk_engine\dist\ml_engine\ml_engine.exe")) { Err "Missing ml_risk_engine\dist\ml_engine\ml_engine.exe" }
if (-not (Test-Path "frontend\out\index.html"))  { Err "Missing frontend\out\index.html" }
Log "Artifacts verified."

# ─── 5. Run NSIS Installer Compilation ──────────────────────────────────────
Log "Compiling NSIS installer..."
& $nsisPath installer.nsi
if ($LASTEXITCODE -ne 0) { Err "NSIS compilation failed!" }

$exePath = Join-Path $ROOT "NetSentinel-Setup-1.0.0.exe"
if (Test-Path $exePath) {
    $size = [math]::Round((Get-Item $exePath).Length / 1MB, 2)
    Log "SUCCESS! NetSentinel installer created: $exePath ($size MB)"
} else {
    Err "Installer EXE not found after build!"
}
