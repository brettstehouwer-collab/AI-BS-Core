# PowerShell Script to Update and Recompile all 17 Ollama Modelfiles in AI-BS
param (
    [int]$Port = 11434
)

$env:OLLAMA_HOST = "127.0.0.1:$Port"
$modelsDir = "C:\AI-BS\backend\models"

$models = @(
    @{ Tag = "stehouwer_llm"; File = "stehouwer_llm.Modelfile" },
    @{ Tag = "qwen2.5-coder:latest"; File = "qwen2.5_coder.Modelfile" },
    @{ Tag = "qwen3.6:latest"; File = "qwen3.6.Modelfile" },
    @{ Tag = "nemotron-3.5-lightning:latest"; File = "nemotron_3.5_lightning.Modelfile" },
    @{ Tag = "stehouwer_qwen:latest"; File = "stehouwer_qwen.Modelfile" },
    @{ Tag = "stehouwer_dolphin:latest"; File = "stehouwer_dolphin.Modelfile" },
    @{ Tag = "unrestricted-llama3.1:latest"; File = "unrestricted_llama3.1.Modelfile" },
    @{ Tag = "dolphin-llama3:latest"; File = "dolphin_llama3.Modelfile" },
    @{ Tag = "stehouwer_llm_dolphin:latest"; File = "stehouwer_llm_dolphin.Modelfile" },
    @{ Tag = "stehouwer_hermes:latest"; File = "stehouwer_hermes.Modelfile" },
    @{ Tag = "gemma4:12b"; File = "gemma4_12b.Modelfile" },
    @{ Tag = "command-r:latest"; File = "command_r.Modelfile" },
    @{ Tag = "mixtral:latest"; File = "mixtral.Modelfile" },
    @{ Tag = "llama3.1:8b-instruct-q5_K_M"; File = "llama3.1_8b_instruct.Modelfile" },
    @{ Tag = "llama3.1:latest"; File = "llama3.1_technical.Modelfile" },
    @{ Tag = "llama3:latest"; File = "llama3_baseline.Modelfile" },
    @{ Tag = "nomic-embed-text:latest"; File = "nomic_embed_text.Modelfile" }
)

Write-Host "=================================================================="
Write-Host "     AI-BS 17-MODEL FLEET COMPILATION PIPELINE (Port $Port)       "
Write-Host "=================================================================="

$success = 0
$total = $models.Count
$idx = 0

foreach ($item in $models) {
    $idx++
    $tag = $item.Tag
    $fileName = $item.File
    $filePath = Join-Path $modelsDir $fileName

    if (-not (Test-Path $filePath)) {
        Write-Host "[$idx/$total] Missing Modelfile: $filePath"
        continue
    }

    Write-Host "[$idx/$total] Compiling '$tag' from '$fileName'..."
    & ollama create $tag -f $filePath
    if ($LASTEXITCODE -eq 0) {
        Write-Host "       Successfully compiled '$tag'"
        $success++
    } else {
        Write-Host "       Error compiling '$tag'"
    }
}

Write-Host "=================================================================="
Write-Host "Compilation complete: $success / $total models built successfully."
Write-Host "=================================================================="
Write-Host ""
Write-Host "Active Fleet Status:"
& ollama list
