# Setup recovery entrypoint; never claims Phase4 containment acceptance.
[CmdletBinding()]
param([switch]$Headless,[switch]$AutoApprove,[switch]$RecoverWorkerVM)
$ErrorActionPreference='Stop'
if ($AutoApprove) { throw 'AutoApprove cannot establish guest containment or Phase4 acceptance.' }
& 'C:\AI-BS\isolated_workers\windows\control\Recover-CurrentWorkerVM.ps1' -Recover:$RecoverWorkerVM
