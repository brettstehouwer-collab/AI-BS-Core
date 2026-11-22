# One-time bounded diagnostic-only profile revision; never touches an existing guest.
$ErrorActionPreference='Stop'
$root='C:\ProgramData\AI-BS-WorkerControl\disposable_probe_v1'
$vm='e5a2fe34-7b90-460c-83af-903d51b4bb16'
if([Security.Principal.WindowsIdentity]::GetCurrent().User.Value -cne 'S-1-5-21-2133766663-4066672948-2456486318-1006'){throw 'STANDARD_LAUNCHER_REQUIRED'}
if(Test-Path -LiteralPath (Join-Path $root 'worker_state\installation.started')){throw 'INSTALL_ALREADY_STARTED'}
$env:VBOX_USER_HOME=Join-Path $root 'vbox_home'
$vbox='C:\Program Files\Oracle\VirtualBox\VBoxManage.exe'
if((Get-FileHash -LiteralPath $vbox).Hash.ToLowerInvariant() -cne '178e016ed38cb6e369a5c17c6c960c176674b9c864030d8ce0ad2867613becff'){throw 'HYPERVISOR_CHANGED'}
function Run([string[]]$Arguments){
 $s=[Diagnostics.ProcessStartInfo]::new($vbox);$s.UseShellExecute=$false;$s.CreateNoWindow=$true;$s.RedirectStandardOutput=$true;$s.RedirectStandardError=$true
 foreach($a in $Arguments){$s.ArgumentList.Add($a)}
 $p=[Diagnostics.Process]::Start($s);$o=$p.StandardOutput.ReadToEndAsync();$e=$p.StandardError.ReadToEndAsync()
 if(-not $p.WaitForExit(30000)){try{$p.Kill($true)}catch{};throw 'OWNED_PROFILE_REVISION_TIMEOUT'}
 $text=$o.GetAwaiter().GetResult();$err=$e.GetAwaiter().GetResult();if($text.Length+$err.Length -gt 131072 -or $p.ExitCode -ne 0){throw 'PROFILE_REVISION_COMMAND_FAILED'};return $text
}
$before=Run @('showvminfo',$vm,'--machinereadable')
if($before -notmatch ('(?m)^UUID="'+$vm+'"\r?$') -or $before -notmatch '(?m)^VMState="poweroff"\r?$' -or $before -notmatch '(?m)^memory=8192\r?$'){throw 'EXACT_NEW_POWERED_OFF_VM_REQUIRED'}
$plan=Get-Content -LiteralPath (Join-Path $root 'policy\provisioning.json') -Raw|ConvertFrom-Json
if($plan.vm_uuid -cne $vm -or $plan.vm_memory_mib -ne 4096 -or $plan.vm_cpus -ne 4 -or $plan.general_worker_admission -or $plan.apply_authorized){throw 'REVIEWED_DIAGNOSTIC_PROFILE_REQUIRED'}
$evidence=Join-Path $root ('worker_outputs\memory_revision_'+[DateTime]::UtcNow.ToString('yyyyMMddTHHmmssZ'))
[IO.File]::WriteAllText(($evidence+'.before.txt'),$before)
$null=Run @('modifyvm',$vm,'--memory=4096')
$after=Run @('showvminfo',$vm,'--machinereadable')
if($after -notmatch '(?m)^memory=4096\r?$' -or $after -notmatch '(?m)^VMState="poweroff"\r?$'){throw 'PROFILE_REVISION_READBACK_FAILED'}
[IO.File]::WriteAllText(($evidence+'.after.txt'),$after)
[IO.File]::WriteAllText((Join-Path $root 'worker_outputs\prepared_vm.txt'),$after)
Write-Output 'DIAGNOSTIC_ONLY_4096_MIB_POWERED_OFF'
