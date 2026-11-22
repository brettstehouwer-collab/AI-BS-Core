# Trusted filesystem/process fixtures for the production lease/history statements.
# Does not run the entry guard, VM query/start, guest code, or worker adoption.
param([Parameter(Mandatory=$true)][string]$EvidenceRoot,[switch]$Contender)
$ErrorActionPreference='Stop'
$target=[IO.Path]::GetFullPath($EvidenceRoot)
if($target -notmatch '^C:\\AI-BS\\backups\\phase4_desktop_evidence_\d{8}T\d{6,}Z$'){throw 'FRESH_FIXED_FIXTURE_ROOT_REQUIRED'}
$entry=Join-Path $PSScriptRoot '..\Inspect-CurrentWorkerDesktop.ps1'
$tokens=$null;$errors=$null
$tree=[Management.Automation.Language.Parser]::ParseFile($entry,[ref]$tokens,[ref]$errors)
if($errors.Count){throw 'ENTRY_AST_PARSE_FAILED'}
$source=[IO.File]::ReadAllText($entry)
$begin=$source.IndexOf("    `$leasePath=Join-Path `$evidenceRoot 'inspection.lease'")
$end=$source.IndexOf("    `$out=Join-Path `$evidenceRoot ('inspection_'",$begin)
if($begin-lt 0-or $end-le $begin){throw 'EXACT_PRODUCTION_PROTOCOL_NOT_FOUND'}
$protocol=$source.Substring($begin,$end-$begin)
if($protocol -match 'Invoke-InspectionQuery|Start-Process|VBoxManage|Add-Type'){throw 'PROTOCOL_EXTRACT_HAS_NATIVE_OPERATION'}
$names=@('Assert-InspectionRegularPath','Read-InspectionHeldText','Get-InspectionHeldHash','Get-InspectionPolicyField','Assert-InspectionPolicyShape','Assert-InspectionPolicyNumber','Assert-InspectionPolicyString','Get-InspectionPolicyUtcTicks','Assert-InspectionPolicyFalseFlags','Assert-InspectionHistoryProfile','Assert-InspectionQueryResult','Assert-InspectionCompletedHistory')
foreach($name in $names){
    $found=@($tree.FindAll({param($node)$node-is [Management.Automation.Language.FunctionDefinitionAst]-and $node.Name-ceq $name},$true))
    if($found.Count-ne 1){throw 'EXACT_PROTOCOL_FUNCTION_REQUIRED'}
    . ([ScriptBlock]::Create($found[0].Extent.Text))
}
function Invoke-FixtureProtocol([string]$Directory){
    $evidenceRoot=$Directory;$workerSid='S-1-5-21-2133766663-4066672948-2456486318-1005'
    $expectedProfileSHA='A'*64;$expectedQuerySHA='B'*64;$expectedVBoxSHA='C'*64;$profiles=@()
    $lease=$null;$held=New-Object 'System.Collections.Generic.List[System.IDisposable]'
    try{. ([ScriptBlock]::Create($protocol))}
    finally{foreach($item in $held){$item.Dispose()};if($null-ne $lease){$lease.Dispose()}}
}
if($Contender){
    try{Invoke-FixtureProtocol (Join-Path $target 'lease_case');exit 20}
    catch{if($_.Exception.ToString()-match 'being used by another process|sharing violation'){Write-Output 'CONTENDER_REFUSED';exit 0};throw}
}
if(Test-Path -LiteralPath $target){throw 'FRESH_FIXTURE_DIRECTORY_REQUIRED'}
New-Item -ItemType Directory -Path $target -ErrorAction Stop|Out-Null
$passes=New-Object 'System.Collections.Generic.List[string]'
function Pass([string]$Name){$passes.Add($Name);Write-Output ('PASS '+$Name)}
function Reject-Preserved([string]$Name,[string]$Directory){
    $before=@{};foreach($f in Get-ChildItem -LiteralPath $Directory -Recurse -File){if($f.Name-ne 'inspection.lease'){$before[$f.FullName]=(Get-FileHash -LiteralPath $f.FullName -Algorithm SHA256).Hash}}
    $denied=$false;try{Invoke-FixtureProtocol $Directory}catch{$denied=$true}
    if(-not $denied){throw 'INCOMPLETE_HISTORY_WAS_ACCEPTED'}
    $after=@{};foreach($f in Get-ChildItem -LiteralPath $Directory -Recurse -File){if($f.Name-ne 'inspection.lease'){$after[$f.FullName]=(Get-FileHash -LiteralPath $f.FullName -Algorithm SHA256).Hash}}
    if($before.Count-ne $after.Count){throw 'HISTORY_FILE_SET_CHANGED'}
    foreach($key in $before.Keys){if($after[$key]-cne $before[$key]){throw 'HISTORY_BYTES_CHANGED'}}
    Pass $Name
}
$case=Join-Path $target 'lease_case';New-Item -ItemType Directory -Path $case|Out-Null
Invoke-FixtureProtocol $case;Pass 'empty history admitted as infrastructure only'
$leasePath=Join-Path $case 'inspection.lease'
$heldLease=New-Object IO.FileStream($leasePath,[IO.FileMode]::OpenOrCreate,[IO.FileAccess]::ReadWrite,[IO.FileShare]::None)
try{
    $process=New-Object Diagnostics.Process;$process.StartInfo=New-Object Diagnostics.ProcessStartInfo
    $process.StartInfo.FileName=(Get-Process -Id $PID).Path
    $process.StartInfo.Arguments='-NoProfile -NonInteractive -File "'+$PSCommandPath+'" -EvidenceRoot "'+$target+'" -Contender'
    $process.StartInfo.UseShellExecute=$false;$process.StartInfo.CreateNoWindow=$true;$process.StartInfo.RedirectStandardOutput=$true;$process.StartInfo.RedirectStandardError=$true
    if(-not $process.Start()){throw 'CONTENDER_NOT_STARTED'}
    if(-not $process.WaitForExit(10000)){try{$process.Kill()}catch{};throw 'CONTENDER_DEADLINE'}
    $stdout=$process.StandardOutput.ReadToEnd();$stderr=$process.StandardError.ReadToEnd()
    if($process.ExitCode-ne 0-or $stdout-notmatch 'CONTENDER_REFUSED'-or $stderr.Length-ne 0){throw 'CROSS_PROCESS_LEASE_NOT_REFUSED'}
    $process.Dispose();Pass 'real second-process lease contention refused'
}finally{$heldLease.Dispose()}
Invoke-FixtureProtocol $case;Pass 'lease reacquired after confirmed owner release'
$case=Join-Path $target 'intent_only';$partial=Join-Path $case 'inspection_partial';New-Item -ItemType Directory -Path $partial|Out-Null
[IO.File]::WriteAllText((Join-Path $partial 'intent.json'),'SYNTHETIC interrupted intent; retain exactly')
Reject-Preserved 'interrupted intent refused with all evidence retained' $case
$case=Join-Path $target 'pending_marker';$partial=Join-Path $case 'inspection_pending';New-Item -ItemType Directory -Path $partial|Out-Null
foreach($name in @('intent.json','final.json','completion.pending.json','query-1-intent.json','query-1-result.json','query-2-intent.json','query-2-result.json','query-3-intent.json','query-3-result.json')){[IO.File]::WriteAllText((Join-Path $partial $name),'{}')}
Reject-Preserved 'uncommitted completion refused without replay or promotion' $case
$case=Join-Path $target 'invalid_json';$partial=Join-Path $case 'inspection_corrupt';New-Item -ItemType Directory -Path $partial|Out-Null
foreach($name in @('intent.json','final.json','completion.json','query-1-intent.json','query-1-result.json','query-2-intent.json','query-2-result.json','query-3-intent.json','query-3-result.json')){[IO.File]::WriteAllText((Join-Path $partial $name),'{')}
Reject-Preserved 'complete filenames cannot admit malformed retained JSON' $case
$result=[ordered]@{Mode='TRUSTED_PRODUCTION_PROTOCOL_FILESYSTEM_FIXTURES';Passed=$passes.Count;Cases=$passes.ToArray();EntrySourceSHA256=(Get-FileHash -LiteralPath $entry -Algorithm SHA256).Hash;TaskAuthority=$false;ProviderAccepted=$false;ActualContainmentCasesRun=0;RealWorkerAdmission=$false}
$result|ConvertTo-Json -Depth 4|Set-Content -LiteralPath (Join-Path $target 'result.json') -Encoding UTF8
Write-Output ('RESULT passed='+$passes.Count+'; filesystem/process infrastructure only; no worker or guest admission.')
