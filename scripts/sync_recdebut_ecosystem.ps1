# Recreational Debut & AI-BS Parity Synchronizer
param(
    [switch]$Watch
)

$python = "python"
$script = "C:\Recreational-Debut\sync\recdebut_sync_engine.py"

if ($Watch) {
    Write-Host ">>> Launching Continuous Watch Daemon..."
    & $python $script --watch
} else {
    Write-Host ">>> Running One-Shot Parity Synchronization..."
    & $python $script
}
