$ErrorActionPreference = 'Stop'
$expectedSID = 'S-1-5-21-2133766663-4066672948-2456486318-1005'
$outputPath = 'C:\AI-BS\isolated_workers\windows\runtime\worker_identity.json'
try {
    $identity = [Security.Principal.WindowsIdentity]::GetCurrent()
    $principal = New-Object Security.Principal.WindowsPrincipal($identity)
    $isAdmin = $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
    $groups = & "$env:SystemRoot\System32\whoami.exe" /groups /fo csv /nh
    if ($LASTEXITCODE -ne 0) { throw 'Windows group query failed.' }
    $integrity = @([regex]::Matches(($groups -join "`n"),'S-1-16-\d+') | ForEach-Object { $_.Value } | Select-Object -Unique)
    $passed = $identity.User.Value -eq $expectedSID -and -not $isAdmin -and $integrity.Count -eq 1 -and $integrity[0] -eq 'S-1-16-8192'
    $process = Get-Process -Id $PID
    [ordered]@{
        Account=$identity.Name
        SID=$identity.User.Value
        PID=$PID
        CreationTimeUTC=$process.StartTime.ToUniversalTime().ToString('o')
        Administrator=$isAdmin
        IntegritySIDs=$integrity
        Passed=$passed
        TimestampUTC=[DateTime]::UtcNow.ToString('o')
        Scope='Identity probe only; no guest or task execution'
    } | ConvertTo-Json -Depth 4 | Set-Content -LiteralPath $outputPath -Encoding UTF8
    if (-not $passed) { throw 'Worker identity is not the expected standard account at medium integrity. Stop here.' }
    Write-Host 'Identity check passed. Return to Codex and leave this window open for independent verification.' -ForegroundColor Green
} catch {
    Write-Host $_.Exception.Message -ForegroundColor Red
    Write-Host 'Identity check did not complete successfully. Return to Codex.'
} finally {
    Read-Host 'Press Enter only after Codex verifies this process' | Out-Null
}
