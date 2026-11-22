# Fixed source-only installation entry. Run only via the protected standard-host launcher.
[CmdletBinding()]
param([switch]$Install)
Set-StrictMode -Version Latest
$ErrorActionPreference='Stop'
$root='C:\ProgramData\AI-BS-WorkerControl\disposable_probe_v1'
$vm='e5a2fe34-7b90-460c-83af-903d51b4bb16'
$isoHash='bc3f24086ebadc94489066b5ad78089e2cf5c3491e90e790bb81a2b199c10e38'
$additionsHash='fc41354d8b974051fa33ca5a4f9c999a58c6e0dfc595b02a924a544392234b3d'
$probeHash='82c6b2510807246aaa99668bb4416ec99c4ce3ecbc7d007cfe4165d14aaf1531'
$template='C:\Program Files\Oracle\VirtualBox\UnattendedTemplates\win_nt6_unattended.xml'
$templateHash='312555562d8b55e550ee22a71e33eb25133b3217e527a2df94a78a1702064970'
function Require([bool]$Condition,[string]$Code){if(-not $Condition){throw [InvalidOperationException]::new($Code)}}
function Hash([string]$Path){(Get-FileHash -LiteralPath $Path -Algorithm SHA256).Hash.ToLowerInvariant()}
if(-not $Install){[pscustomobject]@{state='DESCRIBE_ONLY';vm_id=$vm;operation='OFFLINE_NEW_WINDOWS_INSTALL_ONLY';network='none';txs=$false;candidate_execution=$false;integration_modified=$false}|ConvertTo-Json;return}
Require ($PSVersionTable.PSVersion.Major -ge 7) 'PROTECTED_POWERSHELL7_REQUIRED'
$plan=Get-Content -LiteralPath (Join-Path $root 'policy\provisioning.json') -Raw|ConvertFrom-Json
Require ($plan.schema_version -eq 1 -and $plan.vm_uuid -ceq $vm -and $plan.forbidden_vm_uuid -ceq '6c5a53da-ab80-4ecb-8be6-4059266f736e' -and $plan.root -ceq $root -and $plan.store -ceq 'E:\AI-BS-DisposableProbe-v1' -and $plan.vm_name -ceq 'AI-BS-DisposableProbe-20261026' -and $plan.guest_username -ceq 'aibs_vm_worker' -and $plan.network -ceq 'none' -and -not $plan.general_worker_admission -and -not $plan.apply_authorized) 'EXACT_NEW_VM_PLAN_REQUIRED'
$identity=[Security.Principal.WindowsIdentity]::GetCurrent();$principal=[Security.Principal.WindowsPrincipal]$identity
Require ($identity.User.Value -ceq $plan.dispatcher_sid -and $identity.User.Value -ceq 'S-1-5-21-2133766663-4066672948-2456486318-1006' -and -not $principal.IsInRole('Administrators')) 'EXACT_STANDARD_HOST_LAUNCHER_REQUIRED'
$env:VBOX_USER_HOME=$plan.vbox_user_home
Require ($env:VBOX_USER_HOME -ceq (Join-Path $root 'vbox_home')) 'ISOLATED_VBOX_REGISTRY_REQUIRED'
$held=[Collections.Generic.List[IDisposable]]::new()
function Hold-Pinned([string]$Path,[string]$Digest){
 Require ($Digest -cmatch '^[0-9a-f]{64}$') 'DIGEST_METADATA_REQUIRED'
 $item=Get-Item -LiteralPath $Path -Force;Require (-not($item.Attributes -band [IO.FileAttributes]::ReparsePoint)) 'REPARSE_FILE_REFUSED'
 $stream=[IO.File]::Open($Path,'Open','Read','Read');$held.Add($stream)
 Require ([Convert]::ToHexString([Security.Cryptography.SHA256]::HashData($stream)).ToLowerInvariant() -ceq $Digest) 'PINNED_FILE_CHANGED'
}
$log=Join-Path $root 'worker_outputs\installation.jsonl'
function Log($Object){[IO.File]::AppendAllText($log,(($Object|ConvertTo-Json -Depth 6 -Compress)+"`n"),[Text.UTF8Encoding]::new($false))}
function VBox([string[]]$Arguments,[int]$Seconds=120){
 Require ((Hash $plan.vbox_path) -ceq $plan.vbox_sha256) 'HYPERVISOR_CHANGED'
 $s=[Diagnostics.ProcessStartInfo]::new($plan.vbox_path);$s.UseShellExecute=$false;$s.CreateNoWindow=$true;$s.RedirectStandardOutput=$true;$s.RedirectStandardError=$true
 foreach($a in $Arguments){$s.ArgumentList.Add($a)}
 $p=[Diagnostics.Process]::new();$p.StartInfo=$s
 # Raw output can contain disposable credentials. Retain privately, never in the
 # public command log or ledger. This trusted installer helper is not the worker.
 try{
  Require ($p.Start()) 'VBOX_PROCESS_START_FAILED'
  $o=$p.StandardOutput.ReadToEndAsync();$e=$p.StandardError.ReadToEndAsync()
  $timedOut=-not $p.WaitForExit($Seconds*1000)
  if($timedOut){try{$p.Kill($true)}catch{};$null=$p.WaitForExit(2000)}
  $streamsComplete=$o.IsCompleted -and $e.IsCompleted
  if(-not $streamsComplete){$null=[Threading.Tasks.Task]::WaitAll([Threading.Tasks.Task[]]@($o,$e),2000);$streamsComplete=$o.IsCompleted -and $e.IsCompleted}
  $stdout=if($o.IsCompletedSuccessfully){$o.GetAwaiter().GetResult()}else{''}
  $stderr=if($e.IsCompletedSuccessfully){$e.GetAwaiter().GetResult()}else{''}
  $outBytes=[Text.Encoding]::UTF8.GetBytes($stdout);$errBytes=[Text.Encoding]::UTF8.GetBytes($stderr)
  $outCount=[Math]::Min($outBytes.Length,1048576);$errCount=[Math]::Min($errBytes.Length,1048576-$outCount)
  $outputTruncated=($outCount+$errCount -ne $outBytes.Length+$errBytes.Length)
  $exitCode=if($p.HasExited){$p.ExitCode}else{$null}
  $private=[ordered]@{schema_version=1;classification='PRIVATE_INSTALLATION_EVIDENCE_EXCLUDE_FROM_LEDGER';operation=$Arguments[0];vm_uuid=$vm;timed_out=$timedOut;exit_code=$exitCode;streams_complete=$streamsComplete;output_truncated=$outputTruncated;combined_retained_bytes=($outCount+$errCount);stdout_base64=[Convert]::ToBase64String($outBytes,0,$outCount);stderr_base64=[Convert]::ToBase64String($errBytes,0,$errCount);utc=[DateTime]::UtcNow.ToString('o')}
  $privatePath=Join-Path $root ('worker_state\installation-command-'+[Guid]::NewGuid().ToString('N')+'.private.json')
  [IO.File]::WriteAllText($privatePath,($private|ConvertTo-Json -Depth 3 -Compress),[Text.UTF8Encoding]::new($false))
  Log ([ordered]@{phase='command_result';operation=$Arguments[0];vm_uuid=$vm;exit_code=$exitCode;timed_out=$timedOut;private_output_retained=$true;utc=[DateTime]::UtcNow.ToString('o')})
  Require (-not $timedOut) 'OWNED_INSTALL_COMMAND_TIMEOUT_VM_STATE_REQUIRES_REVIEW'
  Require ($streamsComplete -and -not $outputTruncated) 'VBOX_OUTPUT_LIMIT'
  Require ($exitCode -eq 0) ('VBOX_FAILED_'+$exitCode)
  return $stdout
 }finally{$p.Dispose()}
}
function Machine-Map([string]$Text){
 $map=[Collections.Generic.Dictionary[string,string]]::new([StringComparer]::Ordinal)
 foreach($line in ($Text -split "`n")){if($line -match '^([^=]+)=(.*)$'){$key=$matches[1].Trim('"');Require (-not $map.ContainsKey($key)) 'DUPLICATE_MACHINE_PROPERTY';$map.Add($key,$matches[2].Trim().Trim('"'))}}
 return $map
}
function Verify-NewMachine($Map){
 foreach($pair in @(@('UUID',$vm),@('name','AI-BS-DisposableProbe-20261026'),@('VMState','poweroff'),@('memory','4096'),@('cpus','4'),@('firmware','EFI'),@('SecureBoot','on'),@('clipboard','disabled'),@('clipboard_file_transfers','off'),@('draganddrop','disabled'),@('vrde','off'),@('usb','off'),@('audio','none'),@('audio_in','off'),@('audio_out','off'))){Require ($Map.ContainsKey($pair[0]) -and $Map[$pair[0]] -ceq $pair[1]) ('VM_POLICY_'+$pair[0])}
 foreach($n in 1..8){Require ($Map.ContainsKey('nic'+$n) -and $Map['nic'+$n] -ceq 'none') 'NO_GUEST_NICS_REQUIRED'}
 foreach($n in 1..4){Require ($Map.ContainsKey('uart'+$n) -and $Map['uart'+$n] -ceq 'off') 'NO_GUEST_UART_REQUIRED'}
 foreach($key in $Map.Keys){Require ($key -notmatch '^SharedFolder(Name|Path|Writable)') 'SHARED_FOLDER_REFUSED'}
}
$lease=$null;$attemptMarker=$null
try{
 Require (Test-Path -LiteralPath (Join-Path $root 'worker_outputs\prepared_vm.txt') -PathType Leaf) 'PROVISIONING_CHECKPOINT_REQUIRED'
 $prepared=Machine-Map ([IO.File]::ReadAllText((Join-Path $root 'worker_outputs\prepared_vm.txt')))
 Require ($prepared.ContainsKey('UUID') -and $prepared['UUID'] -ceq $vm -and $prepared.ContainsKey('VMState') -and $prepared['VMState'] -ceq 'poweroff') 'PREPARED_NEW_VM_CHECKPOINT_REQUIRED'
 Hold-Pinned $plan.iso_path $isoHash
 Hold-Pinned $template $templateHash
 $manifest=Get-Content -LiteralPath (Join-Path $root 'identity\install_manifest.json') -Raw|ConvertFrom-Json
 Require ($manifest.schema_version -eq 1 -and $manifest.vm_uuid -ceq $vm -and $manifest.files -is [array] -and $manifest.files.Count -eq 3) 'INSTALL_MANIFEST_SCHEMA'
 $expected=[ordered]@{'deployment\Bootstrap-GuestProbe.ps1'=$null;'deployment\DiagnosticProbe.exe'=$probeHash;'identity\VBoxGuestAdditions.iso'=$additionsHash}
 foreach($relative in $expected.Keys){
  $entries=@($manifest.files|Where-Object{$_.relative_path -ceq $relative});Require ($entries.Count -eq 1) 'ONE_EXACT_INSTALL_MANIFEST_ENTRY_REQUIRED'
  $digest=$entries[0].sha256;Require ($digest -is [string] -and $digest -cmatch '^[0-9a-f]{64}$') 'INSTALL_METADATA_MALFORMED'
  if($expected[$relative]){Require ($digest -ceq $expected[$relative]) 'FIXED_INSTALL_IDENTITY_CHANGED'}
  Hold-Pinned (Join-Path $root $relative) $digest
 }
 $lease=[IO.File]::Open((Join-Path $root 'worker_state\provision.lease'),'Open','ReadWrite','None')
 Verify-NewMachine (Machine-Map (VBox @('showvminfo',$vm,'--machinereadable')))
 Require ((Get-PSDrive E).Free -ge 40GB) 'STORAGE_RESERVE_CHANGED'
 # Fixed diagnostic profile: 4 GiB guest plus 2 GiB currently free host reserve.
 Require ((Get-CimInstance Win32_OperatingSystem).FreePhysicalMemory*1KB -ge 6GB) 'CURRENT_RAM_UNAVAILABLE'
 $attemptMarker=[IO.File]::Open((Join-Path $root 'worker_state\installation.started'),'CreateNew','Write','None')
 $start=[Text.Encoding]::UTF8.GetBytes(([ordered]@{vm_uuid=$vm;utc=[DateTime]::UtcNow.ToString('o');state='INSTALL_INTENT_RETAINED'}|ConvertTo-Json -Compress));$attemptMarker.Write($start,0,$start.Length);$attemptMarker.Flush($true)
 $work=Join-Path $root ('worker_state\install-'+[Guid]::NewGuid().ToString('N'));[IO.Directory]::CreateDirectory($work)|Out-Null
 [xml]$xml=[IO.File]::ReadAllText($template)
 $ns=[Xml.XmlNamespaceManager]::new($xml.NameTable);$ns.AddNamespace('u','urn:schemas-microsoft-com:unattend')
 $bypass=@($xml.SelectNodes('//u:RunAsynchronous[u:RunAsynchronousCommand/u:Path[contains(text(),"LabConfig")]]',$ns))
 Require ($bypass.Count -eq 2) 'EXACT_DEFAULT_BYPASS_BLOCKS_REQUIRED'
 foreach($node in $bypass){$null=$node.ParentNode.RemoveChild($node)}
 $auto=$xml.SelectSingleNode('//u:AutoLogon',$ns);Require ($null -ne $auto) 'DEFAULT_AUTOLOGON_SCHEMA'
 Require (@($auto.SelectNodes('u:LogonCount',$ns)).Count -eq 0) 'DUPLICATE_AUTOLOGON_COUNT_REFUSED'
 $count=$xml.CreateElement('LogonCount','urn:schemas-microsoft-com:unattend');$count.InnerText='1';$null=$auto.AppendChild($count)
 $answer=Join-Path $work 'unattended-template.xml';$xml.Save($answer)
 Require ([IO.File]::ReadAllText($answer) -notmatch 'Bypass(CPU|RAM|SecureBoot|Storage|TPM)Check|LabConfig') 'HARDWARE_BYPASS_REFUSED'
 $bootstrap=[IO.File]::ReadAllBytes((Join-Path $root 'deployment\Bootstrap-GuestProbe.ps1'))
 $binary=[IO.File]::ReadAllBytes((Join-Path $root 'deployment\DiagnosticProbe.exe'))
 $password=[IO.File]::ReadAllText((Join-Path $root 'credentials\guest.txt'))
 Require ($password.Length -ge 32 -and $password.Length -le 128 -and $password -notmatch '[\r\n\x00]') 'GUEST_CREDENTIAL_PROFILE'
 $lines=[Collections.Generic.List[string]]::new();$lines.Add('@echo off');$lines.Add('setlocal')
 $lines.Add('powershell.exe -NoProfile -NonInteractive -Command "$ErrorActionPreference=''Stop''; if(Test-Path -LiteralPath ''C:\AIBSBootstrap''){exit 11}; $a=[Security.AccessControl.DirectorySecurity]::new(); $a.SetOwner([Security.Principal.SecurityIdentifier]::new(''S-1-5-32-544'')); $a.SetAccessRuleProtection($true,$false); foreach($s in @(''S-1-5-18'',''S-1-5-32-544'')){$a.AddAccessRule([Security.AccessControl.FileSystemAccessRule]::new([Security.Principal.SecurityIdentifier]::new($s),''FullControl'',''ContainerInherit,ObjectInherit'',''None'',''Allow''))}; [IO.Directory]::CreateDirectory(''C:\AIBSBootstrap'',$a)|Out-Null"')
 $lines.Add('if errorlevel 1 exit /b 11')
 foreach($entry in @(@('bootstrap.ps1.b64',[Convert]::ToBase64String($bootstrap)),@('probe.exe.b64',[Convert]::ToBase64String($binary)),@('worker.b64',[Convert]::ToBase64String([Text.Encoding]::UTF8.GetBytes($password))))){
  $text=$entry[1];for($i=0;$i -lt $text.Length;$i+=120){$redirect=if($i -eq 0){'>'}else{'>>'};$lines.Add(($redirect+'"C:\AIBSBootstrap\'+$entry[0]+'" echo '+$text.Substring($i,[Math]::Min(120,$text.Length-$i))))}
 }
 $lines.Add('powershell.exe -NoProfile -NonInteractive -Command "$ErrorActionPreference=''Stop''; [IO.File]::WriteAllBytes(''C:\AIBSBootstrap\bootstrap.ps1'',[Convert]::FromBase64String([IO.File]::ReadAllText(''C:\AIBSBootstrap\bootstrap.ps1.b64''))); [IO.File]::WriteAllBytes(''C:\AIBSBootstrap\DiagnosticProbe.exe'',[Convert]::FromBase64String([IO.File]::ReadAllText(''C:\AIBSBootstrap\probe.exe.b64'')))"')
 $lines.Add('if errorlevel 1 exit /b 12')
 $lines.Add('powershell.exe -NoProfile -NonInteractive -ExecutionPolicy Bypass -File "C:\AIBSBootstrap\bootstrap.ps1"')
 $lines.Add('exit /b %ERRORLEVEL%')
 $post=Join-Path $work 'postinstall-template.cmd';[IO.File]::WriteAllLines($post,$lines,[Text.ASCIIEncoding]::new())
 $password=$null
 $commandArguments=@('unattended','install',$vm,('--iso='+$plan.iso_path),'--user=aibs_bootstrap',('--user-password-file='+(Join-Path $root 'credentials\bootstrap.txt')),('--admin-password-file='+(Join-Path $root 'credentials\bootstrap.txt')),'--full-user-name=AI-BS Bootstrap','--hostname=AIBSPROBE01.local','--locale=en_US','--country=US','--language=en-US','--time-zone=UTC','--image-index=1','--install-additions',('--additions-iso='+(Join-Path $root 'identity\VBoxGuestAdditions.iso')),'--no-install-txs',('--script-template='+$answer),('--post-install-template='+$post),('--auxiliary-base-path='+(Join-Path $work 'media-')),'--start-vm=none')
 $null=VBox $commandArguments 180
 Verify-NewMachine (Machine-Map (VBox @('showvminfo',$vm,'--machinereadable')))
 $null=VBox @('startvm',$vm,'--type=headless') 90
 Log ([ordered]@{state='NEW_OFFLINE_WINDOWS_INSTALL_STARTED';vm_uuid=$vm;dispatcher_sid=$identity.User.Value;install_media_sha256=$isoHash;additions_media_sha256=$additionsHash;hardware_bypass=$false;network='none';txs=$false;expected_completion='POWERED_OFF_WITH_BOOTSTRAP_REPORT';guest_report_authenticated=$false;candidate_execution=$false;integration_modified=$false;utc=[DateTime]::UtcNow.ToString('o')})
 Write-Output 'NEW_OFFLINE_WINDOWS_INSTALL_STARTED'
}catch{Log ([ordered]@{state='INSTALL_FAILED_RETAINED';error_type=$_.Exception.GetType().Name;error_code=if($_.Exception.Message -cmatch '^[A-Z0-9_]+$'){$_.Exception.Message}else{'DETAILS_WITHHELD'};vm_uuid=$vm;utc=[DateTime]::UtcNow.ToString('o')});throw [InvalidOperationException]::new('INSTALL_FAILED_RETAINED_REVIEW_PROTECTED_LOG')}
finally{if($attemptMarker){$attemptMarker.Dispose()};if($lease){$lease.Dispose()};foreach($stream in $held){$stream.Dispose()}}
