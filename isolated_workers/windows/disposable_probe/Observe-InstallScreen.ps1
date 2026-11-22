# One fixed new-VM observation. No guest input, starts, stops or account changes.
[CmdletBinding()]
param([switch]$Observe)
Set-StrictMode -Version Latest
$ErrorActionPreference='Stop'
$root='C:\ProgramData\AI-BS-WorkerControl\disposable_probe_v1'
$vm='e5a2fe34-7b90-460c-83af-903d51b4bb16'
$vbox='C:\Program Files\Oracle\VirtualBox\VBoxManage.exe'
$vboxHash='178e016ed38cb6e369a5c17c6c960c176674b9c864030d8ce0ad2867613becff'
function Require([bool]$Condition,[string]$Code){if(-not $Condition){throw [InvalidOperationException]::new($Code)}}
function Parse-ObservedMachine([string]$Text){
 Require ([Text.Encoding]::UTF8.GetByteCount($Text) -le 131072) 'VM_INFO_BOUND'
 $map=[Collections.Generic.Dictionary[string,string]]::new([StringComparer]::Ordinal)
 foreach($line in ($Text -split '\r?\n')){
  if(-not $line){continue};if($line -cmatch '\A rec_screen[0-9]+\z'){continue}
  Require ($line -cmatch '\A([^=\r\n]+)=(.*)\z') 'MALFORMED_VM_INFO'
  $key=$Matches[1].Trim('"');$value=$Matches[2].Trim('"')
  Require (-not $map.ContainsKey($key)) 'DUPLICATE_VM_PROPERTY';$map.Add($key,$value)
 }
 return ,$map
}
function Verify-ObservedMachine($Map){
 foreach($pair in @(@('UUID',$vm),@('name','AI-BS-DisposableProbe-20261026'),@('memory','4096'),@('cpus','4'),@('firmware','EFI'),@('SecureBoot','on'),@('clipboard','disabled'),@('clipboard_file_transfers','off'),@('draganddrop','disabled'),@('vrde','off'),@('usb','off'),@('audio','none'),@('audio_in','off'),@('audio_out','off'))){Require ($Map.ContainsKey($pair[0]) -and $Map[$pair[0]] -ceq $pair[1]) ('VM_POLICY_'+$pair[0])}
 Require ($Map.ContainsKey('VMState') -and $Map['VMState'] -cin @('running','poweroff')) 'OBSERVABLE_STATE_REQUIRED'
 foreach($n in 1..8){Require ($Map.ContainsKey('nic'+$n) -and $Map['nic'+$n] -ceq 'none') 'NO_GUEST_NICS_REQUIRED'}
 foreach($n in 1..4){Require ($Map.ContainsKey('uart'+$n) -and $Map['uart'+$n] -ceq 'off') 'NO_GUEST_UART_REQUIRED'}
 foreach($key in $Map.Keys){Require ($key -notmatch '^SharedFolder') 'SHARED_FOLDER_REFUSED'}
}
function New-ObservationCommandRecord([string[]]$Arguments,[byte[]]$Stdout,[byte[]]$Stderr,$ExitCode,[string]$ErrorCode,[long]$ElapsedMilliseconds,[bool]$TerminationConfirmed){
 Require ($Stdout.Length+$Stderr.Length -le 131072) 'RETAINED_CONSOLE_BOUND'
 [ordered]@{schema_version=1;classification='PRIVATE_INSTALLATION_OBSERVATION_EXCLUDE_FROM_LEDGER';vm_id=$vm;operation=$Arguments[0];argument_count=$Arguments.Count;arguments_sha256=[Convert]::ToHexString([Security.Cryptography.SHA256]::HashData([Text.Encoding]::UTF8.GetBytes(($Arguments|ConvertTo-Json -Compress)))).ToLowerInvariant();exit_code=$ExitCode;error_code=$ErrorCode;elapsed_ms=$ElapsedMilliseconds;termination_confirmed=$TerminationConfirmed;stdout_base64=[Convert]::ToBase64String($Stdout);stderr_base64=[Convert]::ToBase64String($Stderr);combined_bytes=$Stdout.Length+$Stderr.Length;utc=[DateTime]::UtcNow.ToString('o')}
}
if(-not $Observe){[pscustomobject]@{state='DESCRIBE_ONLY';vm_id=$vm;operation='ONE_SCREENSHOT_AND_MACHINE_STATE';guest_input=$false;vm_start_stop=$false;candidate_execution=$false}|ConvertTo-Json;return}
Require ($PSVersionTable.PSVersion.Major -ge 7) 'PROTECTED_POWERSHELL7_REQUIRED'
$plan=Get-Content -LiteralPath (Join-Path $root 'policy\provisioning.json') -Raw|ConvertFrom-Json
Require ($plan.schema_version -eq 1 -and $plan.root -ceq $root -and $plan.vm_uuid -ceq $vm -and $plan.forbidden_vm_uuid -ceq '6c5a53da-ab80-4ecb-8be6-4059266f736e' -and $plan.vm_name -ceq 'AI-BS-DisposableProbe-20261026' -and $plan.vbox_path -ceq $vbox -and $plan.vbox_sha256 -ceq $vboxHash -and $plan.vbox_user_home -ceq (Join-Path $root 'vbox_home') -and $plan.network -ceq 'none' -and -not $plan.general_worker_admission -and -not $plan.apply_authorized) 'EXACT_NEW_VM_PLAN_REQUIRED'
$identity=[Security.Principal.WindowsIdentity]::GetCurrent();$principal=[Security.Principal.WindowsPrincipal]$identity
Require ($identity.User.Value -ceq $plan.dispatcher_sid -and $identity.User.Value -ceq 'S-1-5-21-2133766663-4066672948-2456486318-1006' -and -not $principal.IsInRole('Administrators')) 'EXACT_STANDARD_HOST_LAUNCHER_REQUIRED'
$env:VBOX_USER_HOME=$plan.vbox_user_home
$held=$null;$attempt=$null;$script:ObservationSequence=0
function VBox-Observe([string[]]$Arguments){
 # The only callers below construct fixed showvminfo/screenshot argument vectors.
 $s=[Diagnostics.ProcessStartInfo]::new($vbox);$s.UseShellExecute=$false;$s.CreateNoWindow=$true;$s.RedirectStandardOutput=$true;$s.RedirectStandardError=$true;$s.RedirectStandardInput=$true
 $s.Environment.Clear();foreach($name in @('SystemRoot','WINDIR')){$s.Environment[$name]='C:\Windows'};$s.Environment['PATH']='C:\Windows\System32;C:\Windows';$s.Environment['VBOX_USER_HOME']=$plan.vbox_user_home;$s.Environment['TEMP']=Join-Path $root 'worker_state';$s.Environment['TMP']=Join-Path $root 'worker_state'
 foreach($a in $Arguments){$s.ArgumentList.Add($a)}
 $p=[Diagnostics.Process]::new();$p.StartInfo=$s;$o=[IO.MemoryStream]::new();$e=[IO.MemoryStream]::new();$started=$false;$commandError='';$exitCode=$null;$timer=[Diagnostics.Stopwatch]::StartNew();$script:ObservationSequence++
 try{
  Require ($p.Start()) 'OBSERVATION_PROCESS_START_FAILED';$started=$true;$p.StandardInput.Close()
  $ob=[byte[]]::new(4096);$eb=[byte[]]::new(4096);$os=$p.StandardOutput.BaseStream;$es=$p.StandardError.BaseStream
  $ot=$os.ReadAsync($ob,0,$ob.Length);$et=$es.ReadAsync($eb,0,$eb.Length);$oo=$true;$eo=$true
  while($oo -or $eo -or -not $p.HasExited){
   Require ($timer.Elapsed.TotalSeconds -lt 10) 'OBSERVATION_COMMAND_TIMEOUT'
   foreach($kind in @('out','err')){
    $task=if($kind -ceq 'out'){$ot}else{$et};$open=if($kind -ceq 'out'){$oo}else{$eo}
    if($open -and $task.IsCompleted){
     $read=$task.GetAwaiter().GetResult()
     if($read -eq 0){if($kind -ceq 'out'){$oo=$false}else{$eo=$false}}
     else{Require ($o.Length+$e.Length+$read -le 131072) 'OBSERVATION_CONSOLE_LIMIT';if($kind -ceq 'out'){$o.Write($ob,0,$read);$ot=$os.ReadAsync($ob,0,$ob.Length)}else{$e.Write($eb,0,$read);$et=$es.ReadAsync($eb,0,$eb.Length)}}
    }
   };Start-Sleep -Milliseconds 10
  }
  $exitCode=$p.ExitCode;Require ($exitCode -eq 0) ('OBSERVATION_COMMAND_EXIT_'+$exitCode)
  return [Text.UTF8Encoding]::new($false,$true).GetString($o.ToArray())
 }catch{$commandError=if($_.Exception.Message -cmatch '\A[A-Z0-9_]{1,128}\z'){$_.Exception.Message}else{'OBSERVATION_'+$_.Exception.GetType().Name};throw
 }finally{
  try{
   if($started -and -not $p.HasExited){try{$p.Kill();$null=$p.WaitForExit(2000)}catch{}}
   $terminated=(-not $started -or $p.HasExited);if($started -and $p.HasExited){$exitCode=$p.ExitCode}
   $record=New-ObservationCommandRecord $Arguments $o.ToArray() $e.ToArray() $exitCode $commandError $timer.ElapsedMilliseconds $terminated
   [IO.File]::WriteAllText((Join-Path $attempt ('command-{0:D3}.private.json' -f $script:ObservationSequence)),($record|ConvertTo-Json -Depth 4 -Compress),[Text.UTF8Encoding]::new($false))
  }finally{$p.Dispose();$o.Dispose();$e.Dispose()}
 }
}
try{
 foreach($path in @($root,(Join-Path $root 'worker_outputs'),$vbox)){$item=Get-Item -LiteralPath $path -Force;while($null -ne $item){Require (-not($item.Attributes -band [IO.FileAttributes]::ReparsePoint)) 'REPARSE_PATH_REFUSED';$item=if($item -is [IO.FileInfo]){$item.Directory}else{$item.Parent}}}
 $held=[IO.File]::Open($vbox,'Open','Read','Read')
 Require ([Convert]::ToHexString([Security.Cryptography.SHA256]::HashData($held)).ToLowerInvariant() -ceq $vboxHash) 'HYPERVISOR_CHANGED'
 $attempt=Join-Path $root ('worker_outputs\install-observation-'+[Guid]::NewGuid().ToString('N'));$null=[IO.Directory]::CreateDirectory($attempt)
 $beforeText=VBox-Observe @('showvminfo',$vm,'--machinereadable');$before=Parse-ObservedMachine $beforeText;Verify-ObservedMachine $before
 [IO.File]::WriteAllText((Join-Path $attempt 'before.txt'),$beforeText,[Text.UTF8Encoding]::new($false))
 $screen=$null;$digest=$null;$length=0
 if($before['VMState'] -ceq 'running'){
  $screen=Join-Path $attempt 'screen.png';$null=VBox-Observe @('controlvm',$vm,'screenshotpng',$screen,'0')
  $item=Get-Item -LiteralPath $screen -Force;Require ($item.Length -ge 24 -and $item.Length -le 2097152 -and -not($item.Attributes -band [IO.FileAttributes]::ReparsePoint)) 'SCREENSHOT_FILE_BOUND'
  $bytes=[IO.File]::ReadAllBytes($screen);Require ([Convert]::ToHexString($bytes,0,8) -ceq '89504E470D0A1A0A') 'SCREENSHOT_PNG_REQUIRED'
  $digest=[Convert]::ToHexString([Security.Cryptography.SHA256]::HashData($bytes)).ToLowerInvariant();$length=$bytes.Length
 }
 $afterText=VBox-Observe @('showvminfo',$vm,'--machinereadable');$after=Parse-ObservedMachine $afterText;Verify-ObservedMachine $after
 [IO.File]::WriteAllText((Join-Path $attempt 'after.txt'),$afterText,[Text.UTF8Encoding]::new($false))
 $report=[ordered]@{schema_version=1;classification='PRIVATE_INSTALLATION_OBSERVATION';vm_id=$vm;host_sid=$identity.User.Value;before_state=$before['VMState'];after_state=$after['VMState'];screen_path=$screen;screen_sha256=$digest;screen_bytes=$length;utc=[DateTime]::UtcNow.ToString('o');guest_input=$false;vm_start_stop=$false;integration_modified=$false;candidate_execution=$false}
 [IO.File]::WriteAllText((Join-Path $attempt 'observation.json'),($report|ConvertTo-Json -Compress),[Text.UTF8Encoding]::new($false));$report|ConvertTo-Json -Compress
}catch{
 if($attempt){$code=if($_.Exception.Message -cmatch '\A[A-Z0-9_]{1,128}\z'){$_.Exception.Message}else{'DETAILS_WITHHELD'};[IO.File]::WriteAllText((Join-Path $attempt 'failure.json'),([ordered]@{schema_version=1;vm_id=$vm;error_code=$code;error_type=$_.Exception.GetType().Name;utc=[DateTime]::UtcNow.ToString('o')}|ConvertTo-Json -Compress),[Text.UTF8Encoding]::new($false))};throw
}finally{if($held){$held.Dispose()}}
