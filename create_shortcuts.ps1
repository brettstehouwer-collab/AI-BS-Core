$DesktopPath = [Environment]::GetFolderPath('Desktop')
$FolderPath = Join-Path -Path $DesktopPath -ChildPath 'AI-BS eco system start stop'
New-Item -ItemType Directory -Force -Path $FolderPath | Out-Null
$WshShell = New-Object -comObject WScript.Shell
Get-ChildItem -Path C:\AI-BS -Filter *.bat | ForEach-Object {
    $Shortcut = $WshShell.CreateShortcut((Join-Path -Path $FolderPath -ChildPath ($_.BaseName + '.lnk')))
    $Shortcut.TargetPath = $_.FullName
    $Shortcut.WorkingDirectory = $_.DirectoryName
    $Shortcut.Save()
}
