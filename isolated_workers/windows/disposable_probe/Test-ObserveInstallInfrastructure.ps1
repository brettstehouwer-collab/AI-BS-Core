# Only pure parsing/profile checks. The observation entry and VBox helper never run.
[CmdletBinding()]param()
Set-StrictMode -Version Latest
$ErrorActionPreference='Stop';$checks=0
function Check([bool]$Condition,[string]$Name){if(-not $Condition){throw ('FAILED_'+$Name)};$script:checks++;Write-Output ('PASS '+$Name)}
$source=Join-Path $PSScriptRoot 'Observe-InstallScreen.ps1';$tokens=$null;$errors=$null
$ast=[Management.Automation.Language.Parser]::ParseFile($source,[ref]$tokens,[ref]$errors)
Check (@($errors).Count -eq 0) 'observer_parses'
foreach($name in @('Require','Parse-ObservedMachine','Verify-ObservedMachine','New-ObservationCommandRecord')){
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
[pscustomobject]@{schema_version=1;infrastructure_checks_passed=$checks;observer_entry_executed=$false;vm_operations=0;guest_input=0}|ConvertTo-Json
