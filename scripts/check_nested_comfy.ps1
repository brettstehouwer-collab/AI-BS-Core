$items = Get-ChildItem -Path 'C:\AI-BS\ComfyUI\ComfyUI'
foreach ($item in $items) {
    if ($item.PSIsContainer) {
        $m = (Get-ChildItem -LiteralPath $item.FullName -Recurse -File -Force -ErrorAction SilentlyContinue | Measure-Object -Property Length -Sum).Sum
        if ($m -gt 500MB) {
            Write-Host "$($item.Name): $([math]::Round($m / 1GB, 2)) GB"
        }
    } else {
        if ($item.Length -gt 500MB) {
            Write-Host "$($item.Name): $([math]::Round($item.Length / 1GB, 2)) GB"
        }
    }
}
