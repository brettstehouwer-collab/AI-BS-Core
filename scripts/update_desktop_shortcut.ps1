$WshShell = New-Object -ComObject WScript.Shell
$desktopPath = [System.Environment]::GetFolderPath('Desktop')
$shortcutPath = Join-Path $desktopPath "AI-BS Developer Chrome.lnk"

$Shortcut = $WshShell.CreateShortcut($shortcutPath)
$Shortcut.TargetPath = "C:\Program Files\Google\Chrome\Application\chrome.exe"
$Shortcut.Arguments = '--remote-debugging-port=9222 --user-data-dir="C:\Users\footb\.cache\chrome-devtools-mcp\chrome-profile" --profile-directory="Default" --no-first-run --no-default-browser-check --disable-blink-features=AutomationControlled'
$Shortcut.Description = "AI-BS Developer Chrome with user profile and stealth authentication"
$Shortcut.IconLocation = "C:\Program Files\Google\Chrome\Application\chrome.exe,0"
$Shortcut.WorkingDirectory = "C:\Program Files\Google\Chrome\Application"
$Shortcut.Save()

Write-Host "Shortcut saved at: $shortcutPath"
