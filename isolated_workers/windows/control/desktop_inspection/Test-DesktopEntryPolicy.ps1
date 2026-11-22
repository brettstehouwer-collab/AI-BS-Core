param([Parameter(Mandatory=$true)][string]$EvidenceRoot,[switch]$ExpectedRed)
$ErrorActionPreference='Stop'
$target=[IO.Path]::GetFullPath($EvidenceRoot)
if($target -notmatch '^C:\\AI-BS\\backups\\phase4_desktop_entry_policy_\d{8}T\d{6,}Z$' -or (Test-Path -LiteralPath $target)){throw 'Fresh timestamped pure-policy evidence directory required.'}
New-Item -ItemType Directory -Path $target -ErrorAction Stop|Out-Null
$entry=Join-Path $PSScriptRoot '..\Inspect-CurrentWorkerDesktop.ps1'
$tokens=$null;$parseErrors=$null
$tree=[Management.Automation.Language.Parser]::ParseFile($entry,[ref]$tokens,[ref]$parseErrors)
if($parseErrors.Count){throw 'Entry AST did not parse.'}
# Synthetic infrastructure only: define ONLY these named pure policy functions.
# The entry itself, its guard, imports, evidence writer and native-query route never run here.
$names=@('Assert-InspectionMediumCsv','Assert-InspectionCompletedHistory','Get-InspectionPolicyField','Assert-InspectionPolicyShape','Assert-InspectionPolicyNumber','Assert-InspectionPolicyString','Get-InspectionPolicyUtcTicks','Assert-InspectionPolicyFalseFlags','Assert-InspectionHistoryProfile','Assert-InspectionQueryResult')
foreach($name in $names){
    $found=@($tree.FindAll({param($node)$node -is [Management.Automation.Language.FunctionDefinitionAst] -and $node.Name -ceq $name},$true))
    if($found.Count -gt 1){throw 'Ambiguous pure policy definition.'}
    if($found.Count -eq 1){. ([ScriptBlock]::Create($found[0].Extent.Text))}
    elseif($name -in @('Assert-InspectionMediumCsv','Assert-InspectionCompletedHistory')){throw 'Required pure policy function missing.'}
}
$script:failed=0;$script:passed=0;$script:lines=New-Object 'System.Collections.Generic.List[string]'
function Test-Reject([string]$Name,[scriptblock]$Action){
    $rejected=$false;try{$null=& $Action}catch{$rejected=$true}
    if($rejected){$script:passed++;$line='PASS '+$Name}else{$script:failed++;$line='FAIL '+$Name}
    $script:lines.Add($line);Write-Output $line
}
function Test-Accept([string]$Name,[scriptblock]$Action){
    $accepted=$true;try{$null=& $Action}catch{$accepted=$false;Write-Output ('Fixture rejection code: '+$_.Exception.Message)}
    if($accepted){$script:passed++;$line='PASS '+$Name}else{$script:failed++;$line='FAIL '+$Name};$script:lines.Add($line);Write-Output $line
}
function Write-SyntheticPolicyJson([string]$Path,$Value){
    $bytes=(New-Object Text.UTF8Encoding($false)).GetBytes(($Value|ConvertTo-Json -Depth 20 -Compress))
    $file=New-Object IO.FileStream($Path,[IO.FileMode]::CreateNew,[IO.FileAccess]::Write,[IO.FileShare]::None)
    try{$file.Write($bytes,0,$bytes.Length);$file.Flush($true)}finally{$file.Dispose()}
    return (Get-FileHash -LiteralPath $Path -Algorithm SHA256).Hash
}
function Read-SyntheticPolicyJson([string]$Path){return ([IO.File]::ReadAllText($Path)|ConvertFrom-Json -ErrorAction Stop)}
function Copy-SyntheticPolicyBundle($Value){return ($Value|ConvertTo-Json -Depth 30 -Compress|ConvertFrom-Json -ErrorAction Stop)}
function New-SyntheticPolicyBundle {
    $attempt='11111111-2222-3333-4444-555555555555'
    $binding=[ordered]@{UUID='22222222-3333-4444-5555-666666666666';Path='C:\AI-BS\backups\phase4_wheel_setup_media_20261024T2003424861639Z\AI-BS_Wheels_v1.iso';Length=7153664;SHA256='B6B5703DC0A262E0D8E2A85D7221EA3F830EB45DE38166997FEBFC510A37A5B3'}
    $context=[pscustomobject]@{WorkerSID='S-1-5-21-2133766663-4066672948-2456486318-1005';VMUUID='6c5a53da-ab80-4ecb-8be6-4059266f736e';ProfileSourceSHA256='C1C756CAAE087436E0E7755D9DA628E13A11536E73BB75707C6FCF4FC3611E8D';QuerySourceSHA256='C003EC332AA4A5736008AED1D8B0AB9D013A2BB2D13B5BF4B15F2D097140BD7E';VBoxSHA256='178E016ED38CB6E369A5C17C6C960C176674B9C864030D8CE0AD2867613BECFF';MediaProfiles=@([pscustomobject]@{Path=$binding.Path;Length=$binding.Length;SHA256=$binding.SHA256})}
    $intent=[ordered]@{Schema=2;State='INSPECTING';TaskAuthority=$false;ProviderAccepted=$false;RuntimeVerified=$false;LicensingVerified=$false;GuestStarted=$false;ConfigurationChangeRequested=$false;MutationRequested=$false;RawOutputsLocalOnly=$true;Commands=@();WorkerSID=$context.WorkerSID;ControllerPID=4242;ControllerCreationUTC='2026-10-24T20:00:00.0000000Z';StartedUTC='2026-10-24T20:00:01.0000000Z';VMUUID=$context.VMUUID;ProfileSourceSHA256=$context.ProfileSourceSHA256;QuerySourceSHA256=$context.QuerySourceSHA256;VBoxSHA256=$context.VBoxSHA256;ConfigSHA256=('A'*64);OpticalBinding=$binding;AttemptID=$attempt}
    $fixture=Join-Path $target 'synthetic_completed_history';New-Item -ItemType Directory -Path $fixture -ErrorAction Stop|Out-Null
    $intentSHA=Write-SyntheticPolicyJson (Join-Path $fixture 'intent.json') $intent
    $queries=@();$commands=@()
    foreach($number in 1..3){
        $operation=@('VMInfo','DiskInfo','VMInfo')[$number-1]
        $queryIntent=[ordered]@{Schema=2;AttemptID=$attempt;Sequence=$number;Operation=$operation;AttemptIntentSHA256=$intentSHA;State='INTENT_NO_REPLAY';UTC=('2026-10-24T20:00:0'+($number+1)+'.0000000Z')}
        $qi=Join-Path $fixture ('query-'+$number+'-intent.json');$qiSHA=Write-SyntheticPolicyJson $qi $queryIntent
        $stdout='Synthetic metadata '+$operation+' '+$number
        $native=[ordered]@{State='EXITED';Reason='';ExitCode=0;ExitCodeKnown=$true;PID=(5000+$number);CreationUtc=('2026-10-24T20:00:0'+($number+1)+'.1000000Z');Stdout=$stdout;Stderr='';TimedOut=$false;OutputCapped=$false;ElapsedMilliseconds=23;OutputBytes=[Text.Encoding]::UTF8.GetByteCount($stdout);ErrorBytes=0;CombinedLimitBytes=1048576;StderrLimitBytes=65536;Operation=$operation;Cancelled=$false;ClientKillRequested=$false;DescendantTerminationEstablished=$false;StderrLimitReached=$false;CombinedLimitReached=$false}
        $result=[ordered]@{Schema=2;AttemptID=$attempt;Sequence=$number;Operation=$operation;AttemptIntentSHA256=$intentSHA;QueryIntentSHA256=$qiSHA;Result=$native}
        $qr=Join-Path $fixture ('query-'+$number+'-result.json');$qrSHA=Write-SyntheticPolicyJson $qr $result
        $queries+=@{Intent=(Read-SyntheticPolicyJson $qi);IntentSHA256=$qiSHA;Result=(Read-SyntheticPolicyJson $qr);ResultSHA256=$qrSHA}
        $commands+=@{AttemptID=$attempt;Sequence=$number;Operation=$operation;QueryIntentSHA256=$qiSHA;QueryResultSHA256=$qrSHA;State=$native.State;ExitCode=$native.ExitCode;ExitCodeKnown=$native.ExitCodeKnown;PID=$native.PID;CreationUtc=$native.CreationUtc;TimedOut=$false;OutputCapped=$false;Cancelled=$false;OutputBytes=$native.OutputBytes;ErrorBytes=0;ElapsedMilliseconds=$native.ElapsedMilliseconds}
    }
    $profile=[ordered]@{ProfileMatched=$true;TaskAuthority=$false;ProviderAccepted=$false;RuntimeVerified=$false;LicensingVerified=$false;Scope='CURRENT_DESKTOP_METADATA_ONLY';ExpectedState='poweroff';VMUUID=$context.VMUUID;SnapshotUUID='5f014291-52f1-4b18-83c9-37110083b3a0';DiskUUID='9e1efe57-9da5-49f8-acea-763429616968';OpticalUUID=$binding.UUID;OpticalPath=$binding.Path;OpticalSHA256=$binding.SHA256}
    $final=[ordered]@{};foreach($key in $intent.Keys){$final[$key]=$intent[$key]};$final.State='INSPECTED_PREREQUISITES_PENDING';$final.Commands=$commands
    $final['FinishedUTC']='2026-10-24T20:00:05.0000000Z';$final['Profile']=$profile;$final['XmlProfile']=$profile;$final['AttemptIntentSHA256']=$intentSHA
    $finalSHA=Write-SyntheticPolicyJson (Join-Path $fixture 'final.json') $final
    $completion=[ordered]@{Schema=2;State='COMPLETED_READ_ONLY_PREREQUISITES_PENDING';AttemptID=$attempt;FinalSHA256=$finalSHA;AttemptIntentSHA256=$intentSHA;CompletedUTC='2026-10-24T20:00:06.0000000Z';TaskAuthority=$false;RawOutputsLocalOnly=$true}
    $null=Write-SyntheticPolicyJson (Join-Path $fixture 'completion.pending.json') $completion
    [IO.File]::Move((Join-Path $fixture 'completion.pending.json'),(Join-Path $fixture 'completion.json'))
    return @{Context=$context;Bundle=@{Intent=(Read-SyntheticPolicyJson (Join-Path $fixture 'intent.json'));IntentSHA256=$intentSHA;Final=(Read-SyntheticPolicyJson (Join-Path $fixture 'final.json'));FinalSHA256=$finalSHA;Completion=(Read-SyntheticPolicyJson (Join-Path $fixture 'completion.json'));Queries=$queries}}
}
Test-Reject 'display-name medium SID decoy with actual high SID rejected' {Assert-InspectionMediumCsv @('"Display S-1-16-8192 decoy","Label","S-1-16-12288","Mandatory group, Enabled"')}
Test-Reject 'minimal completed-state final without intent and query history rejected' {Assert-InspectionCompletedHistory @{Final=[pscustomobject]@{State='INSPECTED_PREREQUISITES_PENDING';TaskAuthority=$false}} $null}
if(-not $ExpectedRed){
    Test-Accept 'one exact mandatory medium SID accepted' {Assert-InspectionMediumCsv @('"Group, with ""quotes""","Alias","S-1-5-32-545","Enabled"','"Localized label name","Label","S-1-16-8192","Mandatory group, Enabled"')}
    foreach($rid in @('4096','12288','16384','81920')){Test-Reject ('other mandatory label RID '+$rid+' rejected') {Assert-InspectionMediumCsv @('"S-1-16-8192 display decoy","Label","S-1-16-'+$rid+'","Enabled"')}}
    Test-Reject 'duplicate medium rows rejected' {Assert-InspectionMediumCsv @('"Medium","Label","S-1-16-8192","Enabled"','"Duplicate","Label","S-1-16-8192","Enabled"')}
    Test-Reject 'medium plus high label rejected' {Assert-InspectionMediumCsv @('"Medium","Label","S-1-16-8192","Enabled"','"High","Label","S-1-16-12288","Enabled"')}
    Test-Reject 'extra CSV column rejected' {Assert-InspectionMediumCsv @('"Medium","Label","S-1-16-8192","Enabled","extra"')}
    Test-Reject 'unquoted CSV row rejected' {Assert-InspectionMediumCsv @('Medium,Label,S-1-16-8192,Enabled')}
    Test-Reject 'missing mandatory SID rejected' {Assert-InspectionMediumCsv @('"S-1-16-8192 display","Alias","S-1-5-32-545","Enabled"')}
    $fixture=New-SyntheticPolicyBundle;$context=$fixture.Context;$baseline=$fixture.Bundle
    Test-Accept 'fully bound committed completed history survives actual JSON roundtrip' {Assert-InspectionCompletedHistory $baseline $context}
    foreach($flag in @('TaskAuthority','ProviderAccepted','RuntimeVerified','LicensingVerified','GuestStarted','ConfigurationChangeRequested','MutationRequested')){
        $bad=Copy-SyntheticPolicyBundle $baseline;$bad.Final.$flag=$true;Test-Reject ('true final flag '+$flag+' rejected') {Assert-InspectionCompletedHistory $bad $context}
    }
    $bad=Copy-SyntheticPolicyBundle $baseline;$bad.Final.TaskAuthority='false';Test-Reject 'string false authority rejected' {Assert-InspectionCompletedHistory $bad $context}
    $bad=Copy-SyntheticPolicyBundle $baseline;$bad.Intent.Schema=1;Test-Reject 'legacy intent schema rejected' {Assert-InspectionCompletedHistory $bad $context}
    $bad=Copy-SyntheticPolicyBundle $baseline;$bad.Final.Schema='2';Test-Reject 'string schema rejected' {Assert-InspectionCompletedHistory $bad $context}
    foreach($name in @('WorkerSID','ProfileSourceSHA256','QuerySourceSHA256','VBoxSHA256')){$bad=Copy-SyntheticPolicyBundle $baseline;$bad.Final.$name='WRONG';Test-Reject ('wrong final '+$name+' rejected') {Assert-InspectionCompletedHistory $bad $context}}
    $bad=Copy-SyntheticPolicyBundle $baseline;$bad.Final.ControllerPID=4243;Test-Reject 'different controller identity rejected' {Assert-InspectionCompletedHistory $bad $context}
    $bad=Copy-SyntheticPolicyBundle $baseline;$bad.Final.AttemptID='aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee';Test-Reject 'different final attempt rejected' {Assert-InspectionCompletedHistory $bad $context}
    $bad=Copy-SyntheticPolicyBundle $baseline;$bad.Final.ConfigSHA256='B'*64;Test-Reject 'different final config hash rejected' {Assert-InspectionCompletedHistory $bad $context}
    $bad=Copy-SyntheticPolicyBundle $baseline;$bad.Final.RawOutputsLocalOnly=$false;Test-Reject 'raw output publication permission rejected' {Assert-InspectionCompletedHistory $bad $context}
    $bad=Copy-SyntheticPolicyBundle $baseline;$bad.Final.XmlProfile.RuntimeVerified=$true;Test-Reject 'profile runtime admission rejected' {Assert-InspectionCompletedHistory $bad $context}
    $bad=Copy-SyntheticPolicyBundle $baseline;$bad.Final.XmlProfile.ExpectedState='running';Test-Reject 'different profile and XML states rejected' {Assert-InspectionCompletedHistory $bad $context}
    $bad=Copy-SyntheticPolicyBundle $baseline;$bad.Queries=@($bad.Queries[0],$bad.Queries[1]);Test-Reject 'missing third query rejected' {Assert-InspectionCompletedHistory $bad $context}
    $bad=Copy-SyntheticPolicyBundle $baseline;$bad.Queries[1].Intent.Sequence=1;Test-Reject 'wrong query sequence rejected' {Assert-InspectionCompletedHistory $bad $context}
    $bad=Copy-SyntheticPolicyBundle $baseline;$bad.Queries[1].Result.Operation='VMInfo';Test-Reject 'wrong middle operation rejected' {Assert-InspectionCompletedHistory $bad $context}
    $bad=Copy-SyntheticPolicyBundle $baseline;$bad.Queries[2].Result.AttemptID='aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee';Test-Reject 'query from another attempt rejected' {Assert-InspectionCompletedHistory $bad $context}
    $bad=Copy-SyntheticPolicyBundle $baseline;$bad.Queries[0].Result.AttemptIntentSHA256='B'*64;Test-Reject 'query wrong durable initial intent hash rejected' {Assert-InspectionCompletedHistory $bad $context}
    $bad=Copy-SyntheticPolicyBundle $baseline;$bad.Queries[0].Result.QueryIntentSHA256='B'*64;Test-Reject 'result wrong durable query intent hash rejected' {Assert-InspectionCompletedHistory $bad $context}
    $bad=Copy-SyntheticPolicyBundle $baseline;$bad.Final.Commands[1].QueryResultSHA256='B'*64;Test-Reject 'final wrong durable result hash rejected' {Assert-InspectionCompletedHistory $bad $context}
    foreach($field in @('TimedOut','OutputCapped','Cancelled','ClientKillRequested','StderrLimitReached','CombinedLimitReached','DescendantTerminationEstablished')){$bad=Copy-SyntheticPolicyBundle $baseline;$bad.Queries[0].Result.Result.$field=$true;Test-Reject ('native uncertainty or authority '+$field+' rejected') {Assert-InspectionCompletedHistory $bad $context}}
    $bad=Copy-SyntheticPolicyBundle $baseline;$bad.Queries[0].Result.Result.ExitCode=7;Test-Reject 'native nonzero rejected' {Assert-InspectionCompletedHistory $bad $context}
    $bad=Copy-SyntheticPolicyBundle $baseline;$bad.Queries[0].Result.Result.ExitCode='0';Test-Reject 'native string zero rejected' {Assert-InspectionCompletedHistory $bad $context}
    $bad=Copy-SyntheticPolicyBundle $baseline;$bad.Queries[0].Result.Result.ExitCodeKnown=$false;Test-Reject 'native unknown exit rejected' {Assert-InspectionCompletedHistory $bad $context}
    $bad=Copy-SyntheticPolicyBundle $baseline;$bad.Final.Commands[0].PID=9999;Test-Reject 'summary differs from actual native receipt rejected' {Assert-InspectionCompletedHistory $bad $context}
    $bad=Copy-SyntheticPolicyBundle $baseline;$bad.Final.State=@('INSPECTED_PREREQUISITES_PENDING');Test-Reject 'array state malformed schema rejected' {Assert-InspectionCompletedHistory $bad $context}
    $bad=Copy-SyntheticPolicyBundle $baseline;$bad.PSObject.Properties.Remove('Completion');Test-Reject 'final without committed completion marker rejected' {Assert-InspectionCompletedHistory $bad $context}
    $bad=Copy-SyntheticPolicyBundle $baseline;$bad.Completion.State='PENDING';Test-Reject 'pending completion not committed rejected' {Assert-InspectionCompletedHistory $bad $context}
    $bad=Copy-SyntheticPolicyBundle $baseline;$bad.Completion.FinalSHA256='B'*64;Test-Reject 'completion wrong actual final hash rejected' {Assert-InspectionCompletedHistory $bad $context}
    $bad=Copy-SyntheticPolicyBundle $baseline;$bad.Final.Commands[0].ExitCodeKnown='true';Test-Reject 'summary string known-exit boolean rejected' {Assert-InspectionCompletedHistory $bad $context}
}
$summary='RESULT passed='+$script:passed+' failed='+$script:failed+'; synthetic AST-extracted pure-policy fixtures only; no entry/native/guest operation.'
$script:lines.Add($summary);Write-Output $summary
$utf8=New-Object Text.UTF8Encoding($false)
[IO.File]::WriteAllText((Join-Path $target 'policy_tests.txt'),(($script:lines.ToArray()) -join [Environment]::NewLine),$utf8)
Copy-Item -LiteralPath $entry -Destination (Join-Path $target 'Inspect-CurrentWorkerDesktop.fixture-source.ps1') -ErrorAction Stop
if($ExpectedRed){if($script:failed -ne 2){throw 'Expected exactly two behavioral RED failures.'};Write-Output ('VERIFIED behavioral RED '+$target);exit 0}
if($script:failed){throw 'Pure policy fixtures failed.'}
Write-Output ('Evidence '+$target)
