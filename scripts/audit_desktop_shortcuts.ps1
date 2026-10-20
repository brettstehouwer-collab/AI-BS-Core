$sh = New-Object -ComObject WScript.Shell
$dirs = @('C:\Users\Public\Desktop', 'C:\Users\footb\OneDrive\Desktop', 'C:\Users\footb\Desktop')

$results = foreach ($d in $dirs) {
    if (Test-Path $d) {
        Get-ChildItem -Path $d -Filter *.lnk -ErrorAction SilentlyContinue | ForEach-Object {
            try {
                $lnk = $sh.CreateShortcut($_.FullName)
                [PSCustomObject]@{
                    Location      = $_.DirectoryName
                    ShortcutName  = $_.Name
                    TargetPath    = $lnk.TargetPath
                    Arguments     = $lnk.Arguments
                    TargetExists  = (Test-Path $lnk.TargetPath)
                    LastWriteTime = $_.LastWriteTime
                    FullPath      = $_.FullName
                }
            } catch {
                [PSCustomObject]@{
                    Location      = $_.DirectoryName
                    ShortcutName  = $_.Name
                    TargetPath    = "ERROR"
                    Arguments     = ""
                    TargetExists  = $false
                    LastWriteTime = $_.LastWriteTime
                    FullPath      = $_.FullName
                }
            }
        }
    }
}

$results | Sort-Object ShortcutName, Location | Format-Table ShortcutName, Location, TargetPath, Arguments, TargetExists -AutoSize
$results | Export-Clixml -Path "C:\AI-BS\scripts\shortcuts_audit.xml"
