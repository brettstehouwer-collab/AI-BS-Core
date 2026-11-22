$drives = @("C:\AI-BS", "D:\", "E:\", "F:\", "G:\")
$resultsPath = "C:\AI-BS\scratch\deep_scan.txt"
if (!(Test-Path -Path (Split-Path $resultsPath))) { New-Item -ItemType Directory -Path (Split-Path $resultsPath) | Out-Null }
Set-Content -Path $resultsPath -Value "Deep Scan Started..."
foreach ($drive in $drives) {
    if (Test-Path $drive) {
        Add-Content -Path $resultsPath -Value "`n=== Scanning $drive ==="
        
        # Files
        Get-ChildItem -Path $drive -Recurse -File -Include *.sqlite,*.sqlite3,*.db,*.gguf,Modelfile -ErrorAction SilentlyContinue | Select-Object FullName, Length | Out-File -Append -FilePath $resultsPath
        
        # Folders
        Get-ChildItem -Path $drive -Recurse -Directory -ErrorAction SilentlyContinue | Where-Object { $_.Name -match "stehouwer|ai-bs|chroma" } | Select-Object FullName | Out-File -Append -FilePath $resultsPath
    }
}
Add-Content -Path $resultsPath -Value "`n=== Scan Complete ==="
