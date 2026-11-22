$paths = @("C:\Program Files", "C:\Program Files (x86)", "C:\Users\footb\AppData\Local\Programs", "E:\")
foreach ($path in $paths) {
    Get-ChildItem -Path $path -Filter "*AI-BS Matrix*" -Directory -ErrorAction SilentlyContinue | ForEach-Object { Write-Host $_.FullName }
    Get-ChildItem -Path $path -Filter "*ai-bs-frontend*" -Directory -ErrorAction SilentlyContinue | ForEach-Object { Write-Host $_.FullName }
}
