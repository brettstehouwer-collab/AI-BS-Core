# Trusted parser/guard and harmless native-CMD fixture tests only. No VM entry.
[CmdletBinding()]param()
Set-StrictMode -Version Latest
$ErrorActionPreference='Stop';$checks=0
$evidence=Join-Path $PSScriptRoot ('evidence\setup-progress-infra-'+[DateTime]::UtcNow.ToString('yyyyMMddTHHmmssZ')+'-'+[Guid]::NewGuid().ToString('N'))
$null=[IO.Directory]::CreateDirectory($evidence)
$script:observations=[Collections.Generic.List[object]]::new()
function Check([bool]$Condition,[string]$Name){if(-not $Condition){throw ('FAILED_'+$Name)};$script:checks++;$script:observations.Add([ordered]@{check=$Name;passed=$true});Write-Output ('PASS '+$Name)}
function Run-CmdFixture([string]$Command){
 $start=[Diagnostics.ProcessStartInfo]::new('C:\Windows\System32\cmd.exe');$start.UseShellExecute=$false;$start.CreateNoWindow=$true;$start.RedirectStandardOutput=$true;$start.RedirectStandardError=$true;$start.Arguments='/d /c '+$Command
 $process=[Diagnostics.Process]::Start($start)
 try{$out=$process.StandardOutput.ReadToEnd();$err=$process.StandardError.ReadToEnd();if(-not $process.WaitForExit(10000)){$process.Kill();throw 'TRUSTED_CMD_FIXTURE_TIMEOUT'};return [pscustomobject]@{exit=$process.ExitCode;stdout=$out;stderr=$err}}
 finally{$process.Dispose()}
}
try{
 $path=Join-Path $PSScriptRoot 'Inspect-WorkerSetupProgress.ps1';$tokens=$null;$errors=$null;$ast=[Management.Automation.Language.Parser]::ParseFile($path,[ref]$tokens,[ref]$errors)
 Check (@($errors).Count -eq 0) 'setup_progress_source_parses'
 $reference=[Management.Automation.Language.Parser]::ParseFile((Join-Path $PSScriptRoot 'Inspect-WorkerWinPE.ps1'),[ref]$tokens,[ref]$errors)
 foreach($name in @('Require','Parse-ObservedMachine','Verify-ObservedMachine','Verify-RecoveryStorage','New-ObservationCommandRecord','VBox-Observe')){
  $a=$ast.Find({param($n)$n -is [Management.Automation.Language.FunctionDefinitionAst] -and $n.Name -ceq $name},$true);$b=$reference.Find({param($n)$n -is [Management.Automation.Language.FunctionDefinitionAst] -and $n.Name -ceq $name},$true)
  Check ($null -ne $a -and $null -ne $b -and $a.Extent.Text -ceq $b.Extent.Text) ('tested_primitive_exact_parity_'+$name)
 }
 $text=$ast.Extent.Text
 Check (($ast.ParamBlock.Parameters.Name.VariablePath.UserPath -join ',') -ceq 'InspectStageInventory,InspectSetupTail') 'two_fixed_switches_no_input_parameter'
 Check ($text.Contains('([int][bool]$InspectStageInventory+[int][bool]$InspectSetupTail) -eq 1')) 'exactly_one_phase_required'
 $assignments=@($ast.FindAll({param($n)$n -is [Management.Automation.Language.AssignmentStatementAst] -and $n.Left.Extent.Text -ceq '$command'},$true))
 Check ($assignments.Count -eq 2) 'exactly_two_fixed_literal_commands'
 $commands=@($assignments|ForEach-Object{$_.Right.Find({param($n)$n -is [Management.Automation.Language.StringConstantExpressionAst]},$true).Value})
 $expectedInventory='cls & for %F in (C:\$Windows.~BT\NewOS\Windows\System32\winload.efi C:\$Windows.~BT\NewOS\Windows\Boot\EFI\bootmgfw.efi C:\Windows\System32\winload.efi C:\$Windows.~BT\Sources\Panther\setupact.log C:\$Windows.~BT\Sources\Rollback\setupact.log C:\$Windows.~BT\NewOS\Windows\Panther\setupact.log X:\Windows\Panther\setupact.log) do @if exist %F (echo FILE_PRESENT_BYTES %~zF %F) else @echo FILE_MISSING %F'
 $expectedTail='cls & echo SETUPACT_LAST_6_LINES & for /f %N in (''find /v /c "" ^< C:\$Windows.~BT\Sources\Panther\setupact.log'') do @if %N GTR 6 (for /f %S in (''set /a %N-6'') do @more +%S C:\$Windows.~BT\Sources\Panther\setupact.log) else @type C:\$Windows.~BT\Sources\Panther\setupact.log'
 Check ($commands[0] -ceq $expectedInventory) 'inventory_exact_three_boot_paths_and_four_log_paths'
 Check ($commands[1] -ceq $expectedTail) 'tail_exact_six_lines_one_known_log'
 Check (@([regex]::Matches($text,"'keyboardputstring'")).Count -eq 1 -and @([regex]::Matches($text,"'keyboardputscancode'")).Count -eq 1) 'one_fixed_command_then_enter_per_phase'
 Check ($text.Contains("@('controlvm',`$vm,'keyboardputscancode','1c','9c')")) 'only_fixed_enter_scancodes'
 Check (-not ($text -match "'storageattach'|'changevar'|'startvm'|@\('controlvm',\`$vm,'poweroff'|@\('controlvm',\`$vm,'reset'|bcdboot|format volume|clean disk|\|diskpart|bcdedit|set-content|out-file|autounattend")) 'no_disk_or_firmware_writes_repair_or_answerfile_reads'
 Check ($text.Contains("'worker_state\installation-winpe-'+`$phase+'.started')),'CreateNew','Write','None'") -and $text.Contains("`$phase=if(`$InspectStageInventory){'setup-inventory'}else{'setup-tail'}")) 'separate_permanent_one_use_phase_markers'
 Check ($text.IndexOf('$marker.Flush($true)') -lt $text.IndexOf("@('controlvm',`$vm,'keyboardputstring'")) 'durable_intent_before_keyboard'
 Check ($text.Contains("'REVIEW_SETUP_FAILURE_BEFORE_PROGRESS_QUERY'") -and $text.Contains("if(`$InspectSetupTail){Require (") -and $text.Contains("'REVIEW_SETUP_INVENTORY_BEFORE_TAIL'")) 'prior_reviewed_setup_observation_and_inventory_required'
 Check ($text.Contains("`$beforeScreen=Save-FixedScreen 'before.png'") -and $text.Contains("`$afterScreen=Save-FixedScreen 'after.png'")) 'screens_before_and_after_input'
 Check ($text.Contains("'SCREENSHOT_FILE_BOUND'") -and $text.Contains('2097152') -and $text.Contains('89504E470D0A1A0A')) 'bounded_private_console_images'
 Check ($text.Contains('PRIVATE_INSTALLATION_OBSERVATION_EXCLUDE_FROM_LEDGER')) 'raw_command_records_private'
 Check ($text.Contains("'UNSEALED_INSTALLATION_DIAGNOSTICS_ONLY'") -and $text.Contains("'policy\profile.json'")) 'sealed_worker_refused'
 Check ($text.Contains("'deployment\Inspect-WorkerSetupProgress.ps1'") -and $text.Contains("'EXACT_STANDARD_HOST_LAUNCHER_REQUIRED'")) 'protected_exact_standard_host_entry'
 $fixture=Join-Path $evidence 'fixture.txt';$missing=Join-Path $evidence 'missing.txt'
 # These commands operate only on synthetic text in this new host evidence directory.
 $tailFixture=$commands[1].Replace('cls & ','').Replace('C:\$Windows.~BT\Sources\Panther\setupact.log',$fixture)
 foreach($count in @(14,7,6,3,0)){
  $lines=@(for($i=1;$i -le $count;$i++){'LINE_'+$i});[IO.File]::WriteAllLines($fixture,$lines,[Text.UTF8Encoding]::new($false))
  $actual=Run-CmdFixture $tailFixture;$wanted=@('SETUPACT_LAST_6_LINES')+@($lines|Select-Object -Last 6);$actualLines=@($actual.stdout -split '\r?\n'|Where-Object{$_ -ne ''}|ForEach-Object{$_.TrimEnd()})
  [IO.File]::WriteAllText((Join-Path $evidence ('native-tail-'+$count+'.json')),($actual|ConvertTo-Json -Compress),[Text.UTF8Encoding]::new($false))
  Check ($actual.exit -eq 0 -and $actual.stderr -eq '' -and ($actualLines -join '|') -ceq ($wanted -join '|')) ('native_cmd_tail_fixture_line_count_'+$count)
 }
 [IO.File]::WriteAllText($fixture,'abc',[Text.UTF8Encoding]::new($false))
 $inventoryFixture='for %F in ('+$fixture+' '+$missing+') do @if exist %F (echo FILE_PRESENT_BYTES %~zF %F) else @echo FILE_MISSING %F'
 $actual=Run-CmdFixture $inventoryFixture
 Check ($actual.exit -eq 0 -and $actual.stderr -eq '' -and $actual.stdout.Contains('FILE_PRESENT_BYTES 3 '+$fixture) -and $actual.stdout.Contains('FILE_MISSING '+$missing)) 'native_cmd_inventory_reports_present_size_and_missing_separately'
 [IO.File]::WriteAllText((Join-Path $evidence 'native-inventory.json'),($actual|ConvertTo-Json -Compress),[Text.UTF8Encoding]::new($false))
 $result=[ordered]@{schema_version=1;classification='TRUSTED_INFRASTRUCTURE_ONLY';infrastructure_checks_passed=$checks;failed=0;setup_entry_executed=$false;vm_operations=0;guest_input=0;candidate_execution=$false;native_cmd_inputs='SYNTHETIC_HOST_TEXT_FIXTURES_ONLY';source_sha256=(Get-FileHash -LiteralPath $path -Algorithm SHA256).Hash.ToLowerInvariant();test_sha256=(Get-FileHash -LiteralPath $PSCommandPath -Algorithm SHA256).Hash.ToLowerInvariant();checks=$observations;utc=[DateTime]::UtcNow.ToString('o')}
 [IO.File]::WriteAllText((Join-Path $evidence 'results.json'),($result|ConvertTo-Json -Depth 5),[Text.UTF8Encoding]::new($false));[pscustomobject]@{passed=$checks;failed=0;result_file=(Join-Path $evidence 'results.json')}|ConvertTo-Json -Compress
}catch{
 [IO.File]::WriteAllText((Join-Path $evidence 'failure.json'),([ordered]@{schema_version=1;checks_passed=$checks;failed=1;error=$_.Exception.Message;vm_operations=0;guest_input=0;utc=[DateTime]::UtcNow.ToString('o')}|ConvertTo-Json -Compress),[Text.UTF8Encoding]::new($false));throw
}
