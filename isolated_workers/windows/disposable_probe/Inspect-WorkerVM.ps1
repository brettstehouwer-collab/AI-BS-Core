# Fixed provisioning observation, never an execution entry or VM mutation.
$ErrorActionPreference='Stop'
$root='C:\ProgramData\AI-BS-WorkerControl\disposable_probe_v1'
if([Security.Principal.WindowsIdentity]::GetCurrent().User.Value -cne 'S-1-5-21-2133766663-4066672948-2456486318-1006'){throw 'STANDARD_LAUNCHER_REQUIRED'}
$env:VBOX_USER_HOME=Join-Path $root 'vbox_home'
$vbox='C:\Program Files\Oracle\VirtualBox\VBoxManage.exe'
if((Get-FileHash -LiteralPath $vbox).Hash.ToLowerInvariant() -cne '178e016ed38cb6e369a5c17c6c960c176674b9c864030d8ce0ad2867613becff'){throw 'HYPERVISOR_CHANGED'}
foreach($argsList in @(@('showvminfo','e5a2fe34-7b90-460c-83af-903d51b4bb16','--machinereadable'),@('showmediuminfo','disk','5b4f5331-0da2-491d-a257-6b4ecf435a5a'))){
 $s=[Diagnostics.ProcessStartInfo]::new($vbox);$s.UseShellExecute=$false;$s.CreateNoWindow=$true;$s.RedirectStandardOutput=$true;$s.RedirectStandardError=$true
 foreach($a in $argsList){$s.ArgumentList.Add($a)}
 $p=[Diagnostics.Process]::Start($s);$out=$p.StandardOutput.ReadToEndAsync();$err=$p.StandardError.ReadToEndAsync()
 if(-not $p.WaitForExit(30000)){try{$p.Kill($true)}catch{};throw 'OWNED_INSPECTION_TIMEOUT'}
 $text=$out.GetAwaiter().GetResult();$errorText=$err.GetAwaiter().GetResult();if($text.Length+$errorText.Length -gt 131072){throw 'INSPECTION_OUTPUT_LIMIT'}
 if($p.ExitCode -ne 0){[IO.File]::WriteAllText((Join-Path $root ('worker_outputs\'+$argsList[0]+'.error.txt')),$errorText,[Text.UTF8Encoding]::new($false));throw 'INSPECTION_FAILED'}
 $name=if($argsList[0] -ceq 'showvminfo'){'current_vm.txt'}else{'current_medium.txt'}
 [IO.File]::WriteAllText((Join-Path $root ('worker_outputs\'+$name)),$text,[Text.UTF8Encoding]::new($false))
}
