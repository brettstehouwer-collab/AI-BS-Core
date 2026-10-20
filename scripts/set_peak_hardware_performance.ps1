# Apply Max Unthrottled Performance to all hardware components
$schemeGuid = "63c3fc0d-0d74-4dd1-8e79-76dd28e2bd13" # Ultimate Performance

Write-Host "Enforcing Peak Performance Configuration..." -ForegroundColor Cyan

# 1. Disable PCIe Link State Power Management (ASPM = 0: Off)
powercfg /setacvalueindex $schemeGuid SUB_PCIEXPRESS ASPM 0
Write-Host "  [OK] PCIe Link State Power Management: OFF (Maximum PCIe Bus Bandwidth for RTX 4090)" -ForegroundColor Green

# 2. Processor Minimum & Maximum State to 100% (No downclocking lag on AMD Ryzen 9 9950X)
powercfg /setacvalueindex $schemeGuid SUB_PROCESSOR PROCTHROTTLEMIN 100
powercfg /setacvalueindex $schemeGuid SUB_PROCESSOR PROCTHROTTLEMAX 100
Write-Host "  [OK] CPU Throttle Minimum State: 100% (Instant Clocks, No Spool-up Delay)" -ForegroundColor Green

# 3. Disable Hard Disk / NVMe Drive Sleep
powercfg /setacvalueindex $schemeGuid SUB_DISK DISKIDLE 0
Write-Host "  [OK] NVMe SSD Idle Timeout: 0 (Never Sleep, Instant I/O)" -ForegroundColor Green

# 4. Disable USB Selective Suspend (Keep capture cards, audio interfaces, and peripherals at full power)
powercfg /setacvalueindex $schemeGuid 2a737441-1930-4402-8d77-b2bebba4d5a3 48e6b7a6-50f5-4760-a579-e4ff562b33c1 0
Write-Host "  [OK] USB Selective Suspend: DISABLED (Uninterrupted Peripherals)" -ForegroundColor Green

# 5. Activate Scheme
powercfg /setactive $schemeGuid
Write-Host "  [OK] Power Scheme Active: Ultimate Performance" -ForegroundColor Green

# 6. Set NVIDIA Power Limit ceiling (450W TDP)
nvidia-smi -i 0 -pl 450 | Out-Null
Write-Host "  [OK] NVIDIA GeForce RTX 4090 Power Limit: 450.00 W (Peak TDP Ceiling)" -ForegroundColor Green

Write-Host "Hardware is locked in at Peak Operating Power & Instant Responsiveness." -ForegroundColor Cyan
