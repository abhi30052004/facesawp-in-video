# ==============================================================================
# BollySwap AI — Production-Grade Local Node Startup Script (PowerShell)
# Powered exclusively by FaceFusion 3.9.2 (Ghost 256 ONNX, CPUExecutionProvider)
# ==============================================================================
[CmdletBinding()]
param(
    [string]$HostAddress = "127.0.0.1",
    [int]$Port = 8001,
    [string]$AccessKey = "",
    [switch]$Tunnel = $false
)

$ErrorActionPreference = "Stop"

Write-Host ""
Write-Host "==================================================================" -ForegroundColor Cyan
Write-Host "       BollySwap AI Studio — FaceFusion 3.9.2 Node Startup        " -ForegroundColor Yellow
Write-Host "==================================================================" -ForegroundColor Cyan
Write-Host ""

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Definition
Set-Location $ScriptDir

# 1. Resolve Python Virtual Environment
$VenvPython = Join-Path $ScriptDir "backend\.venv\Scripts\python.exe"
if (-not (Test-Path $VenvPython)) {
    Write-Warning "Local virtual environment not found at backend\.venv. Checking PATH python..."
    $VenvPython = (Get-Command python -ErrorAction SilentlyContinue).Source
    if (-not $VenvPython) {
        Write-Error "Python 3.12+ is required. Please create backend\.venv first."
        exit 1
    }
}
Write-Host "[✓] Python executable : $VenvPython" -ForegroundColor Green

# 2. Configure Dynamic Directories (No Personal Hardcoded Paths)
if (-not $env:FACEFUSION_DIR) {
    $env:FACEFUSION_DIR = Join-Path $ScriptDir "facefusion"
}
if (-not $env:FACEFUSION_MODEL_DIR) {
    $env:FACEFUSION_MODEL_DIR = Join-Path $env:FACEFUSION_DIR ".assets\models"
}
if (-not $env:STORAGE_DIR) {
    $env:STORAGE_DIR = Join-Path $ScriptDir "storage"
}
if ($AccessKey) {
    $env:API_ACCESS_KEY = $AccessKey
}
if (-not $env:MAX_ACTIVE_SWAP_JOBS) {
    $env:MAX_ACTIVE_SWAP_JOBS = "2"
}

Write-Host "[✓] FaceFusion Dir    : $env:FACEFUSION_DIR" -ForegroundColor Green
Write-Host "[✓] Models Cache Dir  : $env:FACEFUSION_MODEL_DIR" -ForegroundColor Green
Write-Host "[✓] Media Storage Dir : $env:STORAGE_DIR" -ForegroundColor Green
Write-Host "[✓] Active Concurrency: $env:MAX_ACTIVE_SWAP_JOBS jobs max" -ForegroundColor Green

if ($env:API_ACCESS_KEY) {
    Write-Host "[✓] Access Protection : ENABLED (X-API-Key required)" -ForegroundColor Yellow
} else {
    Write-Host "[i] Access Protection : OPEN (Local demo mode)" -ForegroundColor DarkGray
}

# 3. Verify Pre-Trained Ghost Model Weights
$GhostModel = Join-Path $env:FACEFUSION_MODEL_DIR "ghost_1_256.onnx"
if (-not (Test-Path $GhostModel)) {
    Write-Warning "Ghost 256 model missing at $GhostModel. Running pre-fetch..."
    & $VenvPython -c "import sys; sys.path.insert(0, '$($env:FACEFUSION_DIR.Replace('\', '/'))'); from facefusion.processors.modules.face_swapper import pre_check; pre_check()"
} else {
    $GhostSizeMb = [math]::Round((Get-Item $GhostModel).Length / 1MB, 2)
    Write-Host "[✓] Ghost 256 Model   : Valid ($GhostSizeMb MB, Apache-2.0)" -ForegroundColor Green
}

# 4. Optional Cloudflare Tunnel Guidance
if ($Tunnel) {
    Write-Host ""
    Write-Host "To expose this processing node securely to your Vercel deployment without port forwarding:" -ForegroundColor Cyan
    Write-Host "  Run in a separate PowerShell window:" -ForegroundColor White
    Write-Host "    cloudflared tunnel --url http://$HostAddress`:$Port" -ForegroundColor Yellow
    Write-Host "  Then set PUBLIC_BACKEND_URL in .env to the issued https://*.trycloudflare.com URL." -ForegroundColor White
    Write-Host ""
}

# 5. Launch FastAPI Application
Write-Host ""
Write-Host "Starting BollySwap AI FastAPI server on http://$HostAddress`:$Port..." -ForegroundColor Cyan
Write-Host "Interactive Swagger Docs: http://$HostAddress`:$Port/docs" -ForegroundColor Gray
Write-Host "Engine Status Endpoint  : http://$HostAddress`:$Port/api/engine/status" -ForegroundColor Gray
Write-Host ""

$env:PYTHONPATH = (Join-Path $ScriptDir "backend")
& $VenvPython -m uvicorn app.main:app --host $HostAddress --port $Port --app-dir (Join-Path $ScriptDir "backend") --reload

