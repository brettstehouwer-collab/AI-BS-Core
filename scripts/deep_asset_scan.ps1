# Deep Asset & Model Discovery across C:, D:, E:
$ErrorActionPreference = 'SilentlyContinue'

Write-Output "=== 1. SEARCHING FOR MODELFILES ACROSS DRIVES ==="
$modelfiles = @()
foreach ($drive in @('C:\', 'D:\', 'E:\')) {
    if (Test-Path $drive) {
        $found = Get-ChildItem -Path $drive -Recurse -Depth 4 -Filter "*Modelfile*" -ErrorAction SilentlyContinue | 
            Where-Object { $_.FullName -notmatch "node_modules|\.git|AppData|Windows" }
        $modelfiles += $found
    }
}
$modelfiles | Select-Object FullName, Length, LastWriteTime | Format-Table -AutoSize

Write-Output "`n=== 2. SEARCHING FOR COMFYUI INSTALLATIONS & ASSETS ==="
$comfyDirs = @()
foreach ($drive in @('C:\', 'D:\', 'E:\')) {
    if (Test-Path $drive) {
        $found = Get-ChildItem -Path $drive -Recurse -Depth 3 -Directory -Filter "*ComfyUI*" -ErrorAction SilentlyContinue |
            Where-Object { $_.FullName -notmatch "node_modules|\.git|AppData|Windows" }
        $comfyDirs += $found
    }
}
foreach ($cd in $comfyDirs) {
    $modelsPath = Join-Path $cd.FullName "models"
    $hasModels = Test-Path $modelsPath
    $size = [math]::Round(((Get-ChildItem -Path $cd.FullName -Recurse -Force -ErrorAction SilentlyContinue | Measure-Object -Property Length -Sum).Sum / 1GB), 2)
    Write-Output ("ComfyUI Dir: {0} (Total Size: {1} GB, Has models dir: {2})" -f $cd.FullName, $size, $hasModels)
    if ($hasModels) {
        Get-ChildItem -Path $modelsPath -Directory -ErrorAction SilentlyContinue | ForEach-Object {
            $subSize = [math]::Round(((Get-ChildItem -Path $_.FullName -Recurse -Force -ErrorAction SilentlyContinue | Measure-Object -Property Length -Sum).Sum / 1GB), 2)
            if ($subSize -gt 0.1) {
                Write-Output ("   - Subfolder {0,-20}: {1,6} GB" -f $_.Name, $subSize)
            }
        }
    }
}

Write-Output "`n=== 3. SEARCHING FOR HUGGING FACE CACHES & MODEL STORES ==="
foreach ($drive in @('C:\', 'D:\', 'E:\')) {
    if (Test-Path $drive) {
        $hfFound = Get-ChildItem -Path $drive -Recurse -Depth 3 -Directory -Filter "*huggingface*" -ErrorAction SilentlyContinue |
            Where-Object { $_.FullName -notmatch "node_modules|\.git" }
        foreach ($h in $hfFound) {
            $hSize = [math]::Round(((Get-ChildItem -Path $h.FullName -Recurse -Force -ErrorAction SilentlyContinue | Measure-Object -Property Length -Sum).Sum / 1GB), 2)
            Write-Output ("HF Dir: {0} ({1} GB)" -f $h.FullName, $hSize)
        }
    }
}

Write-Output "`n=== 4. SEARCHING FOR LARGE GGUF / SAFETENSORS / MODEL WEIGHTS (>1GB) ==="
$modelWeights = @()
foreach ($drive in @('C:\', 'D:\', 'E:\')) {
    if (Test-Path $drive) {
        $found = Get-ChildItem -Path $drive -Recurse -Depth 4 -File -ErrorAction SilentlyContinue | 
            Where-Object { 
                ($_.Extension -in @('.gguf', '.safetensors', '.bin', '.pt', '.pth', '.onnx')) -and
                ($_.Length -gt 1GB) -and
                ($_.FullName -notmatch "models\\ollama|node_modules|\.git|Windows")
            }
        $modelWeights += $found
    }
}
$modelWeights | Select-Object FullName, @{N='SizeGB';E={[math]::Round($_.Length/1GB,2)}}, LastWriteTime | Format-Table -AutoSize

Write-Output "`n=== 5. SEARCHING FOR SQLITE / SQLITE3 DATABASES ==="
$sqliteFiles = @()
foreach ($drive in @('C:\', 'D:\', 'E:\')) {
    if (Test-Path $drive) {
        $found = Get-ChildItem -Path $drive -Recurse -Depth 4 -File -ErrorAction SilentlyContinue | 
            Where-Object { 
                ($_.Extension -in @('.sqlite', '.sqlite3', '.db')) -and 
                ($_.FullName -notmatch "AppData|node_modules|\.git|Windows|Program Files|\.vscode|\.cargo|\.nuget|models\\ollama")
            }
        $sqliteFiles += $found
    }
}
$sqliteFiles | Select-Object FullName, @{N='SizeMB';E={[math]::Round($_.Length/1MB,2)}}, LastWriteTime | Format-Table -AutoSize

Write-Output "`n=== 6. SEARCHING FOR LOOSE AI-BS / TRAINING / ARCHIVE DOCUMENTS ON DESKTOP & USERPROFILE ==="
$docPaths = @(
    "$env:USERPROFILE\Desktop",
    "$env:USERPROFILE\OneDrive\Desktop",
    "$env:USERPROFILE\Documents",
    "$env:USERPROFILE\OneDrive\Documents",
    "D:\",
    "E:\"
)
$looseDocs = @()
foreach ($dp in $docPaths) {
    if (Test-Path $dp) {
        $found = Get-ChildItem -Path $dp -Depth 2 -File -ErrorAction SilentlyContinue |
            Where-Object {
                ($_.Extension -in @('.md', '.txt', '.pdf', '.docx', '.csv', '.json')) -and
                ($_.Name -match "AI|BS|train|model|sovereign|stehouwer|prompt|dataset|lead|crypto|fountain|script|screenplay") -and
                ($_.FullName -notmatch "node_modules|\.git|AppData|C:\\AI-BS")
            }
        $looseDocs += $found
    }
}
$looseDocs | Select-Object FullName, @{N='SizeKB';E={[math]::Round($_.Length/1KB,1)}}, LastWriteTime | Format-Table -AutoSize
