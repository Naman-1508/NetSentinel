# ============================================================
# NetSentinel - One-click Build Script
# Builds: frontend -> single PyInstaller exe -> NSIS installer
# Run from repo root as Administrator
# ============================================================

$ErrorActionPreference = "Stop"
$Root = $PSScriptRoot

Write-Host ""
Write-Host "=====================================================" -ForegroundColor Cyan
Write-Host "  NetSentinel Full Build Pipeline" -ForegroundColor Cyan
Write-Host "=====================================================" -ForegroundColor Cyan
Write-Host ""

# ---- Step 1: Build Next.js frontend (static export) --------
Write-Host "[1/3] Building Next.js frontend..." -ForegroundColor Yellow
Set-Location "$Root\frontend"
npm run build
if ($LASTEXITCODE -ne 0) { Write-Error "Frontend build failed!"; exit 1 }
Write-Host '  Frontend built -> frontend\out' -ForegroundColor Green

# ---- Step 2: PyInstaller - single NetSentinel.exe ----------
Write-Host ""
Write-Host "[2/3] Compiling NetSentinel.exe with PyInstaller..." -ForegroundColor Yellow
Set-Location "$Root\backend"

# Attempt to stop any running NetSentinel process so logs can be removed
try {
    $running = Get-Process -Name NetSentinel -ErrorAction SilentlyContinue
    if ($running) {
        Write-Host "Stopping running NetSentinel process(es)..." -ForegroundColor Yellow
        $running | Stop-Process -Force -ErrorAction SilentlyContinue
        Start-Sleep -Seconds 1
    }
} catch {
    Write-Host "Warning: Unable to query/stop NetSentinel processes: $($_.Exception.Message)" -ForegroundColor Yellow
}

# Clean previous build to avoid stale cache issues (retry if locked)
if (Test-Path "build") {
    try { Remove-Item -Recurse -Force "build" -ErrorAction Stop } catch { Write-Host "Warning: failed to remove build: $($_.Exception.Message)" -ForegroundColor Yellow }
}

if (Test-Path "dist") {
    $tries = 0
    while ($tries -lt 5 -and (Test-Path "dist")) {
        try {
            Remove-Item -Recurse -Force "dist" -ErrorAction Stop
            break
        } catch {
            Write-Host "Warning: failed to remove dist (attempt $($tries+1)): $($_.Exception.Message)" -ForegroundColor Yellow
            Start-Sleep -Seconds 1
            $tries++
        }
    }
    if (Test-Path "dist") {
        Write-Host "Could not remove dist directory after retries. Continuing build - old files may remain." -ForegroundColor Yellow
    }
}

pyinstaller backend.spec -y
if ($LASTEXITCODE -ne 0) { Write-Error "PyInstaller build failed!"; exit 1 }
Write-Host '  NetSentinel.exe built -> backend\dist\NetSentinel.exe' -ForegroundColor Green

# ---- Step 3: NSIS installer --------------------------------
Write-Host ""
Write-Host "[3/3] Creating NSIS installer..." -ForegroundColor Yellow
Set-Location "$Root"

# Check if NSIS is installed
$makensis = Get-Command makensis -ErrorAction SilentlyContinue
if (-not $makensis) {
    # Try default install path
    $nsisPaths = @(
        "C:\Program Files (x86)\NSIS\makensis.exe",
        "C:\Program Files\NSIS\makensis.exe"
    )
    foreach ($p in $nsisPaths) {
        if (Test-Path $p) { $makensis = $p; break }
    }
}

if (-not $makensis) {
    Write-Host "  WARNING: NSIS not found. Skipping installer creation." -ForegroundColor Red
    Write-Host "  Install NSIS from https://nsis.sourceforge.io/" -ForegroundColor Red
    Write-Host "  Then run: makensis installer\NetSentinel.nsi" -ForegroundColor Yellow
} else {
    $nsisBin = if ($makensis -is [string]) { $makensis } else { $makensis.Source }
    & $nsisBin "installer\NetSentinel.nsi"
    if ($LASTEXITCODE -ne 0) { Write-Error "NSIS build failed!"; exit 1 }
    Write-Host '  Installer created -> backend\dist\NetSentinel-Setup.exe' -ForegroundColor Green
}

Write-Host ''
Write-Host '=====================================================' -ForegroundColor Cyan
Write-Host '  BUILD COMPLETE!' -ForegroundColor Green
Write-Host '=====================================================' -ForegroundColor Cyan
Write-Host ''
Write-Host '  Executable :  backend\dist\NetSentinel.exe'
Write-Host '  Installer  :  backend\dist\NetSentinel-Setup.exe'
Write-Host ''
