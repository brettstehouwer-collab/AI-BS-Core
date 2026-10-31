<# Run the reviewed audit checks. Use -ListOnly to inspect the plan without execution. #>
[CmdletBinding()]
param(
    [ValidateSet('All','Python','Clients','TypeScript','Versions')]
    [string[]]$Check = @('All'),
    [switch]$ListOnly,
    [string]$EvidenceRoot = 'E:\AI_BS_Resources\AI-BS-Audit\2026-10-30-complete\evidence'
)
$ErrorActionPreference = 'Stop'
$repoRoot = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..'))
$nodeExecutable = (Get-Command node.exe -ErrorAction Stop).Source
$holds = @{
    DRY_RUN = 'true'; HOLD_DISPATCH = 'true'; AIBS_PAYMENT_MODE = 'disabled'
    AI_BS_BACKEND_MANAGE_DAEMONS = 'false'; AI_BS_BACKEND_BACKGROUND_ENABLED = 'false'
    AI_BS_RECDEBUT_OUTBOUND_ENABLED = 'false'; RECDEBUT_SENDING_ENABLED = 'false'
    AI_BS_RECDEBUT_INBOUND_POLLING_ENABLED = 'false'; RECDEBUT_REPLY_FORWARDING_ENABLED = 'false'
    AI_BS_DISCORD_NOTIFICATIONS_ENABLED = 'false'; PYTHONIOENCODING = 'utf-8'
}
$jobs = @(
    @{
        Name = 'Python'; Executable = (Join-Path $repoRoot 'pyppeteer_env\Scripts\python.exe')
        Arguments = @('-m','unittest',
            'scripts.tests.test_contained_file_access','scripts.tests.test_host_control_containment',
            'scripts.tests.test_legacy_financial_privacy','scripts.tests.test_native_telemetry_truth',
            'scripts.tests.test_media_pipeline_and_signing_integrity','scripts.tests.test_route_registration_integrity',
            'scripts.tests.test_creation_document_save','scripts.tests.test_document_revision_safety',
            'scripts.tests.test_crypto_integrity_containment','scripts.tests.test_crypto_execution_controls',
            'scripts.tests.test_audit_batch_runner198')
    },
    @{
        Name = 'Clients'; Executable = $nodeExecutable
        Arguments = @('--test','scripts/tests/test_financial_media_truth_client.mjs',
            'scripts/tests/test_runtime_truthfulness_client.mjs','scripts/tests/test_independent_service_containment.mjs',
            'scripts/tests/test_daw_contracts198.cjs','scripts/tests/test_broadcast_contracts198.cjs','scripts/tests/test_user_session_telemetry198.cjs')
    },
    @{
        Name = 'TypeScript'; Executable = $nodeExecutable
        Arguments = @((Join-Path $repoRoot 'frontend\node_modules\typescript\bin\tsc'),
            '--noEmit','--pretty','false','-p',(Join-Path $repoRoot 'frontend\tsconfig.json'))
    },
    @{
        Name = 'Versions'; Executable = $nodeExecutable
        Arguments = @((Join-Path $repoRoot 'scripts\release-version.cjs'),'check')
    }
)
if ($Check -notcontains 'All') { $jobs = @($jobs | Where-Object { $Check -contains $_.Name }) }
if ($ListOnly) {
    @{ Jobs = $jobs; Holds = $holds; WorkingDirectory = $repoRoot; ExternalDispatch = $false } | ConvertTo-Json -Depth 6
    exit 0
}
$runDirectory = Join-Path ([IO.Path]::GetFullPath($EvidenceRoot)) ('batch_' + [DateTime]::UtcNow.ToString('yyyyMMddTHHmmssZ') + '_' + [Guid]::NewGuid().ToString('N').Substring(0,8))
New-Item -Path $runDirectory -ItemType Directory -ErrorAction Stop | Out-Null
$previousEnvironment = @{}
$results = @()
$previousLocation = Get-Location
try {
    foreach ($name in $holds.Keys) {
        $previousEnvironment[$name] = [Environment]::GetEnvironmentVariable($name,'Process')
        [Environment]::SetEnvironmentVariable($name,$holds[$name],'Process')
    }
    Set-Location -LiteralPath $repoRoot
    foreach ($job in $jobs) {
        $started = [DateTime]::UtcNow
        $logPath = Join-Path $runDirectory ($job.Name + '.log')
        $exitCode = 1
        try {
            if (-not (Test-Path -LiteralPath $job.Executable -PathType Leaf)) { throw 'Reviewed executable is unavailable.' }
            $arguments = $job.Arguments
            # Native stderr is captured as diagnostics; only its exit status
            # determines the result. Windows PowerShell otherwise promotes
            # ordinary unittest stderr into terminating ErrorRecords.
            $ErrorActionPreference = 'Continue'
            & $job.Executable @arguments *> $logPath
            $exitCode = $LASTEXITCODE
            $ErrorActionPreference = 'Stop'
        } catch {
            $ErrorActionPreference = 'Stop'
            'Audit check could not start. Inspect the reviewed executable and arguments.' | Add-Content -LiteralPath $logPath
        }
        $row = @{ Name = $job.Name; ExitCode = $exitCode; Log = $logPath;
            StartedUtc = $started.ToString('o'); FinishedUtc = [DateTime]::UtcNow.ToString('o') }
        $results += $row
        Write-Host ($job.Name + ': exit ' + $exitCode)
    }
} finally {
    Set-Location -LiteralPath $previousLocation.Path
    foreach ($name in $holds.Keys) { [Environment]::SetEnvironmentVariable($name,$previousEnvironment[$name],'Process') }
}
$failed = @($results | Where-Object { $_.ExitCode -ne 0 })
@{ Results = $results; Failed = $failed.Count; ExternalDispatch = $false; Holds = $holds } |
    ConvertTo-Json -Depth 6 | Set-Content -LiteralPath (Join-Path $runDirectory 'summary.json') -Encoding utf8
Write-Host ('Evidence: ' + $runDirectory)
if ($failed.Count -gt 0) { exit 1 }
exit 0
