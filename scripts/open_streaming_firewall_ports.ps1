# ==============================================================================
# AI-BS Sovereign Intelligence Matrix - Streaming & Desktop Firewall Manager
# Location: C:\AI-BS\scripts\open_streaming_firewall_ports.ps1
# Target: C:\AI-BS\frontend\desktop-build\win-unpacked and Live Streaming Ports
# ==============================================================================

[CmdletBinding()]
param (
    [switch]$VerboseOutput = $true
)

$isAdmin = ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
if (-not $isAdmin) {
    Write-Error "[AI-BS Firewall] Administrator privileges required to configure Windows Defender Firewall. Please run as Administrator."
    exit 1
}

Write-Host "================================================================" -ForegroundColor Cyan
Write-Host "  AI-BS SOVEREIGN STUDIO - STREAMING FIREWALL & PORTS CONFIG    " -ForegroundColor Cyan
Write-Host "================================================================" -ForegroundColor Cyan

# ------------------------------------------------------------------------------
# 1. APPLICATION EXECUTABLE RULES (Inbound & Outbound across Domain, Private, Public)
# ------------------------------------------------------------------------------
$appTargets = @(
    @{
        Name        = "AI-BS-Sovereign-Studio-App"
        DisplayName = "AI-BS Sovereign Studio - Desktop Application"
        Path        = "C:\AI-BS\frontend\desktop-build\win-unpacked\AI-BS Sovereign Studio.exe"
        Description = "Allows unrestricted network connectivity for the main AI-BS Sovereign Studio desktop application."
    },
    @{
        Name        = "AI-BS-Sovereign-Studio-Backend"
        DisplayName = "AI-BS Sovereign Studio - Embedded Brain Backend"
        Path        = "C:\AI-BS\frontend\desktop-build\win-unpacked\resources\brain_backend\brain_backend.exe"
        Description = "Allows high-throughput local and network API access for the frozen Python FastAPI backend."
    },
    @{
        Name        = "AI-BS-Sovereign-Studio-Engine"
        DisplayName = "AI-BS Sovereign Studio - Embedded Go Gateway"
        Path        = "C:\AI-BS\frontend\desktop-build\win-unpacked\resources\go-core\aibs_engine.exe"
        Description = "Allows network access for the high-speed Go gateway in the packaged desktop build."
    },
    @{
        Name        = "AI-BS-Sovereign-Studio-FFmpeg"
        DisplayName = "AI-BS Sovereign Studio - Embedded FFmpeg Encoder"
        Path        = "C:\AI-BS\frontend\desktop-build\win-unpacked\resources\brain_backend\_internal\imageio_ffmpeg\binaries\ffmpeg-win-x86_64-v7.1.exe"
        Description = "Allows hardware NVENC/x264 live RTMP stream outgest to Twitch, YouTube, and local RTMP servers."
    },
    @{
        Name        = "AI-BS-System-FFmpeg"
        DisplayName = "AI-BS System FFmpeg Engine"
        Path        = "C:\Users\footb\AppData\Local\Microsoft\WinGet\Links\ffmpeg.exe"
        Description = "Allows global FFmpeg hardware encoder network streaming."
    },
    @{
        Name        = "AI-BS-Pyppeteer-Python"
        DisplayName = "AI-BS Python Daemon Runtime"
        Path        = "C:\AI-BS\pyppeteer_env\Scripts\python.exe"
        Description = "Allows AI-BS broadcast daemons (Kernel 8088, Engine 8005, Social 8006, VST 8013, Signaling 8888) to accept incoming connections."
    },
    @{
        Name        = "AI-BS-Updater-Stub"
        DisplayName = "AI-BS Sovereign Studio - In-Place Auto-Updater Stub"
        Path        = "C:\AI-BS\frontend\desktop-build\win-unpacked\aibs_updater.exe"
        Description = "Allows standalone binary updater stub to download updates and verify remote update server endpoints."
    },
    @{
        Name        = "AI-BS-Updater-Stub-Temp"
        DisplayName = "AI-BS Sovereign Studio - Temp Staged Updater Stub"
        Path        = "$env:TEMP\aibs_update\aibs_updater.exe"
        Description = "Allows detached temp staged updater stub to manage network and binary updates."
        Optional    = $true
    }
)

# Auto-provision updater stub binaries from known locations if missing
$sourceUpdaterCandidates = @(
    "C:\AI-BS\frontend\desktop-build\win-unpacked\resources\updater\aibs_updater.exe",
    "C:\AI-BS\go-core\aibs_updater.exe",
    "C:\AI-BS\installer\aibs_updater.exe",
    "C:\AI-BS\tools\aibs_updater.exe"
)
$sourceUpdater = $sourceUpdaterCandidates | Where-Object { Test-Path $_ } | Select-Object -First 1

if ($sourceUpdater) {
    # Ensure unpack root has aibs_updater.exe
    $unpackedDir = "C:\AI-BS\frontend\desktop-build\win-unpacked"
    if (Test-Path $unpackedDir) {
        $unpackedUpdater = Join-Path $unpackedDir "aibs_updater.exe"
        if (-not (Test-Path $unpackedUpdater)) {
            Copy-Item -Path $sourceUpdater -Destination $unpackedUpdater -Force -ErrorAction SilentlyContinue
        }
    }

    # Ensure temp staged directory has aibs_updater.exe
    $tempUpdateDir = "$env:TEMP\aibs_update"
    if (-not (Test-Path $tempUpdateDir)) {
        New-Item -ItemType Directory -Path $tempUpdateDir -Force -ErrorAction SilentlyContinue | Out-Null
    }
    $tempUpdater = Join-Path $tempUpdateDir "aibs_updater.exe"
    if (-not (Test-Path $tempUpdater)) {
        Copy-Item -Path $sourceUpdater -Destination $tempUpdater -Force -ErrorAction SilentlyContinue
    }
}

foreach ($target in $appTargets) {
    if (Test-Path $target.Path) {
        # Inbound Application Rule
        $inName = "$($target.Name)-In"
        Remove-NetFirewallRule -Name $inName -ErrorAction SilentlyContinue
        New-NetFirewallRule -Name $inName `
                            -DisplayName "$($target.DisplayName) (Inbound)" `
                            -Description $target.Description `
                            -Program $target.Path `
                            -Direction Inbound `
                            -Action Allow `
                            -Profile Any `
                            -Protocol Any `
                            -Enabled True | Out-Null
        Write-Host "  [+] Inbound App Rule Active:  $($target.DisplayName)" -ForegroundColor Green

        # Outbound Application Rule
        $outName = "$($target.Name)-Out"
        Remove-NetFirewallRule -Name $outName -ErrorAction SilentlyContinue
        New-NetFirewallRule -Name $outName `
                            -DisplayName "$($target.DisplayName) (Outbound)" `
                            -Description $target.Description `
                            -Program $target.Path `
                            -Direction Outbound `
                            -Action Allow `
                            -Profile Any `
                            -Protocol Any `
                            -Enabled True | Out-Null
        Write-Host "  [+] Outbound App Rule Active: $($target.DisplayName)" -ForegroundColor Green
    } else {
        if (-not $target.Optional) {
            Write-Host "  [!] Binary path not found (Skipped): $($target.Path)" -ForegroundColor Yellow
        }
    }
}

# ------------------------------------------------------------------------------
# 2. STREAMING & PROTOCOL SPECIFIC PORT RULES (TCP & UDP)
# ------------------------------------------------------------------------------
$tcpStreamingPorts = @(
    "80",     # Nginx Reverse Proxy / Web
    "443",    # RTMPS / Secure Web
    "1935",   # RTMP Standard Live Streaming (Twitch, YouTube, Kick, Local RTMP)
    "3001",   # Node Backend Engine
    "4173",   # AI-BS Sovereign Studio Local UI HTTP Server
    "4455",   # OBS Studio WebSocket Orchestrator
    "5173",   # Vite Development HMR Server
    "5174",   # BroadcastStudioApp Vite Server
    "8000",   # Go Gateway / AI-BS Engine
    "8001",   # Theatrical Gateway
    "8002",   # ChromaDB Vector Database
    "8005",   # AI-BS Broadcast Daemon (Telemetry & FFmpeg Controller)
    "8006",   # AI-BS Social Daemon & Sidekick WebSocket
    "8008",   # Supabase Kong Gateway
    "8010",   # Shared Memory (SHM) Telemetry WebSocket Gateway
    "8013",   # AI-BS VST Audio Bridge
    "8080",   # Core FastAPI Backend Engine
    "8085",   # Ubuntu-Bio Bridge
    "8088",   # AI-BS Broadcast Kernel (D3D11 / NVENC Zero-Copy Video Engine)
    "8099",   # Gemini MCP Server
    "8189",   # ComfyUI Image/Video Generation
    "8765",   # Legacy WebSocket Telemetry
    "8888",   # Unreal Engine 5.8 Pixel Streaming Signaling Server & WebRTC Control
    "11434",  # Ollama Primary Engine
    "11435"   # Ollama Secondary Engine (E: Drive Models)
)

$udpStreamingPorts = @(
    "8888",         # Unreal Pixel Streaming WebRTC Signaling UDP
    "10000-20000"   # Dynamic WebRTC RTP/SRTP Audio/Video Media Streaming Ports
)

# A. Unified TCP Inbound Rule
$tcpInRule = "AI-BS-Streaming-Suite-TCP-In"
Remove-NetFirewallRule -Name $tcpInRule -ErrorAction SilentlyContinue
New-NetFirewallRule -Name $tcpInRule `
                    -DisplayName "AI-BS Streaming & Broadcast Suite (TCP-In)" `
                    -Description "Permits incoming connections for RTMP (1935), Unreal Pixel Streaming (8888), Broadcast Kernel (8088), Daemons (8005, 8006, 8013), and UI (4173, 5173)." `
                    -Direction Inbound `
                    -Action Allow `
                    -Profile Any `
                    -Protocol TCP `
                    -LocalPort $tcpStreamingPorts `
                    -Enabled True | Out-Null
Write-Host "  [+] TCP Inbound Ports Rule Configured: $($tcpStreamingPorts.Count) Ports Open" -ForegroundColor Green

# B. Unified TCP Outbound Rule
$tcpOutRule = "AI-BS-Streaming-Suite-TCP-Out"
Remove-NetFirewallRule -Name $tcpOutRule -ErrorAction SilentlyContinue
New-NetFirewallRule -Name $tcpOutRule `
                    -DisplayName "AI-BS Streaming & Broadcast Suite (TCP-Out)" `
                    -Description "Permits outgoing stream egress for RTMP, RTMPS, WebRTC, and API relays." `
                    -Direction Outbound `
                    -Action Allow `
                    -Profile Any `
                    -Protocol TCP `
                    -LocalPort $tcpStreamingPorts `
                    -Enabled True | Out-Null
Write-Host "  [+] TCP Outbound Ports Rule Configured: $($tcpStreamingPorts.Count) Ports Open" -ForegroundColor Green

# C. WebRTC & Pixel Streaming Media UDP Inbound Rule
$udpInRule = "AI-BS-Streaming-WebRTC-UDP-In"
Remove-NetFirewallRule -Name $udpInRule -ErrorAction SilentlyContinue
New-NetFirewallRule -Name $udpInRule `
                    -DisplayName "AI-BS WebRTC & Pixel Streaming Media (UDP-In)" `
                    -Description "Permits incoming WebRTC media stream packets (RTP/SRTP video/audio) across ports 8888 and 10000-20000." `
                    -Direction Inbound `
                    -Action Allow `
                    -Profile Any `
                    -Protocol UDP `
                    -LocalPort $udpStreamingPorts `
                    -Enabled True | Out-Null
Write-Host "  [+] WebRTC UDP Inbound Rule Configured: Ports 8888, 10000-20000 Open" -ForegroundColor Green

# D. WebRTC & Pixel Streaming Media UDP Outbound Rule
$udpOutRule = "AI-BS-Streaming-WebRTC-UDP-Out"
Remove-NetFirewallRule -Name $udpOutRule -ErrorAction SilentlyContinue
New-NetFirewallRule -Name $udpOutRule `
                    -DisplayName "AI-BS WebRTC & Pixel Streaming Media (UDP-Out)" `
                    -Description "Permits outgoing WebRTC media stream packets (RTP/SRTP video/audio) across ports 8888 and 10000-20000." `
                    -Direction Outbound `
                    -Action Allow `
                    -Profile Any `
                    -Protocol UDP `
                    -LocalPort $udpStreamingPorts `
                    -Enabled True | Out-Null
Write-Host "  [+] WebRTC UDP Outbound Rule Configured: Ports 8888, 10000-20000 Open" -ForegroundColor Green

Write-Host "================================================================" -ForegroundColor Cyan
Write-Host "  FIREWALL CONFIGURATION COMPLETE - ALL STREAMING PORTS OPEN    " -ForegroundColor Cyan
Write-Host "================================================================" -ForegroundColor Cyan
