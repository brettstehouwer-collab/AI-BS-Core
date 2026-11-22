$BASE = "C:\Users\footb\AI-BS\ComfyUI\ComfyUI\models"

$models = @(
    @{ Path = "$BASE\diffusion_models\flux1-dev-fp8.safetensors"; Label = "FLUX.1 FP8"; TotalGB = 17.2 },
    @{ Path = "$BASE\text_encoders\t5xxl_fp8_e4m3fn.safetensors"; Label = "T5-XXL FP8"; TotalGB = 9.8 },
    @{ Path = "$BASE\text_encoders\clip_l.safetensors"; Label = "CLIP-L"; TotalGB = 0.23 },
    @{ Path = "$BASE\vae\ae.safetensors"; Label = "FLUX VAE"; TotalGB = 0.34 },
    @{ Path = "$BASE\controlnet\flux_depth_controlnet.safetensors"; Label = "Depth ControlNet"; TotalGB = 3.2 },
    @{ Path = "$BASE\controlnet\flux_canny_controlnet.safetensors"; Label = "Canny ControlNet"; TotalGB = 3.2 },
    @{ Path = "$BASE\clip_vision\CLIP-ViT-H-14.safetensors"; Label = "CLIP Vision"; TotalGB = 2.4 },
    @{ Path = "$BASE\upscale_models\4x-UltraSharp.pth"; Label = "4x-UltraSharp"; TotalGB = 0.067 },
    @{ Path = "$BASE\checkpoints\sd_xl_base_1.0.safetensors"; Label = "SDXL Base (existing)"; TotalGB = 6.5 },
    @{ Path = "$BASE\controlnet\control-lora-depth-rank256.safetensors"; Label = "SDXL ControlNet (existing)"; TotalGB = 0.74 }
)

Write-Host "=== FLUX Model Download Status ===" -ForegroundColor Cyan

foreach ($m in $models) {
    if (Test-Path $m.Path) {
        $item = Get-Item $m.Path
        $sizeGB = [math]::Round($item.Length / 1073741824, 3)
        $pct = [math]::Round(($sizeGB / $m.TotalGB) * 100, 1)
        if ($pct -ge 99) {
            Write-Host "[DONE   ] $($m.Label) - $sizeGB GB (100%)" -ForegroundColor Green
        } else {
            Write-Host "[PARTIAL] $($m.Label) - $sizeGB / $($m.TotalGB) GB ($pct%)" -ForegroundColor Yellow
        }
    } else {
        Write-Host "[MISSING] $($m.Label) - not started" -ForegroundColor Red
    }
}
