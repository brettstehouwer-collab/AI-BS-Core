# Only pure parsing/profile checks. The observation entry and VBox helper never run.
[CmdletBinding()]param()
Set-StrictMode -Version Latest
$ErrorActionPreference='Stop';$checks=0
function Check([bool]$Condition,[string]$Name){if(-not $Condition){throw ('FAILED_'+$Name)};$script:checks++;Write-Output ('PASS '+$Name)}
$source=Join-Path $PSScriptRoot 'Resume-InstalledWorker.ps1';$tokens=$null;$errors=$null
$ast=[Management.Automation.Language.Parser]::ParseFile($source,[ref]$tokens,[ref]$errors)
Check (@($errors).Count -eq 0) 'observer_parses'
foreach($name in @('Require','Parse-ObservedMachine','Verify-ObservedMachine','New-ObservationCommandRecord','New-ReviewedBootOrder','Verify-RecoveryStorage')){
 $node=$ast.Find({param($a)$a -is [Management.Automation.Language.FunctionDefinitionAst] -and $a.Name -ceq $name},$true)
 Check ($null -ne $node) ('pure_function_'+$name);. ([scriptblock]::Create($node.Extent.Text))
}
$vm='e5a2fe34-7b90-460c-83af-903d51b4bb16'
$fixture=@(('UUID="'+$vm+'"'),'name="AI-BS-DisposableProbe-20261026"','VMState="poweroff"','memory=4096','cpus=4','firmware="EFI"','SecureBoot="on"','clipboard="disabled"','clipboard_file_transfers="off"','draganddrop="disabled"','vrde="off"','usb="off"','audio="none"','audio_in="off"','audio_out="off"')
foreach($n in 1..8){$fixture+='nic'+$n+'="none"'};foreach($n in 1..4){$fixture+='uart'+$n+'="off"'}
$text=$fixture -join "`r`n";$map=Parse-ObservedMachine $text;Verify-ObservedMachine $map;Check $true 'powered_off_observation_allowed'
$map['VMState']='running';Verify-ObservedMachine $map;Check $true 'running_observation_allowed'
foreach($mutation in @(@('UUID','6c5a53da-ab80-4ecb-8be6-4059266f736e'),@('VMState','paused'),@('memory','8192'),@('firmware','BIOS'),@('SecureBoot','off'),@('nic1','nat'),@('uart1','server'),@('audio','was'),@('clipboard','bidirectional'))){
 $bad=Parse-ObservedMachine $text;$bad[$mutation[0]]=$mutation[1];$rejected=$false;try{Verify-ObservedMachine $bad}catch{$rejected=$true};Check $rejected ('reject_'+$mutation[0])
}
$bad=Parse-ObservedMachine $text;$bad.Add('SharedFolderNameMachineMapping1','private');$rejected=$false;try{Verify-ObservedMachine $bad}catch{$rejected=$true};Check $rejected 'reject_shared_folder'
$rejected=$false;try{$null=Parse-ObservedMachine ($text+"`r`nUUID=`"$vm`"")}catch{$rejected=$true};Check $rejected 'reject_duplicate_property'
$rejected=$false;try{$null=Parse-ObservedMachine ($text+"`r`nnot a property")}catch{$rejected=$true};Check $rejected 'reject_malformed_property'
$rawOut=[byte[]]@(255,0,1);$rawErr=[Text.Encoding]::UTF8.GetBytes('Display not available')
$retained=New-ObservationCommandRecord @('controlvm',$vm,'screenshotpng','C:\fixed\screen.png','0') $rawOut $rawErr 1 'OBSERVATION_COMMAND_EXIT_1' 73 $true
Check ($retained.exit_code -eq 1 -and $retained.error_code -ceq 'OBSERVATION_COMMAND_EXIT_1' -and $retained.combined_bytes -eq 24) 'retain_nonzero_command_evidence'
Check ([Convert]::ToHexString([Convert]::FromBase64String($retained.stdout_base64)) -ceq 'FF0001' -and [Text.Encoding]::UTF8.GetString([Convert]::FromBase64String($retained.stderr_base64)) -ceq 'Display not available') 'retain_exact_raw_console_bytes'
Check ($retained.classification -ceq 'PRIVATE_INSTALLATION_OBSERVATION_EXCLUDE_FROM_LEDGER' -and $retained.termination_confirmed -and $retained.arguments_sha256 -cmatch '^[0-9a-f]{64}$') 'retention_private_and_bound_to_command'
$rejected=$false;try{$null=New-ObservationCommandRecord @('showvminfo',$vm,'--machinereadable') ([byte[]]::new(131072)) ([byte[]]@(1)) 0 '' 1 $true}catch{$rejected=$true};Check $rejected 'retained_console_ceiling'
Check ($ast.Extent.Text.IndexOf('$attempt=Join-Path') -lt $ast.Extent.Text.IndexOf('$beforeText=VBox-Observe')) 'retention_exists_before_first_command'
$sourceText=$ast.Extent.Text
Check ($sourceText.Contains("'modifynvram',`$vm,'listvars'")) 'only_fixed_nvram_listing'
Check (-not ($sourceText -match 'deletevar|inituefivarstore|keyboardputscancode|storageattach')) 'no_firmware_delete_secureboot_guest_input_or_media_mutations'
Check ($sourceText.Contains("@('modifynvram',`$vm,'changevar','--name=BootOrder',('--filename='+`$newPath))") -and @([regex]::Matches($sourceText,"'changevar'")).Count -eq 1) 'only_reviewed_existing_bootorder_write'
Check ($sourceText.Contains("'worker_state\provision.lease'),'Open','ReadWrite','None'")) 'exclusive_provision_lease'
Check ($sourceText.Contains("'deployment\Resume-InstalledWorker.ps1'")) 'protected_deployment_required'
Check ($sourceText.Contains("'intent.json'")) 'intent_retained_before_inspection'
Check ($sourceText.Contains("'worker_state\installation-recovery-poweroff.started'),'CreateNew','Write','None'")) 'recovery_is_permanently_single_use'
Check ($sourceText.IndexOf('$recoveryMarker.Flush($true)') -lt $sourceText.IndexOf("@('controlvm',`$vm,'poweroff')")) 'recovery_intent_flushed_before_poweroff'
Check ($sourceText.Contains("'policy\profile.json'" ) -and $sourceText.Contains("'UNSEALED_INSTALLATION_RECOVERY_ONLY'")) 'recovery_refuses_sealed_worker'
Check (-not ($sourceText -match "@\('controlvm',\`$vm,'reset'")) 'recovery_never_resets_vm'
Check ($sourceText.Contains("@('BootOrder','Boot0000','Boot0001','Boot0002')")) 'only_four_observed_variable_names'
Check ($sourceText.Contains("'POWERED_OFF_EFI_QUERY_REQUIRED'")) 'binary_queries_require_powered_off_vm'
Check ($sourceText.Contains("('--filename='+`$binary)") -and $sourceText.Contains("`$item.Length -le 65536")) 'binary_queries_retain_bounded_raw_values'
Check ($sourceText.Contains("'EFI_OUTPUT_ALREADY_EXISTS'") -and $sourceText.Contains('boot_entries=$bootEntries')) 'binary_outputs_unique_and_reported'
$reordered=New-ReviewedBootOrder ([byte[]]@(0,0,1,0,2,0));Check ([Convert]::ToHexString($reordered) -ceq '020000000100') 'exact_observed_order_moves_existing_disk_first'
foreach($badOrder in @(([byte[]]@(0,0,1,0)),([byte[]]@(0,0,1,0,3,0)),([byte[]]@(1,0,0,0,2,0)),([byte[]]@(0,0,0,0,2,0)))){$rejected=$false;try{$null=New-ReviewedBootOrder $badOrder}catch{$rejected=$true};Check $rejected 'changed_or_malformed_order_rejected'}
$storage=Parse-ObservedMachine $text;$storage.Add('SATA-0-0','E:\\AI-BS-DisposableProbe-v1\\system.vdi');$storage.Add('SATA-ImageUUID-0-0','5b4f5331-0da2-491d-a257-6b4ecf435a5a');$storage.Add('SATA-1-0','C:\\ProgramData\\AI-BS-WorkerControl\\disposable_probe_v1\\worker_state\\install-7ee7b2b0fee14edc840e6444a4ce0401\\media-aux-iso.viso');$storage.Add('SATA-ImageUUID-1-0','32a30818-96b5-462e-8550-d68d18eebc8a');$storage.Add('SATA-IsEjected-1-0','off');Verify-RecoveryStorage $storage;Check $true 'exact_escaped_machine_disk_and_media_accepted'
foreach($pair in @(@('SATA-0-0','E:\\other.vdi'),@('SATA-ImageUUID-0-0','6c5a53da-ab80-4ecb-8be6-4059266f736e'),@('SATA-IsEjected-1-0','on'),@('SATA-1-0','emptydrive'))){$saved=$storage[$pair[0]];$storage[$pair[0]]=$pair[1];$rejected=$false;try{Verify-RecoveryStorage $storage}catch{$rejected=$true};$storage[$pair[0]]=$saved;Check $rejected 'changed_disk_or_media_rejected'}
$storage.Add('SATA-2-0','unexpected.iso');$rejected=$false;try{Verify-RecoveryStorage $storage}catch{$rejected=$true};Check $rejected 'unexpected_media_port_rejected'
Check ($sourceText.Contains("'worker_state\installation-recovery-diskboot.started'),'CreateNew','Write','None'")) 'disk_recovery_permanent_single_use'
Check ($sourceText.IndexOf("`$recoveryMarker.Flush(`$true)`n  `$null=VBox-Observe @('modifynvram'") -ge 0) 'disk_recovery_intent_flushed_before_firmware_write'
Check ($sourceText.Contains("'FIRMWARE_ORDER_READBACK_MISMATCH'") -and $sourceText.Contains("'CURRENT_RAM_UNAVAILABLE'")) 'exact_order_readback_and_live_ram_before_start'
[pscustomobject]@{schema_version=1;infrastructure_checks_passed=$checks;inspection_entry_executed=$false;vm_operations=0;guest_input=0}|ConvertTo-Json
