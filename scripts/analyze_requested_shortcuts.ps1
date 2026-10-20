$sh = New-Object -ComObject WScript.Shell

$requested = @(
    "C:\Users\Public\Desktop\AI-BS Shutdown.lnk",
    "C:\Users\Public\Desktop\AI-BS Broadcast Studio.lnk",
    "C:\Users\Public\Desktop\BS-Studio.lnk",
    "C:\Users\footb\OneDrive\Desktop\Launch_Unreal_OnDemand.lnk",
    "C:\Users\footb\OneDrive\Desktop\Launch_AI_BS - Shortcut.lnk",
    "C:\Users\footb\OneDrive\Desktop\Start Crypto Swarm.lnk",
    "C:\Users\Public\Desktop\AI-BS Sovereign Studio.lnk",
    "C:\Users\footb\OneDrive\Desktop\Stehouwer Publishing AI-BS Matrix.lnk",
    "C:\Users\footb\OneDrive\Desktop\BS-Studio.lnk",
    "C:\Users\Public\Desktop\AI-BS Matrix Boot.lnk",
    "C:\Users\footb\OneDrive\Desktop\AI-BS Matrix Boot.lnk",
    "C:\Users\footb\OneDrive\Desktop\AI-BS Matrix.lnk",
    "C:\Users\footb\OneDrive\Desktop\AI-BS Broadcast Studio.lnk",
    "C:\Users\footb\OneDrive\Desktop\AI-BS Sovereign Studio.lnk",
    "C:\Users\Public\Desktop\AI-BS Matrix.lnk",
    "C:\Users\footb\OneDrive\Desktop\AI-BS Shutdown.lnk",
    "C:\Users\footb\OneDrive\Desktop\Launch_Unreal_OnDemand (2).lnk",
    "C:\Users\footb\OneDrive\Desktop\Launch_AI_BS - Shortcut (2).lnk"
)

$data = foreach ($path in $requested) {
    if (Test-Path $path) {
        $item = Get-Item $path
        $lnk = $sh.CreateShortcut($path)
        $targetExists = Test-Path $lnk.TargetPath
        [PSCustomObject]@{
            ShortcutPath = $path
            Name         = $item.Name
            Folder       = $item.DirectoryName
            TargetPath   = $lnk.TargetPath
            Arguments    = $lnk.Arguments
            WorkingDir   = $lnk.WorkingDirectory
            TargetExists = $targetExists
            LastModified = $item.LastWriteTime
        }
    } else {
        [PSCustomObject]@{
            ShortcutPath = $path
            Name         = [System.IO.Path]::GetFileName($path)
            Folder       = [System.IO.Path]::GetDirectoryName($path)
            TargetPath   = "FILE_NOT_FOUND"
            Arguments    = ""
            WorkingDir   = ""
            TargetExists = $false
            LastModified = $null
        }
    }
}

$data | Format-List
