# Automated S25 Ultra ADB Installer Daemon
$adb = "C:\Users\footb\AppData\Local\Android\Sdk\platform-tools\adb.exe"
$apk = "C:\Users\footb\OneDrive\Desktop\DennisBellRemote_GalaxyS25Ultra.apk"
$package = "com.stehouwerpublishing.digitalstorefront"

Write-Host ">>> Watching for authorized Galaxy S25 Ultra on ADB..."

$maxAttempts = 120
for ($i = 0; $i -lt $maxAttempts; $i++) {
    $devices = & $adb devices
    if ($devices -match "([A-Za-z0-9]+)\s+device\b") {
        $deviceId = $matches[1]
        Write-Host ">>> Device authorized! Detected Device ID: $deviceId"
        Write-Host ">>> Installing APK: $apk ..."
        $installResult = & $adb -s $deviceId install -r $apk
        Write-Host ">>> Install Output: $installResult"
        
        Write-Host ">>> Launching Dennis Bell Remote on Galaxy S25 Ultra..."
        & $adb -s $deviceId shell am start -n "$package/.MainActivity"
        Write-Host ">>> APPLICATION LAUNCHED ON GALAXY S25 ULTRA SUCCESSFULLY!"
        exit 0
    } elseif ($devices -match "unauthorized") {
        Write-Host ">>> Device detected but waiting for operator to tap 'Allow' on Galaxy S25 Ultra screen... (Attempt $($i+1)/$maxAttempts)"
    } else {
        Write-Host ">>> Waiting for device connection... (Attempt $($i+1)/$maxAttempts)"
    }
    Start-Sleep -Seconds 2
}

Write-Host ">>> Timeout waiting for device authorization."
exit 1
