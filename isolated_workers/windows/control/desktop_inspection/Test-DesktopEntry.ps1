# Actual host-refusal infrastructure only. No VM command or guest task.
param([ValidateSet('pwsh','windows')][string]$Engine='pwsh')
$ErrorActionPreference='Stop'
$entry=Join-Path $PSScriptRoot '..\Inspect-CurrentWorkerDesktop.ps1'
if(-not(Test-Path -LiteralPath $entry -PathType Leaf)){throw 'MISSING_DESKTOP_INSPECTION_ENTRY'}
$identity=[Security.Principal.WindowsIdentity]::GetCurrent()
if($identity.User.Value -eq 'S-1-5-21-2133766663-4066672948-2456486318-1005'){throw 'HOST_REFUSAL_FIXTURE_MUST_NOT_RUN_AS_WORKER'}
$shell=if($Engine -eq 'windows'){'C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe'}else{'C:\Users\footb\.cache\codex-runtimes\codex-primary-runtime\dependencies\native\powershell\pwsh.exe'}
if(-not(Test-Path -LiteralPath $shell -PathType Leaf)){throw 'FIXED_TEST_SHELL_MISSING'}
$vmPath='C:\AI-BS\isolated_workers\windows\runtime\base_preparation_v2\vms\AI-BS-Eval-Base-20261023\AI-BS-Eval-Base-20261023.vbox'
$hashBefore=(Get-FileHash -LiteralPath $vmPath -Algorithm SHA256).Hash
$evidenceRoot='C:\AI-BS\isolated_workers\windows\runtime\desktop_inspection_v1'
$existsBefore=Test-Path -LiteralPath $evidenceRoot
foreach($extra in @('', ' -AutoApprove')){
    $p=New-Object Diagnostics.Process
    $p.StartInfo=New-Object Diagnostics.ProcessStartInfo
    $p.StartInfo.FileName=$shell
    $p.StartInfo.Arguments='-NoProfile -NonInteractive -File "'+$entry+'"'+$extra
    $p.StartInfo.UseShellExecute=$false;$p.StartInfo.CreateNoWindow=$true
    $p.StartInfo.RedirectStandardOutput=$true;$p.StartInfo.RedirectStandardError=$true
    if(-not $p.Start()){throw 'HOST_REFUSAL_PROCESS_NOT_STARTED'}
    if(-not $p.WaitForExit(15000)){try{$p.Kill()}catch{};throw 'HOST_REFUSAL_DEADLINE'}
    $out=$p.StandardOutput.ReadToEnd();$err=$p.StandardError.ReadToEnd()
    $expected=if($extra -eq ''){2}else{1}
    if($p.ExitCode -ne $expected){throw ('HOST_REFUSAL_EXIT_MISMATCH: expected '+$expected+', observed '+$p.ExitCode)}
    if($out.Length+$err.Length -gt 8192){throw 'HOST_REFUSAL_UNEXPECTED_OUTPUT'}
    Write-Output ('PASS '+$Engine+' actual nonworker entry ['+$extra.Trim()+'] exit='+$p.ExitCode)
    $p.Dispose()
}
if((Get-FileHash -LiteralPath $vmPath -Algorithm SHA256).Hash -ne $hashBefore){throw 'HOST_REFUSAL_CHANGED_VM_CONFIG'}
if((Test-Path -LiteralPath $evidenceRoot) -ne $existsBefore){throw 'HOST_REFUSAL_CREATED_EVIDENCE_BEFORE_IDENTITY'}
Write-Output ('PASS '+$Engine+' VM config and inspection-root presence unchanged')
Write-Output 'No guest/provider/transport acceptance; only actual host refusal verified.'
