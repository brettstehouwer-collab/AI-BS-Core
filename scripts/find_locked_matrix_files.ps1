Get-ChildItem -Path "C:\Program Files\AI-BS Matrix" -Recurse | Sort-Object FullName -Descending | ForEach-Object {
    try {
        [System.IO.File]::Delete($_.FullName)
    } catch [System.IO.DirectoryNotFoundException] {
        # ignore
    } catch {
        if (-not $_.PSIsContainer) {
            Write-Host "Locked file: $($_.FullName) - $($_.Exception.Message)"
        }
    }
}
