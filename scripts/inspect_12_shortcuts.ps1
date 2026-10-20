$ErrorActionPreference = "SilentlyContinue"
$sh = New-Object -ComObject WScript.Shell
$files = @(
    "Stehouwer Publishing AI-BS Matrix.lnk",
    "BS-Studio.lnk",
    "AI-BS Matrix Boot.lnk",
    "Launch_Unreal_OnDemand.lnk",
    "Launch_AI_BS - Shortcut.lnk",
    "Start Crypto Swarm.lnk",
    "AI-BS Matrix.lnk",
    "AI-BS Broadcast Studio.lnk",
    "AI-BS Sovereign Studio.lnk",
    "AI-BS Shutdown.lnk",
    "Launch_Unreal_OnDemand (2).lnk",
    "Launch_AI_BS - Shortcut (2).lnk"
)

$backupDir = "C:\AI-BS\saved_data\desktop_shortcuts_backup_20260909_115600"
$liveDir = "C:\Users\footb\OneDrive\Desktop"

$results = foreach ($f in $files) {
    $backupFile = Join-Path $backupDir ("User_" + $f)
    $liveFile = Join-Path $liveDir $f
    
    # We want to inspect the original configuration from the backup as well as current live state
    $pathToInspect = if (Test-Path $backupFile) { $backupFile } elseif (Test-Path $liveFile) { $liveFile } else { $null }
    
    if ($pathToInspect) {
        $sc = $sh.CreateShortcut($pathToInspect)
        [PSCustomObject]@{
            ShortcutName = $f
            Target = $sc.TargetPath
            Arguments = $sc.Arguments
            WorkingDirectory = $sc.WorkingDirectory
            TargetExists = Test-Path $sc.TargetPath
            LiveOnDesktop = Test-Path $liveFile
            ArchivedInBackup = Test-Path $backupFile
        }
    } else {
        [PSCustomObject]@{
            ShortcutName = $f
            Target = "NOT FOUND"
            Arguments = ""
            WorkingDirectory = ""
            TargetExists = $false
            LiveOnDesktop = $false
            ArchivedInBackup = $false
        }
    }
}
$results | Format-List
