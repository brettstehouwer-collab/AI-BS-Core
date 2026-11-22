# Trusted parser, exact shared primitive parity, and constrained-input checks only.
[CmdletBinding()]param()
Set-StrictMode -Version Latest
$ErrorActionPreference='Stop';$checks=0
function Check([bool]$Condition,[string]$Name){if(-not $Condition){throw ('FAILED_'+$Name)};$script:checks++;Write-Output ('PASS '+$Name)}
$path=Join-Path $PSScriptRoot 'Inspect-WorkerWinPE.ps1';$tokens=$null;$errors=$null;$ast=[Management.Automation.Language.Parser]::ParseFile($path,[ref]$tokens,[ref]$errors)
Check (@($errors).Count -eq 0) 'winpe_source_parses'
$reference=[Management.Automation.Language.Parser]::ParseFile((Join-Path $PSScriptRoot 'Resume-InstalledWorker.ps1'),[ref]$tokens,[ref]$errors)
foreach($name in @('Require','Parse-ObservedMachine','Verify-ObservedMachine','Verify-RecoveryStorage','New-ObservationCommandRecord','VBox-Observe')){
 $a=$ast.Find({param($n)$n -is [Management.Automation.Language.FunctionDefinitionAst] -and $n.Name -ceq $name},$true);$b=$reference.Find({param($n)$n -is [Management.Automation.Language.FunctionDefinitionAst] -and $n.Name -ceq $name},$true)
 Check ($null -ne $a -and $null -ne $b -and $a.Extent.Text -ceq $b.Extent.Text) ('tested_primitive_exact_parity_'+$name)
}
$text=$ast.Extent.Text
Check (($ast.ParamBlock.Parameters.Name.VariablePath.UserPath -join ',') -ceq 'OpenConsole,ListDisks') 'only_two_fixed_switches_no_input_parameter'
Check ($text.Contains("@('controlvm',`$vm,'keyboardputscancode','2a','44','c4','aa')")) 'only_fixed_shift_f10_open'
Check ($text.Contains("`$command='mode con: cols=120 lines=40 & cls & (echo list disk&echo list volume&echo exit)|diskpart'")) 'literal_read_only_diskpart_pipeline'
Check (@([regex]::Matches($text,"'keyboardputstring'")).Count -eq 1 -and @([regex]::Matches($text,"'keyboardputscancode'")).Count -eq 2) 'exactly_one_literal_command_and_enter'
Check (-not ($text -match "'storageattach'|'changevar'|'startvm'|@\('controlvm',\`$vm,'poweroff'|@\('controlvm',\`$vm,'reset'|bcdboot|format volume|clean disk")) 'no_storage_firmware_boot_or_repair_operation'
Check ($text.Contains("'worker_state\installation-winpe-'+`$phase+'.started')),'CreateNew','Write','None'")) 'single_use_phase_marker'
Check ($text.IndexOf('$marker.Flush($true)') -lt $text.IndexOf("@('controlvm',`$vm,'keyboardputscancode'")) 'durable_intent_before_keyboard'
Check ($text.Contains("'REVIEW_OPEN_CONSOLE_SCREEN_BEFORE_FIXED_DISK_QUERY'")) 'disk_query_requires_open_phase_evidence'
Check ($text.Contains("`$beforeScreen=Save-FixedScreen 'before.png'") -and $text.Contains("`$afterScreen=Save-FixedScreen 'after.png'")) 'screens_before_and_after_input'
Check ($text.Contains("'SCREENSHOT_FILE_BOUND'") -and $text.Contains('2097152') -and $text.Contains('89504E470D0A1A0A')) 'bounded_png_retention'
Check ($text.Contains("'UNSEALED_INSTALLATION_DIAGNOSTICS_ONLY'") -and $text.Contains("'policy\profile.json'")) 'sealed_worker_refused'
Check ($text.Contains("'deployment\Inspect-WorkerWinPE.ps1'") -and $text.Contains("'EXACT_STANDARD_HOST_LAUNCHER_REQUIRED'")) 'protected_exact_standard_host_entry'
Check ($text.Contains('fixed_installation_console_input=$true') -and $text.Contains('candidate_execution=$false')) 'authority_report_does_not_hide_keyboard_input'
[pscustomobject]@{schema_version=1;infrastructure_checks_passed=$checks;winpe_entry_executed=$false;vm_operations=0;guest_input=0}|ConvertTo-Json
