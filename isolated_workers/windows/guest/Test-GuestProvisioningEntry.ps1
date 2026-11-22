# Exercise the real entrypoint's refusal on this host. No installers may start.
$ErrorActionPreference='Stop'
$entry=Join-Path $PSScriptRoot 'Install-AIBSGuestRuntimes.ps1'
if(-not (Test-Path -LiteralPath $entry)){throw 'Required guest-only entrypoint is missing.'}
$tokens=$null; $errors=$null
$ast=[Management.Automation.Language.Parser]::ParseFile($entry,[ref]$tokens,[ref]$errors)
if(@($errors).Count){throw 'Entrypoint does not parse.'}
$parameters=@($ast.ParamBlock.Parameters.Name.VariablePath.UserPath)
if($parameters.Count -ne 1 -or $parameters[0] -ne 'MediaRoot'){throw 'Unexpected override/bypass parameter.'}
Write-Output 'PASS entrypoint has no identity bypass or host destination parameter'
$reportRoot='C:\AIBSGuestProvisioning'
$before=Get-Item -LiteralPath $reportRoot -ErrorAction SilentlyContinue
$exe=Join-Path $PSHOME 'powershell.exe'
if(-not (Test-Path -LiteralPath $exe)){$exe=Join-Path $PSHOME 'pwsh.exe'}
. (Join-Path $PSScriptRoot 'Guest-ProvisioningProcess.ps1')
$probe=Invoke-AIBSProvisionProcess -Executable $exe -Arguments @('-NoProfile','-File',$entry,'-MediaRoot','C:\AI-BS\') -TimeoutSeconds 15 -OutputBytes 4096
$code=$probe.ExitCode
if($code -ne 2 -or $probe.Stderr -notlike '*WRONG_GUEST*') {throw "Host was not rejected at its identity guard (exit $code)."}
$after=Get-Item -LiteralPath $reportRoot -ErrorAction SilentlyContinue
if(($null -eq $before) -ne ($null -eq $after)){throw 'Guest directory was created on the host.'}
if($before -and $before.LastWriteTimeUtc -ne $after.LastWriteTimeUtc){throw 'Existing host directory was changed.'}
Write-Output 'PASS real host invocation rejected before guest directory or installer launch'
$stateCalls=@($ast.FindAll({param($n) $n -is [Management.Automation.Language.CommandAst] -and $n.GetCommandName() -eq 'Open-AIBSProvisionState'},$true))
$installCalls=@($ast.FindAll({param($n) $n -is [Management.Automation.Language.CommandAst] -and $n.GetCommandName() -eq 'Run-ProvisionStep'},$true))
if($stateCalls.Count -ne 1 -or $installCalls.Count -lt 1 -or
   $stateCalls[0].Extent.EndOffset -ge ($installCalls.Extent.StartOffset | Measure-Object -Minimum).Minimum) {
    throw 'Durable single-attempt lease must precede every installer/verification process.'
}
Write-Output 'PASS actual orchestration acquires durable lease before native steps'
Write-Output 'RESULT 3 entrypoint tests passed; installation refused on host.'
