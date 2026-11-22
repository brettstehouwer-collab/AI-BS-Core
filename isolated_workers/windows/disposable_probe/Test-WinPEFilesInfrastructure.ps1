# Trusted parser and constrained fixed-input checks; never invokes either VM entry.
[CmdletBinding()]param()
Set-StrictMode -Version Latest
$ErrorActionPreference='Stop';$checks=0
function Check([bool]$Condition,[string]$Name){if(-not $Condition){throw ('FAILED_'+$Name)};$script:checks++;Write-Output ('PASS '+$Name)}
$path=Join-Path $PSScriptRoot 'Inspect-WorkerWinPEFiles.ps1';$tokens=$null;$errors=$null;$ast=[Management.Automation.Language.Parser]::ParseFile($path,[ref]$tokens,[ref]$errors)
Check (@($errors).Count -eq 0) 'files_source_parses'
$reference=[Management.Automation.Language.Parser]::ParseFile((Join-Path $PSScriptRoot 'Inspect-WorkerWinPE.ps1'),[ref]$tokens,[ref]$errors)
foreach($name in @('Require','Parse-ObservedMachine','Verify-ObservedMachine','Verify-RecoveryStorage','New-ObservationCommandRecord','VBox-Observe')){
 $a=$ast.Find({param($n)$n -is [Management.Automation.Language.FunctionDefinitionAst] -and $n.Name -ceq $name},$true);$b=$reference.Find({param($n)$n -is [Management.Automation.Language.FunctionDefinitionAst] -and $n.Name -ceq $name},$true)
 Check ($null -ne $a -and $null -ne $b -and $a.Extent.Text -ceq $b.Extent.Text) ('tested_primitive_exact_parity_'+$name)
}
$text=$ast.Extent.Text
Check (($ast.ParamBlock.Parameters.Name.VariablePath.UserPath -join ',') -ceq 'CancelDiskQuery,InspectWindows') 'only_two_fixed_switches_no_input_parameter'
Check ($text.Contains("@('controlvm',`$vm,'keyboardputscancode','1d','2e','ae','9d')")) 'exact_ctrl_c_only_cancellation_input'
Check ($text.Contains("`$command='cls & dir /a C:\ & dir /a C:\Windows\System32\winload.efi & dir /a C:\Windows\Boot\EFI\bootmgfw.efi & bcdedit /enum firmware'")) 'literal_read_only_fixed_path_and_firmware_query'
Check (@([regex]::Matches($text,"'keyboardputstring'")).Count -eq 1 -and @([regex]::Matches($text,"'keyboardputscancode'")).Count -eq 2) 'one_literal_command_and_fixed_enter'
Check (-not ($text -match "'storageattach'|'changevar'|'startvm'|@\('controlvm',\`$vm,'poweroff'|@\('controlvm',\`$vm,'reset'|bcdboot|format volume|clean disk|\|diskpart")) 'no_storage_firmware_boot_repair_or_diskpart_replay'
Check ($text.Contains("'worker_state\installation-winpe-'+`$phase+'.started')),'CreateNew','Write','None'")) 'single_use_distinct_phase_marker'
Check ($text.IndexOf('$marker.Flush($true)') -lt $text.IndexOf("@('controlvm',`$vm,'keyboardputscancode'")) 'durable_intent_before_keyboard'
Check ($text.Contains("'RETAINED_DISK_QUERY_REQUIRED'") -and $text.Contains("'REVIEW_CANCEL_SCREEN_CMD_PROMPT_BEFORE_FIXED_PATH_QUERY'")) 'retained_prior_query_and_prompt_review_boundary'
Check ($text.Contains("`$phase=if(`$CancelDiskQuery){'cancel-disk-query'}else{'inspect-windows'}")) 'independent_permanent_phase_scopes'
Check ($text.Contains("`$beforeScreen=Save-FixedScreen 'before.png'") -and $text.Contains("`$afterScreen=Save-FixedScreen 'after.png'")) 'screens_before_and_after_input'
Check ($text.Contains("'SCREENSHOT_FILE_BOUND'") -and $text.Contains('2097152') -and $text.Contains('89504E470D0A1A0A')) 'bounded_png_retention'
Check ($text.Contains("'UNSEALED_INSTALLATION_DIAGNOSTICS_ONLY'") -and $text.Contains("'policy\profile.json'")) 'sealed_worker_refused'
Check ($text.Contains("'deployment\Inspect-WorkerWinPEFiles.ps1'") -and $text.Contains("'EXACT_STANDARD_HOST_LAUNCHER_REQUIRED'")) 'protected_exact_standard_host_entry'
Check ($text.Contains('fixed_installation_console_input=$true') -and $text.Contains('candidate_execution=$false') -and $text.Contains('disk_writes=$false')) 'authority_report_matches_bounded_input'
[pscustomobject]@{schema_version=1;infrastructure_checks_passed=$checks;winpe_entry_executed=$false;vm_operations=0;guest_input=0}|ConvertTo-Json
