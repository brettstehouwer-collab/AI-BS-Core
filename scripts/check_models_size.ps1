$m = (Get-ChildItem -LiteralPath 'C:\AI-BS\ComfyUI\models' -Recurse -File -Force -ErrorAction SilentlyContinue | Measure-Object -Property Length -Sum).Sum
Write-Host "ComfyUI Models Size: $([math]::Round($m / 1GB, 2)) GB"
