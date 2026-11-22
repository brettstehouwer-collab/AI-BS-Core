
$sh = New-Object -ComObject WScript.Shell
$folders = @('C:\Users\footb\OneDrive\Desktop', 'C:\Users\footb\Desktop')
Get-ChildItem -Path $folders -Filter '*.lnk' | ForEach-Object {
    try {
        $s = $sh.CreateShortcut($_.FullName)
        Write-Output "$($_.Name)|$($s.TargetPath)|$($s.Arguments)|$($s.WorkingDirectory)"
    } catch {}
}
