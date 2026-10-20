# Safe Drive C Space Reclamation & Transparent Model Migration
$ErrorActionPreference = 'Stop'

Write-Output "=== 1. PRE-FLIGHT DRIVE C AUDIT ==="
$cBefore = (Get-Volume -DriveLetter C).SizeRemaining / 1GB
Write-Output ("Drive C Free Space Before: {0:N2} GB" -f $cBefore)

# Step 1: Create Destination on Drive E
$destGGUF = "E:\AI_BS_Resources\Models\GGUF"
if (-not (Test-Path $destGGUF)) {
    New-Item -ItemType Directory -Path $destGGUF -Force | Out-Null
    Write-Output "Created: $destGGUF"
}

# Step 2: Relocate 3 GGUF files from custom_nodes to Drive E with Symlinks
$ggufFiles = @(
    "Qwen2.5-32B-Instruct-abliterated.Q5_K_M.gguf",
    "Dolphin3.0-Llama3.1-8B-Q8_0.gguf",
    "Hermes-3-Llama-3.1-8B.Q8_0.gguf"
)

foreach ($file in $ggufFiles) {
    $src = "C:\AI-BS\ComfyUI\custom_nodes\$file"
    $dst = "$destGGUF\$file"
    if (Test-Path $src) {
        $sizeGB = [math]::Round(((Get-Item $src).Length / 1GB), 2)
        Write-Output "Moving $file ($sizeGB GB) to $dst..."
        Move-Item -Path $src -Destination $dst -Force
        Write-Output "Creating symlink at $src pointing to $dst..."
        New-Item -ItemType SymbolicLink -Path $src -Target $dst -Force | Out-Null
        Write-Output " -> Relocated & symlinked successfully."
    } elseif (Test-Path $dst) {
        Write-Output "$file is already relocated on Drive E."
        if (-not (Test-Path $src)) {
            New-Item -ItemType SymbolicLink -Path $src -Target $dst -Force | Out-Null
        }
    }
}

# Step 3: Relocate C:\AI-BS-Models (root) to Drive E and create Junction
$rootModelsSrc = "C:\AI-BS-Models"
$rootModelsDst = "E:\AI_BS_Resources\Models\AI-BS-Models-RootBackup"
if ((Test-Path $rootModelsSrc) -and ((Get-Item $rootModelsSrc).LinkType -ne 'Junction')) {
    $sizeGB = [math]::Round(((Get-ChildItem -Path $rootModelsSrc -Recurse | Measure-Object -Property Length -Sum).Sum / 1GB), 2)
    Write-Output "Moving $rootModelsSrc ($sizeGB GB) to $rootModelsDst..."
    Move-Item -Path $rootModelsSrc -Destination $rootModelsDst -Force
    Write-Output "Creating directory junction from $rootModelsSrc to $rootModelsDst..."
    New-Item -ItemType Junction -Path $rootModelsSrc -Target $rootModelsDst -Force | Out-Null
    Write-Output " -> C:\AI-BS-Models junction established."
}

# Step 4: Purge duplicate download z_image_int8_convrot.safetensors
$dlFile = "C:\Users\footb\Downloads\z_image_int8_convrot.safetensors"
$vaultFile = "D:\AI-BS-ComfyUI-Models\unet\z_image_int8_convrot.safetensors"
if ((Test-Path $dlFile) -and (Test-Path $vaultFile)) {
    $dlLen = (Get-Item $dlFile).Length
    $vLen = (Get-Item $vaultFile).Length
    if ($dlLen -eq $vLen) {
        Write-Output "Purging duplicate in Downloads ($dlFile, $([math]::Round($dlLen/1GB, 2)) GB) - identical file safely in vault..."
        Remove-Item -Path $dlFile -Force
        Write-Output " -> Duplicate purged."
    }
}

# Step 5: Clean stale duplicate C:\Users\footb\AI-BS\ComfyUI if exists
$oldUserComfy = "C:\Users\footb\AI-BS\ComfyUI"
if (Test-Path $oldUserComfy) {
    Write-Output "Removing stale legacy user ComfyUI duplicate: $oldUserComfy..."
    Remove-Item -Path $oldUserComfy -Recurse -Force -ErrorAction SilentlyContinue
    Write-Output " -> Stale duplicate removed."
}

# Step 6: Clean temp & package caches
Write-Output "Cleaning ephemeral caches (pip, npm, temp)..."
try { pip cache purge 2>&1 | Out-Null } catch {}
try { npm cache clean --force 2>&1 | Out-Null } catch {}
Get-ChildItem -Path $env:TEMP -Recurse -Force -ErrorAction SilentlyContinue | Where-Object { $_.LastWriteTime -lt (Get-Date).AddDays(-1) } | Remove-Item -Recurse -Force -ErrorAction SilentlyContinue

# Audit After
Write-Output "`n=== POST-RECLAMATION DRIVE AUDIT ==="
$cAfter = (Get-Volume -DriveLetter C).SizeRemaining / 1GB
$reclaimed = $cAfter - $cBefore
Write-Output ("Drive C Free Space After : {0:N2} GB" -f $cAfter)
Write-Output ("TOTAL SPACE RECLAIMED   : {0:N2} GB" -f $reclaimed)
Get-Volume | Where-Object { $_.DriveType -eq 'Fixed' } | Select-Object DriveLetter, @{N='SizeGB';E={[math]::Round($_.Size/1GB,1)}}, @{N='FreeGB';E={[math]::Round($_.SizeRemaining/1GB,1)}}, @{N='PercentFree';E={[math]::Round(($_.SizeRemaining/$_.Size)*100,1)}} | Format-Table -AutoSize
