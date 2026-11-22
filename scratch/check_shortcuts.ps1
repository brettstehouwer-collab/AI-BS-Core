$sh = New-Object -ComObject WScript.Shell
$links = @(
    'C:\Users\footb\OneDrive\Desktop\Stehouwer AI • Sovereign Intelligence Studio.lnk',
    'C:\Users\footb\OneDrive\Desktop\AI-BS Master Server Boot (All 18 Engines).lnk',
    'C:\Users\footb\OneDrive\Desktop\AI-BS Shutdown.lnk'
)
foreach ($lnk in $links) {
    if (Test-Path $lnk) {
        $s = $sh.CreateShortcut($lnk)
        Write-Output "---"
        Write-Output "Name: $(Split-Path $lnk -Leaf)"
        Write-Output "TargetPath: $($s.TargetPath)"
        Write-Output "Arguments: $($s.Arguments)"
        Write-Output "WorkingDirectory: $($s.WorkingDirectory)"
    } else {
        Write-Output "---"
        Write-Output "Name: $(Split-Path $lnk -Leaf)"
        Write-Output "Status: NOT FOUND"
    }
}
