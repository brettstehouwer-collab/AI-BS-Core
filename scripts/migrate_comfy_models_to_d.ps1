$source = "C:\AI-BS\ComfyUI\ComfyUI\models"
$dest = "D:\AI-BS-ComfyUI-Models"
$backupName = "C:\AI-BS\ComfyUI\ComfyUI\models_old_temp"

Write-Host "Step 1: Creating destination directory $dest..."
if (-not (Test-Path $dest)) {
    New-Item -ItemType Directory -Path $dest -Force | Out-Null
}

Write-Host "Step 2: Copying models using robocopy (multi-threaded fast transfer)..."
robocopy $source $dest /E /MT:16 /R:2 /W:2 /NP

if ($LASTEXITCODE -ge 8) {
    Write-Error "Robocopy failed with exit code $LASTEXITCODE. Aborting migration."
    exit 1
}

Write-Host "Step 3: Verifying destination content..."
$destItems = Get-ChildItem -Path $dest
if ($destItems.Count -eq 0) {
    Write-Error "Destination folder appears empty. Aborting junction creation."
    exit 1
}

Write-Host "Step 4: Renaming original models folder..."
Rename-Item -Path $source -NewName "models_old_temp"

Write-Host "Step 5: Creating NTFS Directory Junction..."
New-Item -ItemType Junction -Path $source -Target $dest

Write-Host "Step 6: Verifying junction link..."
$link = Get-Item -Path $source
if ($link.LinkType -eq "Junction") {
    Write-Host "Junction successfully established! Target: $($link.Target)"
    Write-Host "Step 7: Removing temporary original folder to release 190 GB on C: drive..."
    Remove-Item -Path $backupName -Recurse -Force
    Write-Host "Migration completed successfully!"
} else {
    Write-Error "Junction creation failed. Rolling back..."
    Rename-Item -Path $backupName -NewName "models"
    exit 1
}
