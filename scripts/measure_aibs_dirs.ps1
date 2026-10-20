$dirs = Get-ChildItem -Path 'C:\AI-BS' -Directory
$results = @()
foreach ($d in $dirs) {
    $m = Get-ChildItem -LiteralPath $d.FullName -Recurse -File -Force -ErrorAction SilentlyContinue | Measure-Object -Property Length -Sum
    if ($m.Sum -gt 2GB) {
        $results += [PSCustomObject]@{
            Folder = $d.Name
            SizeGB = [math]::Round($m.Sum / 1GB, 2)
        }
    }
}
$results | Sort-Object SizeGB -Descending | Format-Table -AutoSize
