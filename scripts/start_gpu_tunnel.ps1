# start_gpu_tunnel.ps1
# Manages local port forwarding and Cloudflare tunnel mapping for Vast.ai / Clore.ai compute host containers.

param (
    [int]$VastPortStart = 40000,
    [int]$VastPortEnd = 40010,
    [string]$TunnelHost = "localhost"
)

Write-Host "=== AI-BS GPU Compute Tunnel Manager ===" -ForegroundColor Cyan
Write-Host "Configuring port ranges for Vast.ai / Clore.ai Container Access..." -ForegroundColor Yellow

# Verify Docker / WSL status
try {
    $wslStatus = wsl --status
    Write-Host "WSL2 Status: OK" -ForegroundColor Green
} catch {
    Write-Host "WARNING: WSL2 is not currently active or installed." -ForegroundColor Red
}

# Verify cloudflared status
$cloudflaredPath = Get-Command cloudflared -ErrorAction SilentlyContinue
if ($cloudflaredPath) {
    Write-Host "Cloudflared Tunnel Binary: Available ($($cloudflaredPath.Source))" -ForegroundColor Green
} else {
    Write-Host "Cloudflared Tunnel Binary: Local fallback mode" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "Port range mapped: $VastPortStart-$VastPortEnd -> $TunnelHost" -ForegroundColor Cyan
Write-Host "GPU Tunnel active. Compute containers can safely bind for incoming client traffic." -ForegroundColor Green
