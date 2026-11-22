$content = @"

## Matrix IDE v6.4.0 Architectural Standards & Global Rules
*   **Rule 1: The Thoughtful Friction Gate:** All autonomous IDE code execution must route through the Plan-Review-Execute frontend pipeline (`/v1/ide/plan` -> `<AgentPlanReviewCard/>`).
*   **Rule 2: Auditor Admin Bypass:** Executions triggered via the UI's `[Accept & Execute Plan]` button explicitly pass `user_approved=True` to `execute_polyglot_command()`, permanently bypassing the automated Stehouwer Reality Standard Auditor rejection for manual operations.
*   **Rule 3: Immutable Audit Trail:** Every executed plan must automatically generate a JSON log artifact stored strictly inside `C:\AI-BS\Agent_Implementation_Plans_History\`.
*   **Rule 4: Boot/Shutdown Stabilization:** Launch/Shutdown scripts (`Launch_AI_BS.bat` & `Shutdown_AI_BS.bat`) are globally mandated to use padded daemons timings (5-15s per service) to prevent VRAM race conditions, and must actively terminate `nginx.exe` to prevent port squatting.
*   **Rule 5: Hybrid Compute Bridge:** The backend execution engine operates on a bridged WSL architecture with 16 physical cores and 32GB RAM explicitly carved out from the AMD Ryzen 9 9950X, uniting local sovereign compute with external Clore.ai/Vast.ai GPU swarms.
"@

$files = @(
    "C:\AI-BS\SAVED_CHECKPOINT.md",
    "C:\AI-BS\AI_BS_SAVED_CHECKPOINT.md",
    "C:\AI-BS\ACTIVE_TASK.md",
    "C:\AI-BS\AI_BS_MASTER_ARCHITECTURAL_LEDGER.md",
    "C:\AI-BS\AI_BS_Global_Context.md",
    "C:\AI-BS\AI_BS_Master_History_and_Tech_Spec.md"
)

foreach ($file in $files) {
    if (Test-Path $file) {
        Add-Content -Path $file -Value $content -Encoding UTF8
        Write-Host "Appended to $file"
    } else {
        Set-Content -Path $file -Value $content -Encoding UTF8
        Write-Host "Created and appended to $file"
    }
}
