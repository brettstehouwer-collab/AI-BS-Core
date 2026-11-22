# Fixed scheduled-task entry. Profile path/hash are pinned in the task action;
# the only per-run argument is a canonical, already authorized attempt UUID.
# No automatic task registration, credentials, accounts or VM creation here.
[CmdletBinding()]param(
    [Parameter(Mandatory)][string]$ProfilePath,
    [Parameter(Mandatory)][string]$ExpectedProfileSHA256,
    [Parameter(Mandatory)][string]$AttemptID
)
$ErrorActionPreference='Stop'
if($PSVersionTable.PSVersion.Major -lt 7){ throw 'POWERSHELL7_REQUIRED' }
Import-Module (Join-Path $PSScriptRoot 'DisposableProbe.psm1') -Force
$result=Invoke-AIBSWorkerProbe -ProfilePath $ProfilePath -ExpectedProfileSHA256 $ExpectedProfileSHA256 -AttemptID $AttemptID
$result|ConvertTo-Json -Depth 24 -Compress
if($result.state -cin @('PASSED','CANCELLED')){exit 0}
exit 2
