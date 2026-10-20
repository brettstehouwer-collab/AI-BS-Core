Get-PSDrive -PSProvider FileSystem | ForEach-Object {
    [PSCustomObject]@{
        Drive = $_.Name
        FreeGB = [math]::Round($_.Free / 1GB, 2)
        UsedGB = [math]::Round($_.Used / 1GB, 2)
    }
} | Format-Table -AutoSize
