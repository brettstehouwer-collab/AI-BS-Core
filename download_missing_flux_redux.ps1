$BASE = "C:\AI-BS\AI-BS-Models"
$TOKEN = "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"
$headers = @{ "Authorization" = "Bearer $TOKEN" }

Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "  Downloading Missing ComfyUI FLUX Redux Models" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan

$dirs = @("$BASE\clip")
foreach ($d in $dirs) { if (-not (Test-Path $d)) { New-Item -ItemType Directory -Path $d -Force | Out-Null } }

$models = @(
    @{ Url = "https://huggingface.co/comfyanonymous/flux_text_encoders/resolve/main/t5xxl_fp16.safetensors"; DestDir = "$BASE\clip"; File = "t5xxl_fp16.safetensors" },
    @{ Url = "https://huggingface.co/comfyanonymous/flux_text_encoders/resolve/main/clip_l.safetensors"; DestDir = "$BASE\clip"; File = "clip_l.safetensors" }
)

foreach ($m in $models) {
    $fullPath = Join-Path $m.DestDir $m.File
    if (Test-Path $fullPath) {
        $size = (Get-Item $fullPath).Length
        if ($size -gt 100MB) {
            Write-Host "[SKIP] $($m.File) already exists." -ForegroundColor Green
            continue
        }
    }
    
    Write-Host "[DOWNLOAD] $($m.File) to $($m.DestDir) (This may take a while...)" -ForegroundColor Yellow
    try {
        Invoke-WebRequest -Uri $m.Url -Headers $headers -OutFile $fullPath -UseBasicParsing -ErrorAction Stop
        Write-Host "[DONE] $($m.File) successfully downloaded!" -ForegroundColor Green
    } catch {
        Write-Host "[ERROR] Failed to download $($m.File): $($_.Exception.Message)" -ForegroundColor Red
        if (Test-Path $fullPath) { Remove-Item $fullPath -Force }
    }
}

Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "  ALL MISSING MODELS DOWNLOADED! RESTART COMFYUI!" -ForegroundColor Green
Write-Host "============================================================" -ForegroundColor Cyan
Pause
