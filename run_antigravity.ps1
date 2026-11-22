$ErrorActionPreference = "Stop"
$StagingPath = "C:\AI-BS\scratch\antigravity_staging.py"
if (Test-Path -LiteralPath $StagingPath) {
    Get-Content -LiteralPath $StagingPath -Raw -Encoding UTF8
} else {
    Get-Clipboard -Raw
}

