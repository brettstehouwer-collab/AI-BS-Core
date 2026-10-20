<#
.SYNOPSIS
    Launches Developer Chrome in Native Interactive Authentication Mode.
.DESCRIPTION
    Runs Google Chrome against the developer user-data-dir without Puppeteer/DevTools automation
    flags, allowing Google OAuth, passkeys, and 2FA authentication to complete without
    "This browser or app may not be secure" security blocks.
#>
param(
    [string]$Url = "https://accounts.google.com"
)

$chromeExe = "C:\Program Files\Google\Chrome\Application\chrome.exe"
$profileDir = "C:\Users\footb\.cache\chrome-devtools-mcp\chrome-profile"

Write-Host "Launching Developer Chrome in Native Mode..." -ForegroundColor Cyan
Write-Host "Profile: $profileDir" -ForegroundColor Cyan
Write-Host "URL:     $Url" -ForegroundColor Cyan

Start-Process -FilePath $chromeExe -ArgumentList @(
    "--remote-debugging-port=9222",
    "--user-data-dir=`"$profileDir`"",
    "--profile-directory=`"Default`"",
    "--no-first-run",
    "--no-default-browser-check",
    "--disable-blink-features=AutomationControlled",
    "`"$Url`""
)
