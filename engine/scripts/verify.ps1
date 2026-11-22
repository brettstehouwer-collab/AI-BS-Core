param(
    [ValidateSet('Debug','Release')][string]$Configuration = 'Debug',
    [string]$EvidenceRoot = '',
    [string]$TempRoot = ''
)
$ErrorActionPreference = 'Stop'
$engineRoot = Split-Path -Parent $PSScriptRoot
$preset = $Configuration.ToLowerInvariant()
$engineProject = Get-Content -LiteralPath (Join-Path $engineRoot 'CMakeLists.txt') -Raw
$versionMatch = [regex]::Match($engineProject, 'project\(AIBSEngine VERSION ([0-9]+\.[0-9]+\.[0-9]+)')
if (-not $versionMatch.Success) { throw 'Cannot determine the SDK version for an isolated installation' }
$engineVersion = $versionMatch.Groups[1].Value
$progressScript = Join-Path $PSScriptRoot 'report_progress.py'
$outRoot = Join-Path $engineRoot 'out'
New-Item -ItemType Directory -Force -Path $outRoot | Out-Null
$buildLock = [System.IO.File]::Open((Join-Path $outRoot 'verification.lock'), [System.IO.FileMode]::OpenOrCreate, [System.IO.FileAccess]::ReadWrite, [System.IO.FileShare]::None)
$sharedLogPath = Join-Path $outRoot 'verification.log'
$runRoot = $null
$logPath = $null
$sdkPrefix = $null
$consumerBuild = $null
$runTemp = $null
$nativeTestsStarted = $false
$previousTemp = $env:TEMP
$previousTmp = $env:TMP
$startedUtc = [DateTime]::UtcNow.ToString('o')
$status = 'failed'
$script:lastCMakeExitCode = $null
function Publish-Progress([string]$Status, [string]$Stage) {
    & python $progressScript $Configuration $Status $Stage
    if ($LASTEXITCODE -ne 0) { throw 'Could not publish build progress' }
}
function Invoke-CMake {
    param([Parameter(ValueFromRemainingArguments=$true)][string[]]$CMakeArguments)
    # Retain complete native stderr under Windows PowerShell before checking RC.
    $previousPreference = $ErrorActionPreference
    try {
        $ErrorActionPreference = 'Continue'
        & python -m cmake @CMakeArguments 2>&1 | ForEach-Object {
            # Tee-Object in Windows PowerShell appends UTF-16 regardless of the
            # UTF-8 header. Explicit encoding keeps every retained run readable.
            $line = $_.ToString()
            Add-Content -LiteralPath $logPath -Value $line -Encoding utf8
            Add-Content -LiteralPath $sharedLogPath -Value $line -Encoding utf8
            Write-Output $line
        }
        $script:lastCMakeExitCode = $LASTEXITCODE
    } finally {
        $ErrorActionPreference = $previousPreference
    }
    if ($script:lastCMakeExitCode -ne 0) { throw "CMake failed with exit code $script:lastCMakeExitCode" }
}
Push-Location $engineRoot
try {
    # Explicit root wins; otherwise retain the user's cached base, then default.
    $configuredBase = $EvidenceRoot
    if (-not $configuredBase) {
        $cache = Join-Path $outRoot 'windows-msvc/CMakeCache.txt'
        if (Test-Path -LiteralPath $cache) {
            foreach ($line in [System.IO.File]::ReadLines($cache)) {
                if ($line -match '^AIBS_EVIDENCE_ROOT:[^=]+=(.*)$') { $configuredBase = $Matches[1]; break }
            }
        }
    }
    if (-not $configuredBase) { $configuredBase = $outRoot }
    if (-not [System.IO.Path]::IsPathRooted($configuredBase)) { $configuredBase = Join-Path $engineRoot $configuredBase }
    $configuredBase = [System.IO.Path]::GetFullPath($configuredBase)
    # Native fixtures include hash-addressed assets and retained UUID suffixes.
    # Compact IDs leave room under legacy Win32 MAX_PATH; UTC is in the receipt.
    $runId = [Guid]::NewGuid().ToString('N').Substring(0,12)
    $runRoot = Join-Path $configuredBase "v/$runId"
    New-Item -ItemType Directory -Path $runRoot | Out-Null
    $runEvidence = Join-Path $runRoot 'e'
    New-Item -ItemType Directory -Path $runEvidence | Out-Null
    $logPath = Join-Path $runRoot 'verification.log'
    $heading = "Starting $Configuration verification $runId; evidence: $runEvidence"
    Set-Content -LiteralPath $logPath -Value $heading -Encoding utf8
    Add-Content -LiteralPath $sharedLogPath -Value $heading -Encoding utf8
    if ($runEvidence.Length -gt 36) {
        throw "Native verification evidence path is too long ($($runEvidence.Length) characters; maximum 36). Use a short -EvidenceRoot such as $outRoot. No build or tests were started."
    }
    # Keep legacy native fixtures short and private to this verification run.
    # Do not depend on a particular user's profile or discard temporary evidence.
    if (-not $TempRoot) { $TempRoot = Join-Path (Split-Path -Parent $engineRoot) 't' }
    $runTemp = [System.IO.Path]::GetFullPath((Join-Path $TempRoot "nv$runId"))
    if ($runTemp.Length -gt 36) {
        throw "Native temporary path is too long ($($runTemp.Length) characters; maximum 36). Supply a short -TempRoot. No build or tests were started."
    }
    New-Item -ItemType Directory -Force -Path (Split-Path -Parent $runTemp) | Out-Null
    New-Item -ItemType Directory -Path $runTemp | Out-Null
    $env:TEMP = $runTemp
    $env:TMP = $runTemp
    Publish-Progress running starting
    Invoke-CMake --preset windows-msvc "-DAIBS_VERIFICATION_EVIDENCE_ROOT=$runEvidence"
    Publish-Progress running configured
    Invoke-CMake --build --preset $preset
    Publish-Progress running compiled
    $nativeTestsStarted = $true
    Invoke-CMake --build out/windows-msvc --config $Configuration --target RUN_TESTS
    Publish-Progress running native-window-dx12-gpu-verified
    Publish-Progress running grounded-obstacle-course-verified
    Publish-Progress running persistent-visible-world-verified
    Publish-Progress running checkpoint-restart-recovery-passed
    Publish-Progress running engine-tests-passed
    $sdkPrefix = Join-Path $runRoot "sdk/$engineVersion/$preset"
    Invoke-CMake --install out/windows-msvc --config $Configuration --prefix $sdkPrefix
    Publish-Progress running sdk-installed
    $consumerBuild = Join-Path $runRoot 'sdk-consumer'
    Invoke-CMake -S examples/sdk_consumer -B $consumerBuild -G 'Visual Studio 17 2022' -A x64 "-DCMAKE_PREFIX_PATH=$sdkPrefix"
    Invoke-CMake --build $consumerBuild --config $Configuration
    Invoke-CMake --build $consumerBuild --config $Configuration --target RUN_TESTS
    Publish-Progress passed installed-sdk-consumer-tested
    $status = 'passed'
} catch {
    if ($logPath) { Add-Content -LiteralPath $logPath -Value $_.Exception.Message -Encoding utf8 }
    Publish-Progress failed $_.Exception.Message
    throw
} finally {
    try {
        if ($runRoot -and (Test-Path -LiteralPath $runRoot -PathType Container)) {
            $nativeLog = Join-Path $outRoot 'windows-msvc/Testing/Temporary/LastTest.log'
            if ($nativeTestsStarted -and (Test-Path -LiteralPath $nativeLog)) {
                $observedLog = Get-Item -LiteralPath $nativeLog
                if ($observedLog.LastWriteTimeUtc -ge [DateTime]::Parse($startedUtc).ToUniversalTime()) {
                    Copy-Item -LiteralPath $nativeLog -Destination (Join-Path $runRoot 'native-LastTest.log')
                }
            }
            if ($consumerBuild) {
                $consumerLog = Join-Path $consumerBuild 'Testing/Temporary/LastTest.log'
                if (Test-Path -LiteralPath $consumerLog) { Copy-Item -LiteralPath $consumerLog -Destination (Join-Path $runRoot 'consumer-LastTest.log') }
            }
            [ordered]@{
                schema_version = 1; status = $status; run_id = $runId
                configuration = $Configuration; sdk_version = $engineVersion
                started_utc = $startedUtc; completed_utc = [DateTime]::UtcNow.ToString('o')
                configured_evidence_base = $configuredBase; evidence_root = $runEvidence
                log_path = $logPath; last_cmake_exit_code = $script:lastCMakeExitCode
                sdk_prefix = $sdkPrefix; consumer_build = $consumerBuild
                temporary_root = $runTemp
            } | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $runRoot 'verification.json') -Encoding utf8
        }
    } finally {
        $env:TEMP = $previousTemp
        $env:TMP = $previousTmp
        Pop-Location
        $buildLock.Dispose()
    }
}
