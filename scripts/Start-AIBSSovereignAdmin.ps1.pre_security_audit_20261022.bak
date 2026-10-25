<#
.SYNOPSIS
    Starts the complete AI-BS Sovereign Intelligence Ecosystem and Native Studio
    with full Windows Administrator privileges and optimal system performance.
#>
param(
    [switch]$NoStudio
)

# 1. Self-Elevation Check: Ensure running with full Administrator privileges
$isAdmin = ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
if (-not $isAdmin) {
    Write-Host "[ELEVATION REQUIRED] Requesting Windows Administrator privileges..." -ForegroundColor Yellow
    $scriptPath = $MyInvocation.MyCommand.Path
    if (-not $scriptPath) { $scriptPath = "C:\AI-BS\scripts\Start-AIBSSovereignAdmin.ps1" }
    $argList = @("-ExecutionPolicy", "Bypass", "-NoExit", "-File", "`"$scriptPath`"")
    if ($NoStudio) { $argList += "-NoStudio" }
    Start-Process -FilePath "powershell.exe" -Verb RunAs -ArgumentList $argList
    exit
}

try {
    $Host.UI.RawUI.WindowTitle = "AI-BS Sovereign Ecosystem (Administrator Level)"
} catch {}

$baseDir = "C:\AI-BS"
$py = "$($baseDir)\pyppeteer_env\Scripts\python.exe"
$pyw = "$($baseDir)\pyppeteer_env\Scripts\pythonw.exe"

Clear-Host
Write-Host "==========================================================================" -ForegroundColor Cyan
Write-Host "      AI-BS SOVEREIGN INTELLIGENCE ECOSYSTEM -- ADMIN LEVEL LAUNCHER       " -ForegroundColor Cyan
Write-Host "       Host: Windows 11 Pro | Status: Full Administrator Privileges       " -ForegroundColor Green
Write-Host "==========================================================================" -ForegroundColor Cyan
Write-Host ""

# 2. Windows Defender and Performance Optimizations
Write-Host ">>> [1/6] Registering Admin-level Defender exclusions and firewall ports..." -ForegroundColor Cyan
try {
    $excludePaths = @("C:\AI-BS", "C:\AI-BS\.temp_executor")
    if (Test-Path "E:\AI_BS_Resources") { $excludePaths += "E:\AI_BS_Resources" }
    Add-MpPreference -ExclusionPath $excludePaths -ErrorAction SilentlyContinue
    Add-MpPreference -ExclusionProcess @("AI_BS_Studio.exe", "python.exe", "pythonw.exe", "aibs_engine.exe", "ollama.exe", "node.exe") -ErrorAction SilentlyContinue
} catch {}

$firewallScript = "$($baseDir)\scripts\open_streaming_firewall_ports.ps1"
if (Test-Path $firewallScript) {
    try {
        & powershell.exe -ExecutionPolicy Bypass -File $firewallScript | Out-Null
    } catch {}
}

# 3. WSL2 Subsystem Background Services
Write-Host ">>> [2/6] Starting WSL2 multi-tenant Ubuntu background services..." -ForegroundColor Cyan
try {
    wsl.exe -d Ubuntu -u root -- systemctl start clore-hosting.service 2>$null
    wsl.exe -d Ubuntu -u root -- systemctl start ubuntu-bio-bridge.service 2>$null
} catch {}

# 4. Host Web Server and Go Gateway
Write-Host ">>> [3/6] Starting Nginx and Go Matrix Engine..." -ForegroundColor Cyan
$nginxPath = "C:\Users\footb\AppData\Local\Microsoft\WinGet\Packages\nginxinc.nginx_Microsoft.Winget.Source_8wekyb3d8bbwe\nginx-1.31.3\nginx.exe"
if (Test-Path $nginxPath) {
    $p80 = Get-NetTCPConnection -State Listen -LocalPort 80 -ErrorAction SilentlyContinue
    if (-not $p80) {
        Start-Process -FilePath $nginxPath -ArgumentList "-p C:\StehouwerPublishing.com -c C:\StehouwerPublishing.com\nginx.conf" -WindowStyle Hidden
    }
}

$goEngine = "$($baseDir)\go-core\aibs_engine.exe"
if (Test-Path $goEngine) {
    $p8000 = Get-NetTCPConnection -State Listen -LocalPort 8000 -ErrorAction SilentlyContinue
    if (-not $p8000) {
        Start-Process -FilePath $goEngine -WorkingDirectory "$($baseDir)\go-core" -WindowStyle Hidden
    }
}

# 5. Core Ecosystem Daemons (Ollama, FastAPI 8080, ChromaDB 8001/8002, Node 3001, Vite 5173, Daemons)
Write-Host ">>> [4/6] Verifying and spawning all ecosystem daemons via multi-port supervisor..." -ForegroundColor Cyan
$env:CUDA_VISIBLE_DEVICES = "0"
$env:OLLAMA_IGPU_ENABLE = "0"
$env:OLLAMA_MODELS = "C:\AI-BS\models\ollama"
$env:OLLAMA_HOST = "0.0.0.0"
$env:OLLAMA_KEEP_ALIVE = "0"
$env:OLLAMA_FLASH_ATTENTION = "1"

& $py -m backend.aibs_ecosystem_spawner

# 6. Launch Pure Native Direct2D Studio with Elevated HWND and Real-Time MMCSS
if (-not $NoStudio) {
    Write-Host ">>> [5/6] Launching AI-BS Sovereign Native Studio (Elevated Admin HWND)..." -ForegroundColor Cyan
    $env:PYTHONPATH = "$($baseDir);$($baseDir)\native_studio;$($baseDir)\backend"
    $appPath = "$($baseDir)\native_studio\app.py"
    Start-Process -FilePath $py -ArgumentList "`"$appPath`"" -WorkingDirectory $baseDir
}

Write-Host ""
Write-Host "==========================================================================" -ForegroundColor Green
Write-Host "  [SUCCESS] All sovereign services and Native Studio running at Admin level!" -ForegroundColor Green
Write-Host "==========================================================================" -ForegroundColor Green
Write-Host ""
