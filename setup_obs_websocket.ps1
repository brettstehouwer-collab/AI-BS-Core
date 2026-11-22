$ErrorActionPreference = "Stop"

$wsConfigDir = "C:\AI-BS\obs-core\config\obs-studio\plugin_config\obs-websocket"
if (-not (Test-Path $wsConfigDir)) {
    New-Item -ItemType Directory -Force -Path $wsConfigDir | Out-Null
}

$wsConfigFile = "$wsConfigDir\config.json"

$configJson = @"
{
    "server_port": 4455,
    "server_password": "",
    "server_enable": true,
    "server_auth_enable": false,
    "alerts_enabled": false
}
"@

Set-Content -Path $wsConfigFile -Value $configJson -Force
Write-Host "[OK] OBS WebSocket Port 4455 Configuration Written." -ForegroundColor Green