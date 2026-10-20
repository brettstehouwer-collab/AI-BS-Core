# AI-BS System Peak Performance Optimizer for Salad Compute & Mining
Write-Host "======================================================" -ForegroundColor Cyan
Write-Host "  PREPARING SYSTEM FOR PEAK SALAD & HARDWARE YIELD    " -ForegroundColor Cyan
Write-Host "======================================================" -ForegroundColor Cyan

# 1. Windows Power Plan -> Ultimate Performance
try {
    powercfg /setactive 63c3fc0d-0d74-4dd1-8e79-76dd28e2bd13
    Write-Host "[OK] CPU Power Plan set to: Ultimate Performance (No core throttling)" -ForegroundColor Green
} catch {
    Write-Host "[WARN] Could not set Ultimate Performance: $_" -ForegroundColor Yellow
}

# 2. NVIDIA GPU Power Limit & Clocks
try {
    nvidia-smi -pl 450 | Out-Null
    Write-Host "[OK] NVIDIA RTX 4090 Power Limit locked at full 450.00 Watts" -ForegroundColor Green
} catch {
    Write-Host "[WARN] Could not set GPU power limit: $_" -ForegroundColor Yellow
}

# 3. Elevate Salad Process Priorities
$saladProcesses = Get-Process -Name "Salad*", "rigel*" -ErrorAction SilentlyContinue
foreach ($proc in $saladProcesses) {
    try {
        if ($proc.ProcessName -eq "Salad.Bowl.Service" -or $proc.ProcessName -eq "rigel") {
            $proc.PriorityClass = [System.Diagnostics.ProcessPriorityClass]::High
            Write-Host "[OK] Process '$($proc.ProcessName)' (PID $($proc.Id)) set to HIGH priority" -ForegroundColor Green
        } else {
            $proc.PriorityClass = [System.Diagnostics.ProcessPriorityClass]::AboveNormal
            Write-Host "[OK] Process '$($proc.ProcessName)' (PID $($proc.Id)) set to ABOVE NORMAL priority" -ForegroundColor Green
        }
    } catch {
        # Process may have transient security or exited
    }
}

# 4. Telemetry Snapshot
Write-Host "`n--- HARDWARE STATUS SNAPSHOT ---" -ForegroundColor Cyan
$gpuInfo = nvidia-smi --query-gpu=name,temperature.gpu,power.limit,memory.free,memory.total,utilization.gpu --format=csv,noheader
Write-Host "GPU: $gpuInfo" -ForegroundColor White

$mem = Get-CimInstance Win32_OperatingSystem
$freeRamGb = [math]::Round($mem.FreePhysicalMemory / 1048576, 2)
$totalRamGb = [math]::Round($mem.TotalVisibleMemorySize / 1048576, 2)
Write-Host "RAM: $freeRamGb GB free of $totalRamGb GB total" -ForegroundColor White

$cDrive = Get-PSDrive C
$cFree = [math]::Round($cDrive.Free / 1GB, 2)
Write-Host "C:\ Drive Free Space: $cFree GB" -ForegroundColor White

Write-Host "`nSystem is fully primed and optimized for maximum Salad workload earnings." -ForegroundColor Green
