# Drive and Asset Audit Script
Write-Output "=== DISK DRIVES STATUS ==="
Get-Volume | Where-Object { $_.DriveType -eq 'Fixed' } | Select-Object DriveLetter, FileSystemLabel, @{N='SizeGB';E={[math]::Round($_.Size/1GB,1)}}, @{N='FreeGB';E={[math]::Round($_.SizeRemaining/1GB,1)}}, @{N='PercentFree';E={[math]::Round(($_.SizeRemaining/$_.Size)*100,1)}} | Format-Table -AutoSize

Write-Output "`n=== OLLAMA INSTALLED MODELS (Port 11434 / Default) ==="
try {
    ollama list
} catch {
    Write-Output "Ollama CLI call error: $_"
}

Write-Output "`n=== POTENTIAL SAFE CLEANUP TARGETS ==="
$cleanupTargets = @(
    @{ Name = "User Temp"; Path = $env:TEMP },
    @{ Name = "Windows Temp"; Path = "C:\Windows\Temp" },
    @{ Name = "Crash Dumps"; Path = "$env:LOCALAPPDATA\CrashDumps" },
    @{ Name = "Pip Cache"; Path = "$env:LOCALAPPDATA\pip\cache" },
    @{ Name = "NPM Cache"; Path = "$env:LOCALAPPDATA\npm-cache" },
    @{ Name = "HF Cache (User)"; Path = "$env:USERPROFILE\.cache\huggingface" },
    @{ Name = "AI-BS Ollama Dir"; Path = "C:\AI-BS\models\ollama" },
    @{ Name = "Legacy User Ollama"; Path = "$env:USERPROFILE\.ollama" },
    @{ Name = "C:\AI-BS\frontend\dist"; Path = "C:\AI-BS\frontend\dist" },
    @{ Name = "C:\AI-BS\dist"; Path = "C:\AI-BS\dist" },
    @{ Name = "C:\AI-BS\build"; Path = "C:\AI-BS\build" }
)

foreach ($target in $cleanupTargets) {
    if (Test-Path $target.Path) {
        $sizeBytes = (Get-ChildItem -Path $target.Path -Recurse -Force -ErrorAction SilentlyContinue | Measure-Object -Property Length -Sum).Sum
        $sizeGB = [math]::Round(($sizeBytes / 1GB), 2)
        Write-Output ("- {0,-25} : {1,8} GB  ({2})" -f $target.Name, $sizeGB, $target.Path)
    } else {
        Write-Output ("- {0,-25} : [Not Found] ({1})" -f $target.Name, $target.Path)
    }
}
