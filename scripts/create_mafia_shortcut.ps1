$wsh = New-Object -ComObject WScript.Shell
$desktop = [System.Environment]::GetFolderPath('Desktop')
$shortcutPath = Join-Path $desktop "Build_and_Open_Mafia_World_UE5.lnk"

# Also check OneDrive Desktop
if (-not (Test-Path $desktop)) {
    $shortcutPath = "C:\Users\footb\OneDrive\Desktop\Build_and_Open_Mafia_World_UE5.lnk"
}

$shortcut = $wsh.CreateShortcut($shortcutPath)
$shortcut.TargetPath = "C:\AI-BS\Build_and_Open_Mafia_World_UE5.bat"
$shortcut.WorkingDirectory = "C:\AI-BS"
$shortcut.Description = "AI-BS 1-Click Mafia World Builder in Unreal Engine 5.8"
$shortcut.Save()

# If OneDrive Desktop exists, save there too
$oneDriveDesktop = "C:\Users\footb\OneDrive\Desktop\Build_and_Open_Mafia_World_UE5.lnk"
if (Test-Path "C:\Users\footb\OneDrive\Desktop") {
    $sc2 = $wsh.CreateShortcut($oneDriveDesktop)
    $sc2.TargetPath = "C:\AI-BS\Build_and_Open_Mafia_World_UE5.bat"
    $sc2.WorkingDirectory = "C:\AI-BS"
    $sc2.Description = "AI-BS 1-Click Mafia World Builder in Unreal Engine 5.8"
    $sc2.Save()
}

Write-Host "Created shortcut: $shortcutPath"
