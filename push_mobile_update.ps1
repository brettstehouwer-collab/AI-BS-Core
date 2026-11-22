$adb = "C:\Users\footb\AppData\Local\Android\Sdk\platform-tools\adb.exe"
$apk = "C:\AI-BS\frontend\android\app\build\outputs\apk\debug\app-debug.apk"
$phoneIp = "192.168.4.27:5555"

Write-Host "==================================================" -ForegroundColor Cyan
Write-Host "  AI-BS Mobile ADB Push & In-Place Installer     " -ForegroundColor Cyan
Write-Host "==================================================" -ForegroundColor Cyan

Write-Host "[1/3] Connecting to target phone ($phoneIp)..." -ForegroundColor Yellow
& $adb connect $phoneIp

Write-Host "[2/3] Checking ADB device authorization..." -ForegroundColor Yellow
$deviceReady = $false
for ($i = 0; $i -lt 15; $i++) {
    $devices = & $adb devices
    $lines = $devices -split "`r?`n"
    foreach ($line in $lines) {
        if ($line -match "^\s*([^\s]+)\s+device\s*$") {
            $matchedDev = $matches[1]
            if ($matchedDev -notmatch "List of devices") {
                $deviceReady = $true
                $targetDev = $matchedDev
                break
            }
        }
    }
    if ($deviceReady) { break }
    
    if ($devices -match "unauthorized") {
        Write-Host "  -> Phone connected at $phoneIp but UNPAIRED/UNAUTHORIZED." -ForegroundColor Magenta
        Write-Host "     Please unlock your phone and tap 'Allow' on the USB/Wireless Debugging dialog!" -ForegroundColor Yellow
    } else {
        Write-Host "  -> Waiting for device connection..." -ForegroundColor Gray
    }
    Start-Sleep -Seconds 2
    & $adb connect $phoneIp | Out-Null
}

if ($deviceReady) {
    Write-Host "[3/3] Device authorized ($targetDev)! Pushing and installing latest APK..." -ForegroundColor Green
    & $adb -s $targetDev install -r $apk
    Write-Host "Restarting application on device..." -ForegroundColor Green
    & $adb -s $targetDev shell am force-stop com.stehouwerpublishing.digitalstorefront
    & $adb -s $targetDev shell am start -n com.stehouwerpublishing.digitalstorefront/.MainActivity
    Write-Host "==================================================" -ForegroundColor Green
    Write-Host "  MOBILE APP UPDATED & LAUNCHED SUCCESSFULLY!     " -ForegroundColor Green
    Write-Host "==================================================" -ForegroundColor Green
} else {
    Write-Host "==================================================" -ForegroundColor Red
    Write-Host "  FAILED: Device authorization timed out.         " -ForegroundColor Red
    Write-Host "  Action needed on your phone:                    " -ForegroundColor Yellow
    Write-Host "  1. Unlock your phone screen.                    " -ForegroundColor White
    Write-Host "  2. Look for 'Allow USB / Wireless debugging?'   " -ForegroundColor White
    Write-Host "  3. Check 'Always allow' and tap 'Allow'.        " -ForegroundColor White
    Write-Host "  Then run this script or batch file again!       " -ForegroundColor Yellow
    Write-Host "==================================================" -ForegroundColor Red
}
