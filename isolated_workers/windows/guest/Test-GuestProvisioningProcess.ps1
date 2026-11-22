# Fixed trusted infrastructure probes only; no installer or generated project code.
$ErrorActionPreference='Stop'
$helper=Join-Path $PSScriptRoot 'Guest-ProvisioningProcess.ps1'
if (-not (Test-Path -LiteralPath $helper)) {throw 'Required bounded process helper is missing.'}
. $helper
$exe=Join-Path $PSHOME 'powershell.exe'
if (-not (Test-Path -LiteralPath $exe)) {$exe=Join-Path $PSHOME 'pwsh.exe'}
function Probe([string]$Code,[int]$Seconds=5,[int]$Bytes=4096) {
    $encoded=[Convert]::ToBase64String([Text.Encoding]::Unicode.GetBytes($Code))
    Invoke-AIBSProvisionProcess -Executable $exe -Arguments @('-NoProfile','-EncodedCommand',$encoded) -TimeoutSeconds $Seconds -OutputBytes $Bytes
}
$ok=Probe "[Console]::Write('verified'); [Console]::Error.Write('diagnostic'); exit 7"
if($ok.ExitCode -ne 7 -or $ok.Stdout -cne 'verified' -or $ok.Stderr -cne 'diagnostic') {throw 'Native return/output evidence was lost.'}
Write-Output 'PASS actual stdout/stderr and nonzero return retained'
$timeout=$false
try {Probe 'Start-Sleep -Seconds 10' 1 | Out-Null} catch {$timeout=$_.Exception.Message -like 'PROCESS_TIMEOUT_UNCONFIRMED*'}
if(-not $timeout){throw 'Deadline did not fail closed.'}
Write-Output 'PASS actual deadline fails closed (tree completion not claimed)'
$overflow=$false
try {Probe "[Console]::Write(('x' * 10000))" 5 128 | Out-Null} catch {$overflow=$_.Exception.Message -like 'PROCESS_OUTPUT_LIMIT_UNCONFIRMED*'}
if(-not $overflow){throw 'Output limit did not fail closed.'}
Write-Output 'PASS actual output cap fails closed'
$rejected=$false
try {Invoke-AIBSProvisionProcess -Executable $exe -Arguments @("bad`"argument") -TimeoutSeconds 5 -OutputBytes 1024 | Out-Null} catch {$rejected=$true}
if(-not $rejected){throw 'Unsafe argument accepted.'}
Write-Output 'PASS unsafe argument rejected before native launch'
Write-Output 'RESULT 4 process tests passed; no installers or project checks executed.'
