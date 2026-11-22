# Trusted controller infrastructure only. Never invokes VBoxManage or guest code.
[CmdletBinding()]param([string]$EvidenceDirectory)
Set-StrictMode -Version Latest
$ErrorActionPreference='Stop'
if(-not $EvidenceDirectory){$EvidenceDirectory=Join-Path $PSScriptRoot ('evidence\infra-'+[DateTime]::UtcNow.ToString('yyyyMMddTHHmmssZ')+'-'+[Guid]::NewGuid().ToString('N'))}
$null=[IO.Directory]::CreateDirectory($EvidenceDirectory)
Import-Module (Join-Path $PSScriptRoot 'DisposableProbe.psm1') -Force
$module=Get-Module DisposableProbe
$report=& $module {
 param($EvidenceDirectory,$SourceRoot)
 $checks=[Collections.Generic.List[object]]::new()
 function Check([string]$Name,[scriptblock]$Body){
   try{$null=& $Body;$checks.Add([ordered]@{name=$Name;passed=$true})}
   catch{$checks.Add([ordered]@{name=$Name;passed=$false;error=$_.Exception.Message})}
 }
 function Expect-Failure([scriptblock]$Body,[string]$Code){$caught=$false;try{&$Body}catch{$caught=$true;Require ($_.Exception.Message.Contains($Code,[StringComparison]::Ordinal)) ('WRONG_FAILURE '+$_.Exception.Message)};Require $caught ('EXPECTED_FAILURE '+$Code)}
 function Parsed($Value){Read-StrictJSON ([Text.Encoding]::UTF8.GetBytes((ConvertTo-Json -InputObject $Value -Depth 12 -Compress)))}
 Check 'bootstrap host entry describes only without execution switch' {
   $description=& (Join-Path $sourceRoot 'Readback-And-SnapshotWorker.ps1') | ConvertFrom-Json -AsHashtable
   Require ($description.state -ceq 'DESCRIBE_ONLY' -and $description.vm_uuid -ceq $script:WorkerUUID -and -not $description.candidate_execution -and -not $description.general_admission -and -not $description.profile_published) 'BOOTSTRAP_DESCRIBE_GATE_FAILED'
 }
 Check 'bootstrap source execution refused before import outside protected deployment' {
   Expect-Failure {& (Join-Path $sourceRoot 'Readback-And-SnapshotWorker.ps1') -Execute -ExpectedModuleSHA256 ('a'*64) -ExpectedGrantSHA256 ('b'*64)} 'PROTECTED_POWERSHELL7_DEPLOYMENT_REQUIRED'
 }
 Check 'bootstrap controller launcher describes only without execution switch' {
   $description=& (Join-Path $sourceRoot 'Start-BootstrapPreparation.ps1') | ConvertFrom-Json -AsHashtable
   Require ($description.state -ceq 'DESCRIBE_ONLY' -and $description.vm_uuid -ceq $script:WorkerUUID -and $description.creates_one_use_grant -and $description.launches_only_standard_dispatcher -and -not $description.profile_published) 'BOOTSTRAP_LAUNCHER_DESCRIBE_GATE_FAILED'
 }
 Check 'bootstrap controller launcher rejects source execution before mutation' {
   Expect-Failure {& (Join-Path $sourceRoot 'Start-BootstrapPreparation.ps1') -Execute} 'PROTECTED_POWERSHELL7_DEPLOYMENT_REQUIRED'
 }
 Check 'guest bootstrap readback remains a bounded source artifact without host execution' {
   $path=Join-Path $sourceRoot 'Guest-BootstrapReadback.ps1'
   $tokens=$null;$errors=$null;$ast=[Management.Automation.Language.Parser]::ParseFile($path,[ref]$tokens,[ref]$errors)
   Require (@($errors).Count -eq 0 -and (Get-Item -LiteralPath $path).Length -le 10240) 'GUEST_READBACK_SOURCE_BOUND_OR_SYNTAX'
   Require ($ast.ParamBlock.Parameters.Count -eq 1 -and $ast.ParamBlock.Parameters[0].Name.VariablePath.UserPath -ceq 'Challenge') 'GUEST_READBACK_PUBLIC_ARGUMENTS_CHANGED'
 }
 Check 'all fixed host sources parse before protected publication' {
   foreach($name in @('DisposableProbe.psm1','Invoke-WorkerTransport.ps1','Readback-And-SnapshotWorker.ps1','Start-BootstrapPreparation.ps1')){
     $tokens=$null;$errors=$null;$null=[Management.Automation.Language.Parser]::ParseFile((Join-Path $sourceRoot $name),[ref]$tokens,[ref]$errors)
     Require (@($errors).Count -eq 0) ('HOST_SOURCE_SYNTAX_'+$name)
   }
 }
 $profile=Parsed ([ordered]@{schema_version=1;state='PROVISIONED';vm_uuid=$script:WorkerUUID;image_id=('aibs-fixed-probe-win11-eval-'+$script:WorkerUUID);image_base_path='E:\AI-BS-DisposableProbe-v1\sealed\system.vdi';image_base_sha256=('a'*64);system_disk_uuid='5b4f5331-0da2-491d-a257-6b4ecf435a5a';accepted_snapshot_uuid='22222222-2222-4222-8222-222222222222';vbox_path='C:\Program Files\Oracle\VirtualBox\VBoxManage.exe';vbox_sha256=('b'*64);vbox_user_home=(Fixed-Path 'vbox_home');guest_executable='C:\AIBSProbe\DiagnosticProbe.exe';guest_executable_sha256=('c'*64);guest_username='aibs_vm_worker';guest_sid='S-1-5-21-111-222-333-1001';dispatcher_sid=$script:DispatcherSID;controller_sid=$script:ControllerSID;vm_memory_mib=4096;vm_cpus=4})
 $now=[DateTime]::new(2026,10,26,18,0,0,[DateTimeKind]::Utc)
 $id='33333333-3333-4333-8333-333333333333';$pin='d'*64
 $request=Parsed ([ordered]@{schema_version=1;purpose='fixed_disposable_diagnostic_v1';task_id='first-disposable-diagnostic-v1';attempt_id=$id;challenge=('e'*64);mode='success';profile_sha256=$pin;issued_at=$now.ToString('o');expires_at=$now.AddMinutes(10).ToString('o');guest_timeout_ms=2000;output_bytes=4096;transport_seconds=30;cancel_after_ms=0})
 Check 'exact fixed profile accepted' {Assert-ProfileData $profile}
 Check 'native integrity read uses TokenIntegrityLevel rather than membership groups' {Require ([AIBSProbeHost.Native]::IntegritySID() -cmatch '\AS-1-16-(4096|8192|8448|12288|16384)\z') 'TOKEN_INTEGRITY_QUERY_FAILED'}
 foreach($change in @(@('state','PREPARED','ISOLATION_UNAVAILABLE'),@('vm_uuid',$script:IntegrationUUID,'INTEGRATION_VM_REFUSED'),@('vm_uuid','44444444-4444-4444-8444-444444444444','EXACT_NEW_VM_REQUIRED'),@('dispatcher_sid',($script:HostSIDPrefix+'1005'),'SEPARATE_DISPATCHER_REQUIRED'),@('guest_sid',($script:HostSIDPrefix+'1006'),'SEPARATE_GUEST_ACCOUNT_REQUIRED'),@('guest_username','Administrator','SEPARATE_GUEST_ACCOUNT_REQUIRED'),@('guest_executable','C:\Windows\System32\cmd.exe','FIXED_GUEST_EXECUTABLE_REQUIRED'),@('vbox_sha256',('F'*64),'PROFILE_DIGEST_REQUIRED'),@('vbox_user_home','C:\Users\aibs_probe_host\.VirtualBox','FIXED_VBOX_HOME_REQUIRED'),@('vm_cpus',8,'REVIEWED_VM_PROFILE_REQUIRED'))){
   $field=$change[0];$value=$change[1];$code=$change[2];Check ('profile rejects '+$field+' '+$value) {$copy=Parsed $profile;$copy[$field]=$value;Expect-Failure {Assert-ProfileData $copy} $code}
 }
 Check 'duplicate exact JSON keys rejected' {Expect-Failure {Read-StrictJSON ([Text.Encoding]::UTF8.GetBytes('{"x":1,"x":2}'))} 'DUPLICATE_JSON_KEY'}
 Check 'noninteger JSON rejected' {Expect-Failure {Read-StrictJSON ([Text.Encoding]::UTF8.GetBytes('{"x":1.5}'))} 'INTEGER_JSON_REQUIRED'}
 Check 'root JSON array rejected' {Expect-Failure {Read-StrictJSON ([Text.Encoding]::UTF8.GetBytes('[1]'))} 'JSON_OBJECT_REQUIRED'}
 Check 'invalid UTF8 rejected' {$threw=$false;try{Read-StrictJSON ([byte[]]@(0xff,0xfe))}catch{$threw=$true};Require $threw 'INVALID_UTF8_ACCEPTED'}
 Check 'valid grant accepted at issue instant' {Assert-Request $request $profile $pin $id $now}
 Check 'valid grant accepted one tick before expiry' {Assert-Request $request $profile $pin $id ($now.AddMinutes(10).AddTicks(-1))}
 Check 'grant expires at exact boundary' {Expect-Failure {Assert-Request $request $profile $pin $id $now.AddMinutes(10)} 'EXPIRED_OR_FUTURE_REQUEST'}
 Check 'grant rejected one microsecond after expiry' {Expect-Failure {Assert-Request $request $profile $pin $id $now.AddMinutes(10).AddTicks(10)} 'EXPIRED_OR_FUTURE_REQUEST'}
 Check 'future grant rejected' {Expect-Failure {Assert-Request $request $profile $pin $id $now.AddTicks(-1)} 'EXPIRED_OR_FUTURE_REQUEST'}
 foreach($change in @(@('attempt_id','44444444-4444-4444-8444-444444444444','REQUEST_SCOPE_MISMATCH'),@('challenge','bad','REQUEST_SCOPE_MISMATCH'),@('mode','cmd','FIXED_MODE_REQUIRED'),@('profile_sha256',('1'*64),'REQUEST_SCOPE_MISMATCH'),@('guest_timeout_ms',3000,'FIXED_DIAGNOSTIC_LIMITS_REQUIRED'),@('output_bytes',1048577,'FIXED_DIAGNOSTIC_LIMITS_REQUIRED'),@('cancel_after_ms',500,'FIXED_CANCELLATION_REQUIRED'))){
   $field=$change[0];$value=$change[1];$code=$change[2];Check ('request rejects '+$field) {$copy=Parsed $request;$copy[$field]=$value;Expect-Failure {Assert-Request $copy $profile $pin $id $now} $code}
 }
 $vmText=@("UUID=`"$($profile.vm_uuid)`"",'VMState="poweroff"','memory=4096','cpus=4','clipboard="disabled"','draganddrop="disabled"',"CurrentSnapshotUUID=`"$($profile.accepted_snapshot_uuid)`"",'"SATA-ImageUUID-0-0"="44444444-4444-4444-8444-444444444444"')+@(1..8|ForEach-Object{'nic'+$_+'="none"'})+@(' rec_screen0','rec_screen_enabled="on"')
 $vm=Parse-VMInfo ($vmText -join "`n")
 foreach($key in @('clipboard_file_transfers','vrde','usb','ehci','xhci','teleporterenabled')){$vm.Add($key,'off')}
 $vm.Add('storagecontrollername0','SATA')
 foreach($pair in @(@('firmware','EFI'),@('SecureBoot','on'),@('audio','none'),@('audio_in','off'),@('audio_out','off'))){$vm.Add($pair[0],$pair[1])}
 foreach($index in 1..4){$vm.Add('uart'+$index,'off')}
 $vmText=@($vm.GetEnumerator()|ForEach-Object {'"'+$_.Key+'"="'+$_.Value+'"'})+@(' rec_screen0')
 Check 'actual quoted storage key and recording marker syntax accepted' {Assert-VMInfo $vm $profile 'poweroff'}
 Check 'duplicate quoted/unquoted key refused' {Expect-Failure {Parse-VMInfo 'UUID="x"`n"UUID"="y"'.Replace('`n',"`n")} 'DUPLICATE_VM_INFO'}
 Check 'unknown bare line refused' {Expect-Failure {Parse-VMInfo 'unknown marker'} 'VM_INFO_MALFORMED'}
 Check 'integration identity refused before control operations' {$copy=Parse-VMInfo ($vmText -join "`n");$copy.UUID=$script:IntegrationUUID;Expect-Failure {Assert-VMInfo $copy $profile 'poweroff'} 'VM_IDENTITY_OR_STATE_MISMATCH'}
 Check 'running VM is never taken over' {Expect-Failure {Assert-VMInfo $vm $profile 'running'} 'VM_IDENTITY_OR_STATE_MISMATCH'}
 Check 'network enabled refused' {$copy=Parse-VMInfo ($vmText -join "`n");$copy.nic3='nat';Expect-Failure {Assert-VMInfo $copy $profile 'poweroff'} 'VM_NETWORK_NOT_DISABLED'}
 Check 'shared folder refused' {$copy=Parse-VMInfo ($vmText -join "`n");$copy.Add('SharedFolderNameMachineMapping1','host');Expect-Failure {Assert-VMInfo $copy $profile 'poweroff'} 'VM_SHARED_FOLDER_REFUSED'}
 Check 'snapshot drift refused' {$copy=Parse-VMInfo ($vmText -join "`n");$copy.CurrentSnapshotUUID='55555555-5555-4555-8555-555555555555';Expect-Failure {Assert-VMInfo $copy $profile 'poweroff'} 'VM_IMAGE_IDENTITY_CHANGED'}
 Check 'attached installation media refused' {$copy=Parse-VMInfo ($vmText -join "`n");$copy.Add('SATA-1-0','C:\private.iso');Expect-Failure {Assert-VMInfo $copy $profile 'poweroff'} 'VM_EXTRA_MEDIA_ATTACHED'}
 Check 'USB channel enabled refused' {$copy=Parse-VMInfo ($vmText -join "`n");$copy.usb='on';Expect-Failure {Assert-VMInfo $copy $profile 'poweroff'} 'VM_EXTRA_CHANNEL_ENABLED'}
 Check 'UART enabled refused' {$copy=Parse-VMInfo ($vmText -join "`n");$copy.uart3='server';Expect-Failure {Assert-VMInfo $copy $profile 'poweroff'} 'VM_UART_NOT_DISABLED'}
 Check 'SecureBoot disabled refused' {$copy=Parse-VMInfo ($vmText -join "`n");$copy.SecureBoot='off';Expect-Failure {Assert-VMInfo $copy $profile 'poweroff'} 'VM_BOOT_OR_AUDIO_PROFILE_CHANGED'}
 Check 'arbitrary VBox operation refused' {Expect-Failure {VBox-Arguments Arbitrary $profile $request} 'FIXED_OPERATION_REQUIRED'}
 Check 'run uses password-file and exact16 guest arguments' {$args=VBox-Arguments Run $profile $request;Require ($args -ccontains (Fixed-Path 'credentials\guest.txt')) 'PASSWORD_FILE_ABSENT';Require ((Guest-Arguments $profile $request).Count -eq 16) 'GUEST_ARGUMENT_COUNT';Require ($args -cnotcontains 'cmd.exe') 'UNAPPROVED_EXECUTABLE'}
 Check 'GuestControl delimiter forwards sixteen arguments without duplicate argv0' {$args=VBox-Arguments Run $profile $request;$delimiter=[Array]::IndexOf($args,'--');Require ($delimiter -gt 0 -and $args.Count-$delimiter-1 -eq 16 -and $args[$delimiter+1] -ceq '--mode' -and ($args[($delimiter+1)..($args.Count-1)] -join "`n") -ceq ((Guest-Arguments $profile $request)-join "`n")) 'GUESTCONTROL_ARGV_DRIFT'}
 $guest=Parsed ([ordered]@{schema_version=1;attempt_id=$id;challenge=$request.challenge;mode='emit';guest_sid=$profile.guest_sid;guest_username='aibs_vm_worker';standard_account=$true;administrator_group_present=$false;medium_integrity=$true;executable_sha256=$profile.guest_executable_sha256;image_sha256=$profile.image_base_sha256;vm_id=$profile.vm_uuid;state='COMPLETED';child_exit_code=7;stdout_base64=[Convert]::ToBase64String([Text.Encoding]::UTF8.GetBytes("probe`n"));stderr_base64=[Convert]::ToBase64String([Text.Encoding]::UTF8.GetBytes("diagnostic`n"));combined_output_bytes=17;output_limit_bytes=4096;termination_confirmed=$true;self_hash_revalidated=$true;resource_profile=@{process_limit=1;job_memory_bytes=268435456;cpu_rate_percent=25;elapsed_limit_ms=2000};input_sha256=(Hash-Text ((Guest-Arguments $profile $request)-join "`n"))})
 Check 'fixed guest emit report accepted' {Assert-GuestReport $guest $profile $request}
 foreach($change in @(@('challenge',('0'*64),'GUEST_REPORT_BINDING_FAILED'),@('guest_sid',($script:HostSIDPrefix+'1005'),'GUEST_STANDARD_IDENTITY_OR_TERMINATION_FAILED'),@('self_hash_revalidated',$false,'GUEST_STANDARD_IDENTITY_OR_TERMINATION_FAILED'),@('termination_confirmed',$false,'GUEST_STANDARD_IDENTITY_OR_TERMINATION_FAILED'),@('standard_account','true','GUEST_BOOLEAN_TYPE_REQUIRED'),@('input_sha256',('0'*64),'GUEST_INPUT_DIGEST_MISMATCH'),@('combined_output_bytes',18,'GUEST_OUTPUT_BOUND_FAILED'),@('child_exit_code',0,'FIXED_PROBE_RESULT_MISMATCH'))){
   $field=$change[0];$value=$change[1];$code=$change[2];Check ('guest report rejects '+$field) {$copy=Parsed $guest;$copy[$field]=$value;Expect-Failure {Assert-GuestReport $copy $profile $request} $code}
 }
 Check 'canonical serialization independent of property order' {Require ((JSON ([ordered]@{b=2;a=1})) -ceq (JSON ([ordered]@{a=1;b=2}))) 'CANONICAL_ORDER_FAILED'}
 Check 'raw VBox disk metadata adapter validates capacity units' {$m=Parse-MediumInfo "UUID: 5b4f5331-0da2-491d-a257-6b4ecf435a5a`nParent UUID: base`nLocation: E:\AI-BS-DisposableProbe-v1\sealed\system.vdi`nStorage format: VDI`nCapacity: 65536 MBytes`n";Require ($m.UUID -ceq $profile.system_disk_uuid -and $m.ParentUUID -ceq 'base' -and $m.Capacity -ceq '65536') 'DISK_ADAPTER_FAILED'}
 Check 'duplicate disk identity refused' {Expect-Failure {Parse-MediumInfo "UUID: x`nUUID: y"} 'DUPLICATE_MEDIUM_INFO'}
 Check 'authenticated receipt binds exact attempt and payload' {$body=Parsed @{domain='AI-BS/host-fixed-probe-receipt/v1';attempt_id=$id;profile_sha256=$pin;state='PASSED';output_sha256=('a'*64)};$key=[byte[]](0..31);$receipt=Parsed @{body=$body;hmac_sha256=(Receipt-Tag $body $key)};Assert-ReceiptAuthentication $receipt $key $id $pin}
 Check 'altered receipt output rejected' {$body=Parsed @{domain='AI-BS/host-fixed-probe-receipt/v1';attempt_id=$id;profile_sha256=$pin;output_sha256=('a'*64)};$key=[byte[]](0..31);$receipt=Parsed @{body=$body;hmac_sha256=(Receipt-Tag $body $key)};$receipt.body.output_sha256='b'*64;Expect-Failure {Assert-ReceiptAuthentication $receipt $key $id $pin} 'RECEIPT_AUTHENTICATION_FAILED'}
 Check 'receipt wrong attempt rejected' {$body=Parsed @{domain='AI-BS/host-fixed-probe-receipt/v1';attempt_id=$id;profile_sha256=$pin};$key=[byte[]](0..31);$receipt=Parsed @{body=$body;hmac_sha256=(Receipt-Tag $body $key)};Expect-Failure {Assert-ReceiptAuthentication $receipt $key '44444444-4444-4444-8444-444444444444' $pin} 'RECEIPT_SCOPE_FAILED'}
 Check 'permanent attempt CreateNew rejects replay without overwriting' {$path=Join-Path $EvidenceDirectory 'attempt.claim';New-File $path ([byte[]]@(1));$threw=$false;try{New-File $path ([byte[]]@(2))}catch{$threw=$true};Require ($threw -and [IO.File]::ReadAllBytes($path)[0] -eq 1) 'REPLAY_CLAIM_CHANGED'}
 Check 'exclusive lease excludes simultaneous controller' {$path=Join-Path $EvidenceDirectory 'vm.lease';$lease=[IO.File]::Open($path,[IO.FileMode]::OpenOrCreate,[IO.FileAccess]::ReadWrite,[IO.FileShare]::None);try{$threw=$false;try{$other=[IO.File]::Open($path,[IO.FileMode]::OpenOrCreate,[IO.FileAccess]::ReadWrite,[IO.FileShare]::None);$other.Dispose()}catch{$threw=$true};Require $threw 'LEASE_EXCLUSION_FAILED'}finally{$lease.Dispose()}}
 Check 'held admitted file resists concurrent write and replacement' {$path=Join-Path $EvidenceDirectory 'held.bin';New-File $path ([byte[]]@(1,2,3));try{$null=Read-Bytes $path 3 (Hash-Bytes ([byte[]]@(1,2,3)));$threw=$false;try{[IO.File]::WriteAllBytes($path,[byte[]]@(4))}catch{$threw=$true};Require $threw 'ADMITTED_FILE_WRITABLE'}finally{Close-Held}}
 Check 'changed admitted bytes rejected' {$path=Join-Path $EvidenceDirectory 'changed.bin';New-File $path ([byte[]]@(3));Expect-Failure {Read-Bytes $path 1 ('0'*64)} 'PINNED_BYTES_CHANGED'}
 Check 'hardlinked admitted input rejected' {$path=Join-Path $EvidenceDirectory 'link-target.bin';$link=Join-Path $EvidenceDirectory 'linked.bin';New-File $path ([byte[]]@(1));$null=New-Item -ItemType HardLink -Path $link -Target $path;Expect-Failure {Read-Bytes $link 1} 'HARDLINK_REFUSED'}
 Check 'infrastructure process exact exit and bounded stdout collected' {$r=Invoke-BoundedProcess (Join-Path $PSHOME 'pwsh.exe') @('-NoLogo','-NoProfile','-NonInteractive','-Command','[Console]::Out.Write("infra");exit 7') (Fixed-Path 'vbox_home') $EvidenceDirectory 10 4096;Require ($r.state -ceq 'EXITED' -and $r.exit_code -eq 7 -and $r.stdout -ceq 'infra' -and $r.owned_process_termination_confirmed) 'PROCESS_EXIT_COLLECTION_FAILED'}
 Check 'infrastructure process timeout terminates owned process' {$r=Invoke-BoundedProcess (Join-Path $PSHOME 'pwsh.exe') @('-NoLogo','-NoProfile','-NonInteractive','-Command','Start-Sleep -Seconds 10') (Fixed-Path 'vbox_home') $EvidenceDirectory 1 4096;Require ($r.state -ceq 'TIMED_OUT' -and $r.owned_process_termination_confirmed) 'TIMEOUT_FAILED'}
 Check 'infrastructure process cancellation terminates owned process' {$r=Invoke-BoundedProcess (Join-Path $PSHOME 'pwsh.exe') @('-NoLogo','-NoProfile','-NonInteractive','-Command','Start-Sleep -Seconds 10') (Fixed-Path 'vbox_home') $EvidenceDirectory 10 4096 250;Require ($r.state -ceq 'CANCELLED' -and $r.owned_process_termination_confirmed) 'CANCEL_FAILED'}
 Check 'infrastructure stdout plus stderr ceiling enforced' {$r=Invoke-BoundedProcess (Join-Path $PSHOME 'pwsh.exe') @('-NoLogo','-NoProfile','-NonInteractive','-Command','[Console]::Out.Write(("a"*8192));[Console]::Error.Write(("b"*8192))') (Fixed-Path 'vbox_home') $EvidenceDirectory 10 4096;Require ($r.state -ceq 'OUTPUT_LIMIT' -and $r.combined_output_bytes -le 4096 -and $r.owned_process_termination_confirmed) 'OUTPUT_LIMIT_FAILED'}
 Check 'retained real VBox disk fixture parses without unsupported flags' {$path='C:\ProgramData\AI-BS-WorkerControl\disposable_probe_v1\worker_outputs\current_medium.txt';if([IO.File]::Exists($path)){$m=Parse-MediumInfo ([IO.File]::ReadAllText($path));Require ($m.UUID -ceq $profile.system_disk_uuid -and $m.Capacity -ceq '65536' -and $m.ParentUUID -ceq 'base') 'MEASURED_MEDIUM_ADAPTER_FAILED'}else{Fail 'RETAINED_MEDIUM_FIXTURE_UNAVAILABLE'}}
 foreach($scenario in @('passed','start_uncertain','cleanup_uncertain','replayed')){
  Check ('mocked lifecycle '+$scenario) {
   $names=@('Read-Profile','Assert-Principal','Read-Request','Assert-Path','Assert-ClaimPolicy','Read-Bytes','Assert-StorageReserve','Assert-HostMemoryReserve','Assert-ImageChain','Now-UTC','Invoke-Operation')
   $originals=@{};foreach($name in $names){$originals[$name]=(Get-Item ('Function:'+ $name)).ScriptBlock}
   $originalRoot=$script:Root
   try{
    $script:Root=Join-Path $EvidenceDirectory ('lifecycle-'+$scenario)
    foreach($dir in @('worker_state','worker_claims','worker_outputs','vbox_home','credentials')){$null=[IO.Directory]::CreateDirectory((Fixed-Path $dir))}
    $base=Fixed-Path 'base.bin';New-File $base ([byte[]]@(1,2,3));$script:TestProfile=Parsed $profile;$script:TestProfile.image_base_path=$base;$script:TestProfile.image_base_sha256=Hash-Bytes ([byte[]]@(1,2,3))
    $script:TestRequest=Parsed $request;$script:TestGuest=Parsed $guest;$script:TestGuest.image_sha256=$script:TestProfile.image_base_sha256;$script:TestGuest.input_sha256=Hash-Text ((Guest-Arguments $script:TestProfile $script:TestRequest)-join "`n")
    $script:TestNow=$now;$script:TestScenario=$scenario;$script:TestVMText=$vmText -join "`n";$script:TestOperations=[Collections.Generic.List[string]]::new();$script:TestStarted=$false
    Set-Item Function:script:Read-Profile {param($Path,$ExpectedSHA256) return ,$script:TestProfile}
    Set-Item Function:script:Assert-Principal {param($SID,[switch]$Standard)}
    Set-Item Function:script:Read-Request {param($Profile,$Hash,$Attempt) return ,$script:TestRequest}
    Set-Item Function:script:Assert-Path {param($Path,$Writers,[switch]$External)}
    Set-Item Function:script:Assert-ClaimPolicy {param($Profile)}
    Set-Item Function:script:Read-Bytes {param($Path,$Maximum,$Hash) return ,([byte[]]@(1))}
    Set-Item Function:script:Assert-StorageReserve {}
    Set-Item Function:script:Assert-HostMemoryReserve {}
    Set-Item Function:script:Assert-ImageChain {param($Info,$Profile,$Request,$Root,[ref]$Sequence) return ('9'*64)}
    Set-Item Function:script:Now-UTC {return $script:TestNow}
    Set-Item Function:script:Invoke-Operation {
      param($Operation,$Profile,$Request,$AttemptRoot,$Sequence,$CancelAfterMS=0,$DiskUUID='')
      $script:TestOperations.Add($Operation)
      if($Operation -ceq 'Start'){$script:TestStarted=$true;if($script:TestScenario -ceq 'start_uncertain'){Fail 'SIMULATED_START_UNCERTAIN'}}
      if($Operation -ceq 'PowerOff'){$script:TestStarted=$false;if($script:TestScenario -ceq 'cleanup_uncertain'){Fail 'SIMULATED_CLEANUP_UNCERTAIN'}}
      $output=switch($Operation){Inspect {if($script:TestStarted){$script:TestVMText.Replace('VMState"="poweroff"','VMState"="running"')}else{$script:TestVMText}}Readiness {"Value: 3`n"}Run {JSON $script:TestGuest}default {''}}
      return [ordered]@{state='EXITED';exit_code=0;owned_process_termination_confirmed=$true;stdout=$output;stderr=''}
    }
    if($scenario -ceq 'replayed'){New-JSON (Fixed-Path ('worker_claims\'+$id+'.claim')) @{attempt_id=$id}}
    $r=Invoke-AIBSWorkerProbe -ProfilePath 'mocked' -ExpectedProfileSHA256 $pin -AttemptID $id
    switch($scenario){
      passed {Require ($r.state -ceq 'PASSED' -and $r.worker_observed.terminal_state -ceq 'poweroff' -and $r.worker_observed.accepted_snapshot_restored -and -not $r.full_containment_accepted -and -not $r.candidate_execution_authorized) ('MOCK_SUCCESS_FAILED '+$r.error_code);Require (($script:TestOperations -join ',') -ceq 'Inspect,Restore,Inspect,Start,Inspect,Readiness,Run,PowerOff,Inspect,Restore,Inspect') 'LIFECYCLE_OPERATION_ORDER'}
      start_uncertain {Require ($r.state -ceq 'BLOCKED' -and $r.permanent_attempt_claimed -and $script:TestOperations.Contains('PowerOff') -and $r.worker_observed.accepted_snapshot_restored) 'UNCERTAIN_START_NOT_CLEANED'}
      cleanup_uncertain {Require ($r.state -ceq 'QUARANTINED' -and $r.error_code -ceq 'VM_TERMINATION_UNCONFIRMED') 'UNCERTAIN_CLEANUP_NOT_QUARANTINED'}
      replayed {Require ($r.state -ceq 'BLOCKED' -and $script:TestOperations.Count -eq 0) 'REPLAY_REACHED_VM_CONTROL'}
    }
   }finally{foreach($name in $names){Set-Item ('Function:script:'+ $name) $originals[$name]};$script:Root=$originalRoot;Close-Held}
  }
 }
 foreach($scenario in @('interrupted','quarantined','tampered','settled')){
  Check ('permanent reservation reconciliation '+$scenario) {
   $originalRoot=$script:Root;$originalACL=(Get-Item Function:Assert-Path).ScriptBlock;$originalKey=(Get-Item Function:Read-ReceiptKey).ScriptBlock
   try{
    $script:Root=Join-Path $EvidenceDirectory ('reconcile-'+$scenario)
    foreach($dir in @('state','receipts')){$null=[IO.Directory]::CreateDirectory((Fixed-Path $dir))}
    New-JSON (Fixed-Path ('state\'+$id+'.reservation.json')) @{attempt_id=$id}
    Set-Item Function:script:Assert-Path {param($Path,$Writers,[switch]$External)}
    Set-Item Function:script:Read-ReceiptKey {return ,([byte[]](0..31))}
    if($scenario -cne 'interrupted'){
      $body=Parsed @{domain='AI-BS/host-fixed-probe-receipt/v1';attempt_id=$id;profile_sha256=$pin;state=$(if($scenario -ceq 'quarantined'){'QUARANTINED'}else{'PASSED'});worker_reported=@{worker_observed=@{accepted_snapshot_restored=$true}}}
      $receipt=Parsed @{body=$body;hmac_sha256=(Receipt-Tag $body ([byte[]](0..31)))}
      if($scenario -ceq 'tampered'){$receipt.body.state='CANCELLED'}
      New-JSON (Fixed-Path ('receipts\'+$id+'.json')) $receipt
    }
    switch($scenario){
      interrupted {Expect-Failure {Assert-NoPendingAttempt} 'PENDING_ATTEMPT_RECONCILIATION_REQUIRED'}
      quarantined {Expect-Failure {Assert-NoPendingAttempt} 'UNCERTAIN_ATTEMPT_RECONCILIATION_REQUIRED'}
      tampered {Expect-Failure {Assert-NoPendingAttempt} 'RECEIPT_AUTHENTICATION_FAILED'}
      settled {Assert-NoPendingAttempt}
    }
   }finally{Set-Item Function:script:Assert-Path $originalACL;Set-Item Function:script:Read-ReceiptKey $originalKey;$script:Root=$originalRoot;Close-Held}
  }
 }
 Check 'retained bootstrap reservation does not corrupt diagnostic attempt index' {
   $originalRoot=$script:Root
   try{
     $script:Root=Join-Path $EvidenceDirectory 'separate-bootstrap-index'
     $null=[IO.Directory]::CreateDirectory((Fixed-Path 'state'))
     New-JSON (Fixed-Path ('state\bootstrap-'+$id+'.bootstrap_reserved.json')) @{purpose='bootstrap_readback_snapshot_v1';attempt_id=$id;status='RESERVED_NO_AUTOMATIC_REPLAY'}
     Assert-NoPendingAttempt
   }finally{$script:Root=$originalRoot;Close-Held}
 }
 Check 'public worker fails closed before runtime when isolation missing' {
   $original=(Get-Item Function:Read-Profile).ScriptBlock
   try{Set-Item Function:script:Read-Profile {param($Path,$ExpectedSHA256) Fail 'ISOLATION_UNAVAILABLE'};$r=Invoke-AIBSWorkerProbe -ProfilePath 'unavailable' -ExpectedProfileSHA256 ('0'*64) -AttemptID $id;Require ($r.state -ceq 'BLOCKED' -and $r.error_code -ceq 'ISOLATION_UNAVAILABLE' -and -not $r.permanent_attempt_claimed) 'FAIL_CLOSED_FAILED'}
   finally{Set-Item Function:script:Read-Profile $original}
 }
 Close-Held
 return [ordered]@{schema_version=1;evidence_class='trusted_controller_infrastructure_only';disposable_vm_checks_performed=$false;candidate_tests_executed=$false;checks=@($checks.ToArray());passed=@($checks|Where-Object passed).Count;failed=@($checks|Where-Object {-not $_.passed}).Count;completed_utc=[DateTime]::UtcNow.ToString('o')}
} $EvidenceDirectory $PSScriptRoot
$path=Join-Path $EvidenceDirectory 'results.json'
[IO.File]::WriteAllText($path,($report|ConvertTo-Json -Depth 8),[Text.UTF8Encoding]::new($false))
$report.checks|Where-Object {-not $_.passed}|ForEach-Object {[PSCustomObject]$_}|Format-Table name,error -Wrap
Write-Output ('Infrastructure: '+$report.passed+' passed; '+$report.failed+' failed. '+$path)
if($report.failed -gt 0){exit 1}
