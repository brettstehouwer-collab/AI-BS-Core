# Trusted parser and fixed read-only setup-observation contract checks only.
[CmdletBinding()]param()
Set-StrictMode -Version Latest
$ErrorActionPreference='Stop';$checks=0
function Check([bool]$Condition,[string]$Name){if(-not $Condition){throw ('FAILED_'+$Name)};$script:checks++;Write-Output ('PASS '+$Name)}
$path=Join-Path $PSScriptRoot 'Inspect-WorkerSetupFailure.ps1';$tokens=$null;$errors=$null;$ast=[Management.Automation.Language.Parser]::ParseFile($path,[ref]$tokens,[ref]$errors)
Check (@($errors).Count -eq 0) 'setup_failure_source_parses'
$reference=[Management.Automation.Language.Parser]::ParseFile((Join-Path $PSScriptRoot 'Inspect-WorkerWinPE.ps1'),[ref]$tokens,[ref]$errors)
foreach($name in @('Require','Parse-ObservedMachine','Verify-ObservedMachine','Verify-RecoveryStorage','New-ObservationCommandRecord','VBox-Observe')){
 $a=$ast.Find({param($n)$n -is [Management.Automation.Language.FunctionDefinitionAst] -and $n.Name -ceq $name},$true);$b=$reference.Find({param($n)$n -is [Management.Automation.Language.FunctionDefinitionAst] -and $n.Name -ceq $name},$true)
 Check ($null -ne $a -and $null -ne $b -and $a.Extent.Text -ceq $b.Extent.Text) ('tested_primitive_exact_parity_'+$name)
}
$text=$ast.Extent.Text
Check (($ast.ParamBlock.Parameters.Name.VariablePath.UserPath -join ',') -ceq 'InspectSetupFailure') 'one_fixed_switch_no_input_parameter'
$expected='cls & dir /a C:\$Windows.~BT & dir /a C:\$Windows.~BT\Sources & dir /a C:\$Windows.~BT\NewOS\Windows\System32\winload.efi & dir /a C:\$Windows.~BT\Sources\Panther & type C:\$Windows.~BT\Sources\Panther\setuperr.log'
$assignment=$ast.Find({param($n)$n -is [Management.Automation.Language.AssignmentStatementAst] -and $n.Left.Extent.Text -ceq '$command'},$true)
Check ($assignment.Right.Extent.Text -ceq ("'"+$expected+"'")) 'literal_staging_paths_and_single_private_error_log'
Check (@([regex]::Matches($text,"'keyboardputstring'")).Count -eq 1 -and @([regex]::Matches($text,"'keyboardputscancode'")).Count -eq 1) 'exactly_one_literal_command_and_enter'
Check ($text.Contains("@('controlvm',`$vm,'keyboardputscancode','1c','9c')")) 'only_fixed_enter_scancodes'
Check (-not ($text -match "'storageattach'|'changevar'|'startvm'|@\('controlvm',\`$vm,'poweroff'|@\('controlvm',\`$vm,'reset'|bcdboot|format volume|clean disk|\|diskpart|bcdedit")) 'no_storage_firmware_boot_repair_or_enumeration_change'
Check ($text.Contains("'worker_state\installation-winpe-'+`$phase+'.started')),'CreateNew','Write','None'") -and $text.Contains("`$phase='setup-failure'")) 'single_use_setup_phase_marker'
Check ($text.IndexOf('$marker.Flush($true)') -lt $text.IndexOf("@('controlvm',`$vm,'keyboardputstring'")) 'durable_intent_before_keyboard'
Check ($text.Contains("'RETAINED_DISK_QUERY_REQUIRED'") -and $text.Contains("'REVIEW_FIXED_WINDOWS_PATH_QUERY_BEFORE_SETUP_LOG_QUERY'")) 'prior_disk_and_path_query_required'
Check ($text.Contains("`$beforeScreen=Save-FixedScreen 'before.png'") -and $text.Contains("`$afterScreen=Save-FixedScreen 'after.png'")) 'screens_before_and_after_input'
Check ($text.Contains("'SCREENSHOT_FILE_BOUND'") -and $text.Contains('2097152') -and $text.Contains('89504E470D0A1A0A')) 'bounded_private_console_images'
Check ($text.Contains('PRIVATE_INSTALLATION_OBSERVATION_EXCLUDE_FROM_LEDGER')) 'raw_command_records_private'
Check ($text.Contains("'UNSEALED_INSTALLATION_DIAGNOSTICS_ONLY'") -and $text.Contains("'policy\profile.json'")) 'sealed_worker_refused'
Check ($text.Contains("'deployment\Inspect-WorkerSetupFailure.ps1'") -and $text.Contains("'EXACT_STANDARD_HOST_LAUNCHER_REQUIRED'")) 'protected_exact_standard_host_entry'
Check ($text.Contains('fixed_installation_console_input=$true') -and $text.Contains('candidate_execution=$false') -and $text.Contains('disk_writes=$false')) 'authority_report_matches_observation_scope'
[pscustomobject]@{schema_version=1;infrastructure_checks_passed=$checks;setup_entry_executed=$false;vm_operations=0;guest_input=0}|ConvertTo-Json
