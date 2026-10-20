$items = Get-ChildItem -Path C:\ -Directory
$results = @()
foreach ($item in $items) {
    if ($item.Name -in @('Windows', '$Recycle.Bin', 'System Volume Information')) { continue }
    $m = Get-ChildItem -LiteralPath $item.FullName -Recurse -File -Force -ErrorAction SilentlyContinue | Measure-Object -Property Length -Sum
    if ($m.Sum -gt 1GB) {
        $results += [PSCustomObject]@{
            Folder = $item.Name
            SizeGB = [math]::Round($m.Sum / 1GB, 2)
        }
    }
}
$results | Sort-Object SizeGB -Descending | Format-Table -AutoSize
