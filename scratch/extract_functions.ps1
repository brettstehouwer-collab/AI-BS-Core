$OutFile = "C:\AI-BS\function_manifest.txt"
Clear-Content $OutFile -ErrorAction SilentlyContinue

# Python Functions
Select-String -Path "C:\AI-BS\*.py" -Pattern "^\s*def\s+([a-zA-Z0-9_]+)" -Recurse | ForEach-Object { $_.Matches.Groups[1].Value } | Add-Content $OutFile

# Go Functions
Select-String -Path "C:\AI-BS\*.go" -Pattern "^\s*func\s+([a-zA-Z0-9_]+)" -Recurse | ForEach-Object { $_.Matches.Groups[1].Value } | Add-Content $OutFile

# TypeScript/React Functions
Select-String -Path "C:\AI-BS\*.ts", "C:\AI-BS\*.tsx" -Pattern "(function\s+[a-zA-Z0-9_]+|const\s+[a-zA-Z0-9_]+\s*=\s*\([^)]*\)\s*=>)" -Recurse | ForEach-Object { $_.Matches.Value } | Add-Content $OutFile

# Deduplicate
$UniqueFunctions = Get-Content $OutFile | Sort-Object -Unique
$UniqueFunctions | Set-Content $OutFile
