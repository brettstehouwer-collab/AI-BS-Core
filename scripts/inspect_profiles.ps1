$devState = Get-Content "C:\Users\footb\.cache\chrome-devtools-mcp\chrome-profile\Local State" -Raw | ConvertFrom-Json
$srcState = Get-Content "C:\Users\footb\AppData\Local\Google\Chrome\User Data\Local State" -Raw | ConvertFrom-Json

Write-Host "=== DEV Local State Profile Info ==="
$devState.profile.info_cache | Format-List *

Write-Host "=== SRC Local State Profile Info ==="
$srcState.profile.info_cache | Format-List *

Write-Host "=== Checking Cookies and Login Data ==="
$devCookies = "C:\Users\footb\.cache\chrome-devtools-mcp\chrome-profile\Default\Network\Cookies"
$srcCookies = "C:\Users\footb\AppData\Local\Google\Chrome\User Data\Default\Network\Cookies"
Write-Host "Dev Cookies exists: $(Test-Path $devCookies) (Size: $((Get-Item $devCookies -ErrorAction SilentlyContinue).Length))"
Write-Host "Src Cookies exists: $(Test-Path $srcCookies) (Size: $((Get-Item $srcCookies -ErrorAction SilentlyContinue).Length))"

$devLogin = "C:\Users\footb\.cache\chrome-devtools-mcp\chrome-profile\Default\Login Data"
$srcLogin = "C:\Users\footb\AppData\Local\Google\Chrome\User Data\Default\Login Data"
Write-Host "Dev last_used: $($devState.profile.last_used)"
Write-Host "Dev last_active_profiles: $($devState.profile.last_active_profiles -join ', ')"
$devPref = Get-Content "C:\Users\footb\.cache\chrome-devtools-mcp\chrome-profile\Default\Preferences" -Raw | ConvertFrom-Json
$srcPref = Get-Content "C:\Users\footb\AppData\Local\Google\Chrome\User Data\Default\Preferences" -Raw | ConvertFrom-Json

Write-Host "Dev account_tracker_service_last_update: $($devPref.account_tracker_service_last_update)"
Write-Host "Src account_tracker_service_last_update: $($srcPref.account_tracker_service_last_update)"
Write-Host "Dev google.services.signin: $($devPref.google.services.signin | ConvertTo-Json -Compress)"
Write-Host "Src google.services.signin: $($srcPref.google.services.signin | ConvertTo-Json -Compress)"
Write-Host "Dev sync.has_setup_completed: $($devPref.sync.has_setup_completed)"
Write-Host "Src sync.has_setup_completed: $($srcPref.sync.has_setup_completed)"


Write-Host "=== Default Profile Files in Dev ==="
$files = Get-ChildItem "C:\Users\footb\.cache\chrome-devtools-mcp\chrome-profile\Default" -File
foreach ($f in $files) {
    if ($f.Name -match "Preferences|Web Data|Login Data|History|Cookies|Bookmarks|Secure Preferences") {
        Write-Host "$($f.Name) : $($f.Length) bytes ($($f.LastWriteTime))"
    }
}

