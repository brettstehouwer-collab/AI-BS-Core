$sh = New-Object -ComObject WScript.Shell
$names = @("AI-BS Sovereign Studio.lnk", "AI-BS Broadcast Studio.lnk", "AI-BS Matrix Boot.lnk")
$results = foreach ($name in $names) {
    $path = Join-Path "C:\Users\footb\OneDrive\Desktop" $name
    if (Test-Path $path) {
        $sc = $sh.CreateShortcut($path)
        [PSCustomObject]@{
            ShortcutName = $name
            TargetPath = $sc.TargetPath
            WorkingDirectory = $sc.WorkingDirectory
            Arguments = $sc.Arguments
            IconLocation = $sc.IconLocation
            TargetExists = Test-Path $sc.TargetPath
        }
    } else {
        [PSCustomObject]@{
            ShortcutName = $name
            TargetPath = "NOT FOUND"
            WorkingDirectory = ""
            Arguments = ""
            IconLocation = ""
            TargetExists = $false
        }
    }
}
$results | Format-List
