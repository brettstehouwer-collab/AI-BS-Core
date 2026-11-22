$dir = "C:\AI-BS\Ecosystem_Ledgers"
if (-not (Test-Path $dir)) { New-Item -ItemType Directory -Path $dir | Out-Null }
$files = @("SAVED_CHECKPOINT.md", "AI_BS_SAVED_CHECKPOINT.md", "ACTIVE_TASK.md", "AI_BS_MASTER_ARCHITECTURAL_LEDGER.md", "AI_BS_Global_Context.md", "AI_BS_Master_History_and_Tech_Spec.md")
foreach ($file in $files) {
    if (Test-Path "C:\AI-BS\$file") { 
        Move-Item -Path "C:\AI-BS\$file" -Destination "$dir\$file" -Force 
        Write-Host "Moved $file"
    } else {
        Write-Host "File not found: $file"
    }
}

$rule = "

GLOBAL CONTEXT ANCHOR: All historical ledgers, active task trackers, and saved checkpoints are strictly located in C:\AI-BS\Ecosystem_Ledgers\. Always read from and save to this directory to maintain ecosystem memory."
Add-Content -Path "C:\AI-BS\.antigravityrules" -Value $rule -Encoding UTF8
Write-Host "Appended Global Context Anchor"
