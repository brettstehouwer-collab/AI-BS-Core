# Reviewed v2 read-only inspector. Exact v1 failure retained; no VM start/adoption.
# Snapshot metadata distinction reviewed in Record107; all other gates retained.
[CmdletBinding()]
param()
$ErrorActionPreference='Stop'
$workerSid='S-1-5-21-2133766663-4066672948-2456486318-1005'
$identity=[Security.Principal.WindowsIdentity]::GetCurrent()
$principal=New-Object Security.Principal.WindowsPrincipal($identity)
if($identity.User.Value -ne $workerSid -or $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)){
    Write-Host 'REFUSED: existing standard aibs_vm_worker account required; no VM query or evidence write.'
    exit 2
}
if(-not [Environment]::Is64BitProcess){Write-Host 'REFUSED: x64 worker process required.';exit 2}

$root='C:\AI-BS\isolated_workers\windows'
$registry=Join-Path $root 'runtime\base_preparation_v2\vbox_config'
$vmRoot=Join-Path $root 'runtime\base_preparation_v2\vms\AI-BS-Eval-Base-20261023'
$config=Join-Path $vmRoot 'AI-BS-Eval-Base-20261023.vbox'
$vbox='C:\Program Files\Oracle\VirtualBox\VBoxManage.exe'
$evidenceRoot=Join-Path $root 'runtime\desktop_inspection_v2'
$profilePath=Join-Path $PSScriptRoot 'desktop_inspection_v2\DesktopProfile.ps1'
$queryPath=Join-Path $PSScriptRoot 'desktop_inspection\DesktopQuery.cs'
$expectedProfileSHA='AB194E76ECEEA4B2C914DE1AC704559DEF1C66A82646983902EE56DFC92C6803'
$expectedQuerySHA='C003EC332AA4A5736008AED1D8B0AB9D013A2BB2D13B5BF4B15F2D097140BD7E'
$expectedVBoxSHA='178E016ED38CB6E369A5C17C6C960C176674B9C864030D8CE0AD2867613BECFF'
$lease=$null;$out=$null;$held=New-Object 'System.Collections.Generic.List[System.IDisposable]'
$clock=[Diagnostics.Stopwatch]::StartNew()
$report=[ordered]@{Schema=2;State='REFUSED';TaskAuthority=$false;ProviderAccepted=$false;RuntimeVerified=$false;LicensingVerified=$false;GuestStarted=$false;ConfigurationChangeRequested=$false;MutationRequested=$false;RawOutputsLocalOnly=$true;Commands=@()}

function Assert-InspectionRegularPath([string]$Path){
    $node=Get-Item -LiteralPath $Path -Force -ErrorAction Stop
    while($null -ne $node){
        if($node.Attributes -band [IO.FileAttributes]::ReparsePoint){throw 'LINKED_PATH_REFUSED'}
        if($node -is [IO.FileInfo]){$node=$node.Directory}else{$node=$node.Parent}
    }
}
function Read-InspectionHeldText([string]$Path,[long]$Limit){
    Assert-InspectionRegularPath $Path
    $file=New-Object IO.FileStream($Path,[IO.FileMode]::Open,[IO.FileAccess]::Read,[IO.FileShare]::Read)
    $held.Add($file)
    if($file.Length -lt 1 -or $file.Length -gt $Limit){throw 'BOUNDED_FILE_LENGTH_REQUIRED'}
    Assert-InspectionRegularPath $Path
    $reader=New-Object IO.StreamReader($file,(New-Object Text.UTF8Encoding($false,$true)),$true,4096,$true)
    try{$text=$reader.ReadToEnd()}finally{$reader.Dispose();$file.Position=0}
    return $text
}
function Get-InspectionHeldHash([IO.Stream]$Stream){
    $sha=[Security.Cryptography.SHA256]::Create()
    try{$Stream.Position=0;$hash=[BitConverter]::ToString($sha.ComputeHash($Stream)).Replace('-','');$Stream.Position=0;return $hash}finally{$sha.Dispose()}
}
function Write-InspectionJson([string]$Path,$Value,[int]$Limit=8388608){
    $bytes=(New-Object Text.UTF8Encoding($false)).GetBytes(($Value|ConvertTo-Json -Depth 12 -Compress))
    if($bytes.Length -gt $Limit){throw 'EVIDENCE_SERIALIZATION_LIMIT'}
    Assert-InspectionRegularPath ([IO.Path]::GetDirectoryName($Path))
    $file=New-Object IO.FileStream($Path,[IO.FileMode]::CreateNew,[IO.FileAccess]::Write,[IO.FileShare]::None)
    try{$file.Write($bytes,0,$bytes.Length);$file.Flush($true)}finally{$file.Dispose()}
}
function Get-InspectionCanonicalPath([string]$Path){
    if([string]::IsNullOrWhiteSpace($Path) -or $Path.StartsWith('\\')){throw 'LOCAL_PATH_REQUIRED'}
    return [IO.Path]::GetFullPath($Path.Replace('\\','\').Replace('/','\'))
}
function Assert-InspectionMediumCsv([string[]]$Lines){
    if($null -eq $Lines -or $Lines.Count -lt 1 -or $Lines.Count -gt 4096 -or [Text.Encoding]::UTF8.GetByteCount(($Lines -join "`n")) -gt 1048576){throw 'INTEGRITY_CSV_BOUND'}
    foreach($line in $Lines){
        if($line.Length -gt 16384 -or $line -match '[\x00-\x1f\x7f]' -or $line -cnotmatch '^"(?:[^"]|"")*","(?:[^"]|"")*","(?:[^"]|"")*","(?:[^"]|"")*"$'){throw 'INTEGRITY_CSV_FOUR_FIELDS_REQUIRED'}
    }
    $rows=@($Lines|ConvertFrom-Csv -Header Name,Type,SID,Attributes -ErrorAction Stop -WarningAction Stop)
    foreach($row in $rows){if($row.SID -isnot [string] -or $row.SID -cnotmatch '^S-1-[0-9]+(?:-[0-9]+)+$'){throw 'INTEGRITY_CSV_SID_REQUIRED'}}
    $labels=@($rows|Where-Object {$_.SID -cmatch '^S-1-16-[0-9]+$'})
    if($labels.Count -ne 1 -or $labels[0].SID -cne 'S-1-16-8192'){throw 'ONE_EXACT_MEDIUM_INTEGRITY_SID_REQUIRED'}
    return $true
}
function Get-InspectionPolicyField($Value,[string]$Name){
    if($null -eq $Value){throw 'PRIOR_HISTORY_OBJECT_REQUIRED'}
    if($Value -is [Collections.IDictionary]){foreach($key in $Value.Keys){if($key -ceq $Name){return ,$Value[$key]}}}
    elseif($Value -is [pscustomobject]){foreach($property in $Value.PSObject.Properties){if($property.Name -ceq $Name){return ,$property.Value}}}
    throw 'PRIOR_HISTORY_FIELD_REQUIRED'
}
function Assert-InspectionPolicyShape($Value,[string[]]$Required){
    if($Value -is [Collections.IDictionary]){$names=@($Value.Keys)}elseif($Value -is [pscustomobject]){$names=@($Value.PSObject.Properties.Name)}else{throw 'PRIOR_HISTORY_OBJECT_REQUIRED'}
    if($names.Count -ne $Required.Count){throw 'PRIOR_HISTORY_FIELDS'}
    foreach($name in $Required){if($names -cnotcontains $name){throw 'PRIOR_HISTORY_FIELDS'}}
}
function Assert-InspectionPolicyNumber($Value,[long]$Minimum,[long]$Maximum){
    if(($Value -isnot [int] -and $Value -isnot [long]) -or $Value -lt $Minimum -or $Value -gt $Maximum){throw 'PRIOR_HISTORY_TYPED_NUMBER_REQUIRED'}
}
function Assert-InspectionPolicyString($Value,[int]$Minimum=1,[int]$Maximum=2048){
    if($Value -isnot [string] -or $Value.Length -lt $Minimum -or $Value.Length -gt $Maximum){throw 'PRIOR_HISTORY_TYPED_STRING_REQUIRED'}
}
function Get-InspectionPolicyUtcTicks($Value){
    if($Value -is [DateTime]){if($Value.Kind -ne [DateTimeKind]::Utc){throw 'PRIOR_HISTORY_UTC_REQUIRED'};return [long]$Value.Ticks}
    if($Value -is [DateTimeOffset]){if($Value.Offset -ne [TimeSpan]::Zero){throw 'PRIOR_HISTORY_UTC_REQUIRED'};return [long]$Value.UtcDateTime.Ticks}
    if($Value -isnot [string] -or $Value -cnotmatch '^\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d\.\d{7}Z$'){throw 'PRIOR_HISTORY_UTC_REQUIRED'}
    $date=[DateTime]::MinValue
    if(-not [DateTime]::TryParseExact($Value,'o',[Globalization.CultureInfo]::InvariantCulture,[Globalization.DateTimeStyles]::RoundtripKind,[ref]$date) -or $date.Kind -ne [DateTimeKind]::Utc){throw 'PRIOR_HISTORY_UTC_REQUIRED'}
    return [long]$date.Ticks
}
function Assert-InspectionPolicyFalseFlags($Value,[string[]]$Names){
    foreach($name in $Names){$flag=Get-InspectionPolicyField $Value $name;if($flag -isnot [bool] -or $flag){throw 'PRIOR_HISTORY_FALSE_FLAGS_REQUIRED'}}
}
function Assert-InspectionHistoryProfile($Value,$Binding,$Context){
    Assert-InspectionPolicyShape $Value @('ProfileMatched','TaskAuthority','ProviderAccepted','RuntimeVerified','LicensingVerified','Scope','ExpectedState','VMUUID','SnapshotUUID','DiskUUID','OpticalUUID','OpticalPath','OpticalSHA256')
    Assert-InspectionPolicyFalseFlags $Value @('TaskAuthority','ProviderAccepted','RuntimeVerified','LicensingVerified')
    foreach($name in @('Scope','ExpectedState','VMUUID','SnapshotUUID','DiskUUID','OpticalUUID','OpticalPath','OpticalSHA256')){Assert-InspectionPolicyString (Get-InspectionPolicyField $Value $name)}
    if($Value.ProfileMatched -isnot [bool] -or -not $Value.ProfileMatched -or $Value.Scope -cne 'CURRENT_DESKTOP_METADATA_ONLY' -or $Value.ExpectedState -cnotin @('running','saved','poweroff') -or $Value.VMUUID -cne $Context.VMUUID -or $Value.SnapshotUUID -cne '5f014291-52f1-4b18-83c9-37110083b3a0' -or $Value.DiskUUID -cne '9e1efe57-9da5-49f8-acea-763429616968' -or $Value.OpticalUUID -cne $Binding.UUID -or $Value.OpticalPath -cne $Binding.Path -or $Value.OpticalSHA256 -cne $Binding.SHA256){throw 'PRIOR_HISTORY_PROFILE_MISMATCH'}
}
function Assert-InspectionQueryResult($Value,[string]$Operation,[long]$Started,[long]$Finished){
    Assert-InspectionPolicyShape $Value @('State','Reason','ExitCode','ExitCodeKnown','PID','CreationUtc','Stdout','Stderr','TimedOut','OutputCapped','ElapsedMilliseconds','OutputBytes','ErrorBytes','CombinedLimitBytes','StderrLimitBytes','Operation','Cancelled','ClientKillRequested','DescendantTerminationEstablished','StderrLimitReached','CombinedLimitReached')
    Assert-InspectionPolicyFalseFlags $Value @('TimedOut','OutputCapped','Cancelled','ClientKillRequested','DescendantTerminationEstablished','StderrLimitReached','CombinedLimitReached')
    Assert-InspectionPolicyString $Value.State;Assert-InspectionPolicyString $Value.Operation
    Assert-InspectionPolicyNumber $Value.ExitCode 0 0;Assert-InspectionPolicyNumber $Value.PID 1 2147483647
    Assert-InspectionPolicyNumber $Value.OutputBytes 1 1048576;Assert-InspectionPolicyNumber $Value.ErrorBytes 0 0;Assert-InspectionPolicyNumber $Value.ElapsedMilliseconds 0 90000
    Assert-InspectionPolicyNumber $Value.CombinedLimitBytes 1048576 1048576;Assert-InspectionPolicyNumber $Value.StderrLimitBytes 65536 65536
    $created=Get-InspectionPolicyUtcTicks $Value.CreationUtc
    if($Value.State -cne 'EXITED' -or $Value.Reason -isnot [string] -or $Value.Reason.Length -ne 0 -or $Value.ExitCodeKnown -isnot [bool] -or -not $Value.ExitCodeKnown -or $Value.Operation -cne $Operation -or $Value.Stdout -isnot [string] -or $Value.Stdout.Length -eq 0 -or $Value.Stderr -isnot [string] -or $Value.Stderr.Length -ne 0 -or [Text.Encoding]::UTF8.GetByteCount($Value.Stdout) -ne $Value.OutputBytes -or $created -lt $Started -or $created -gt $Finished){throw 'PRIOR_HISTORY_NATIVE_RESULT_MISMATCH'}
}
function Assert-InspectionCompletedHistory($Bundle,$ExpectedContext){
    Assert-InspectionPolicyShape $Bundle @('Intent','IntentSHA256','Final','FinalSHA256','Completion','Queries')
    $intent=$Bundle.Intent;$final=$Bundle.Final
    $common=@('Schema','State','TaskAuthority','ProviderAccepted','RuntimeVerified','LicensingVerified','GuestStarted','ConfigurationChangeRequested','MutationRequested','RawOutputsLocalOnly','Commands','WorkerSID','ControllerPID','ControllerCreationUTC','StartedUTC','VMUUID','ProfileSourceSHA256','QuerySourceSHA256','VBoxSHA256','ConfigSHA256','OpticalBinding','AttemptID')
    Assert-InspectionPolicyShape $intent $common
    Assert-InspectionPolicyShape $final ($common+@('FinishedUTC','Profile','XmlProfile','AttemptIntentSHA256'))
    foreach($value in @($intent,$final)){
        Assert-InspectionPolicyNumber $value.Schema 2 2
        Assert-InspectionPolicyFalseFlags $value @('TaskAuthority','ProviderAccepted','RuntimeVerified','LicensingVerified','GuestStarted','ConfigurationChangeRequested','MutationRequested')
        Assert-InspectionPolicyNumber $value.ControllerPID 1 2147483647
        Assert-InspectionPolicyString $value.State
        if($value.RawOutputsLocalOnly -isnot [bool] -or -not $value.RawOutputsLocalOnly){throw 'PRIOR_HISTORY_RAW_LOCAL_ONLY_REQUIRED'}
        foreach($name in @('WorkerSID','VMUUID','ProfileSourceSHA256','QuerySourceSHA256','VBoxSHA256')){if((Get-InspectionPolicyField $value $name) -isnot [string] -or (Get-InspectionPolicyField $value $name) -cne (Get-InspectionPolicyField $ExpectedContext $name)){throw 'PRIOR_HISTORY_IDENTITY_OR_SOURCE_PIN_MISMATCH'}}
        if($value.ConfigSHA256 -isnot [string] -or $value.ConfigSHA256 -cnotmatch '^[A-F0-9]{64}$'){throw 'PRIOR_HISTORY_CONFIG_HASH_REQUIRED'}
        $id=[guid]::Empty;if($value.AttemptID -isnot [string] -or -not [guid]::TryParseExact($value.AttemptID,'D',[ref]$id) -or $id -eq [guid]::Empty){throw 'PRIOR_HISTORY_ATTEMPT_ID_REQUIRED'}
        Assert-InspectionPolicyShape $value.OpticalBinding @('UUID','Path','Length','SHA256')
        $binding=$value.OpticalBinding;$id=[guid]::Empty
        if($binding.UUID -isnot [string] -or -not [guid]::TryParseExact($binding.UUID,'D',[ref]$id) -or $id -eq [guid]::Empty -or $binding.Path -isnot [string] -or $binding.Path.Length -gt 2048 -or $binding.SHA256 -isnot [string] -or $binding.SHA256 -cnotmatch '^[A-F0-9]{64}$'){throw 'PRIOR_HISTORY_OPTICAL_BINDING_REQUIRED'}
        Assert-InspectionPolicyNumber $binding.Length 1 33554432
        $approved=@($ExpectedContext.MediaProfiles|Where-Object {$_.Path -ceq $binding.Path -and $_.Length -eq $binding.Length -and $_.SHA256 -ceq $binding.SHA256})
        if($approved.Count -ne 1){throw 'PRIOR_HISTORY_REVIEWED_OPTICAL_REQUIRED'}
    }
    if($intent.State -cne 'INSPECTING' -or $final.State -cne 'INSPECTED_PREREQUISITES_PENDING' -or $intent.Commands -isnot [array] -or $intent.Commands.Count -ne 0 -or $final.Commands -isnot [array] -or $final.Commands.Count -ne 3 -or $Bundle.Queries -isnot [array] -or $Bundle.Queries.Count -ne 3){throw 'PRIOR_HISTORY_COMPLETE_SEQUENCE_REQUIRED'}
    foreach($name in @('AttemptID','ControllerPID','ConfigSHA256')){if((Get-InspectionPolicyField $intent $name) -cne (Get-InspectionPolicyField $final $name)){throw 'PRIOR_HISTORY_INTENT_FINAL_MISMATCH'}}
    foreach($name in @('UUID','Path','Length','SHA256')){if((Get-InspectionPolicyField $intent.OpticalBinding $name) -cne (Get-InspectionPolicyField $final.OpticalBinding $name)){throw 'PRIOR_HISTORY_OPTICAL_INTENT_FINAL_MISMATCH'}}
    $started=Get-InspectionPolicyUtcTicks $intent.StartedUTC;$finished=Get-InspectionPolicyUtcTicks $final.FinishedUTC;$creation=Get-InspectionPolicyUtcTicks $intent.ControllerCreationUTC
    if((Get-InspectionPolicyUtcTicks $final.StartedUTC) -ne $started -or (Get-InspectionPolicyUtcTicks $final.ControllerCreationUTC) -ne $creation -or $creation -gt $started -or $started -gt $finished){throw 'PRIOR_HISTORY_TIME_BINDING_MISMATCH'}
    if($Bundle.IntentSHA256 -isnot [string] -or $Bundle.IntentSHA256 -cnotmatch '^[A-F0-9]{64}$' -or $final.AttemptIntentSHA256 -isnot [string] -or $final.AttemptIntentSHA256 -cne $Bundle.IntentSHA256){throw 'PRIOR_HISTORY_DURABLE_INTENT_HASH_MISMATCH'}
    Assert-InspectionPolicyShape $Bundle.Completion @('Schema','State','AttemptID','FinalSHA256','AttemptIntentSHA256','CompletedUTC','TaskAuthority','RawOutputsLocalOnly')
    Assert-InspectionPolicyNumber $Bundle.Completion.Schema 2 2;Assert-InspectionPolicyFalseFlags $Bundle.Completion @('TaskAuthority')
    foreach($name in @('State','AttemptID','FinalSHA256','AttemptIntentSHA256')){Assert-InspectionPolicyString (Get-InspectionPolicyField $Bundle.Completion $name)}
    if($Bundle.FinalSHA256 -isnot [string] -or $Bundle.FinalSHA256 -cnotmatch '^[A-F0-9]{64}$' -or $Bundle.Completion.State -cne 'COMPLETED_READ_ONLY_PREREQUISITES_PENDING' -or $Bundle.Completion.AttemptID -cne $intent.AttemptID -or $Bundle.Completion.FinalSHA256 -cne $Bundle.FinalSHA256 -or $Bundle.Completion.AttemptIntentSHA256 -cne $Bundle.IntentSHA256 -or $Bundle.Completion.RawOutputsLocalOnly -isnot [bool] -or -not $Bundle.Completion.RawOutputsLocalOnly -or (Get-InspectionPolicyUtcTicks $Bundle.Completion.CompletedUTC) -lt $finished){throw 'PRIOR_HISTORY_COMMITTED_COMPLETION_REQUIRED'}
    Assert-InspectionHistoryProfile $final.Profile $final.OpticalBinding $ExpectedContext;Assert-InspectionHistoryProfile $final.XmlProfile $final.OpticalBinding $ExpectedContext
    if($final.Profile.ExpectedState -cne $final.XmlProfile.ExpectedState){throw 'PRIOR_HISTORY_PROFILE_STATE_MISMATCH'}
    for($index=0;$index -lt 3;$index++){
        $sequence=$index+1;$operation=@('VMInfo','DiskInfo','VMInfo')[$index];$record=$Bundle.Queries[$index];$command=$final.Commands[$index]
        Assert-InspectionPolicyShape $record @('Intent','IntentSHA256','Result','ResultSHA256')
        Assert-InspectionPolicyShape $record.Intent @('Schema','AttemptID','Sequence','Operation','AttemptIntentSHA256','State','UTC')
        Assert-InspectionPolicyShape $record.Result @('Schema','AttemptID','Sequence','Operation','AttemptIntentSHA256','QueryIntentSHA256','Result')
        foreach($envelope in @($record.Intent,$record.Result)){
            Assert-InspectionPolicyNumber $envelope.Schema 2 2;Assert-InspectionPolicyNumber $envelope.Sequence $sequence $sequence
            foreach($name in @('AttemptID','Operation','AttemptIntentSHA256')){Assert-InspectionPolicyString (Get-InspectionPolicyField $envelope $name)}
            if($envelope.AttemptID -cne $intent.AttemptID -or $envelope.Operation -cne $operation -or $envelope.AttemptIntentSHA256 -cne $Bundle.IntentSHA256){throw 'PRIOR_HISTORY_QUERY_BINDING_MISMATCH'}
        }
        if($record.IntentSHA256 -isnot [string] -or $record.IntentSHA256 -cnotmatch '^[A-F0-9]{64}$' -or $record.ResultSHA256 -isnot [string] -or $record.ResultSHA256 -cnotmatch '^[A-F0-9]{64}$' -or $record.Result.QueryIntentSHA256 -isnot [string] -or $record.Result.QueryIntentSHA256 -cne $record.IntentSHA256 -or $record.Intent.State -isnot [string] -or $record.Intent.State -cne 'INTENT_NO_REPLAY'){throw 'PRIOR_HISTORY_QUERY_DURABLE_HASH_MISMATCH'}
        $queryUtc=Get-InspectionPolicyUtcTicks $record.Intent.UTC
        if($queryUtc -lt $started -or $queryUtc -gt $finished){throw 'PRIOR_HISTORY_QUERY_TIME_MISMATCH'}
        $native=$record.Result.Result;Assert-InspectionQueryResult $native $operation $queryUtc $finished
        Assert-InspectionPolicyShape $command @('AttemptID','Sequence','Operation','QueryIntentSHA256','QueryResultSHA256','State','ExitCode','ExitCodeKnown','PID','CreationUtc','TimedOut','OutputCapped','Cancelled','OutputBytes','ErrorBytes','ElapsedMilliseconds')
        Assert-InspectionPolicyNumber $command.Sequence $sequence $sequence;Assert-InspectionPolicyNumber $command.ExitCode 0 0;Assert-InspectionPolicyNumber $command.PID 1 2147483647
        Assert-InspectionPolicyNumber $command.OutputBytes 1 1048576;Assert-InspectionPolicyNumber $command.ErrorBytes 0 0;Assert-InspectionPolicyNumber $command.ElapsedMilliseconds 0 90000
        Assert-InspectionPolicyFalseFlags $command @('TimedOut','OutputCapped','Cancelled')
        foreach($name in @('AttemptID','Operation','QueryIntentSHA256','QueryResultSHA256','State')){Assert-InspectionPolicyString (Get-InspectionPolicyField $command $name)}
        if($command.AttemptID -cne $intent.AttemptID -or $command.Operation -cne $operation -or $command.QueryIntentSHA256 -cne $record.IntentSHA256 -or $command.QueryResultSHA256 -cne $record.ResultSHA256 -or $command.ExitCodeKnown -isnot [bool] -or -not $command.ExitCodeKnown){throw 'PRIOR_HISTORY_COMMAND_BINDING_MISMATCH'}
        foreach($name in @('State','ExitCode','ExitCodeKnown','PID','OutputBytes','ErrorBytes','ElapsedMilliseconds')){if((Get-InspectionPolicyField $command $name) -cne (Get-InspectionPolicyField $native $name)){throw 'PRIOR_HISTORY_NATIVE_SUMMARY_MISMATCH'}}
        if((Get-InspectionPolicyUtcTicks $command.CreationUtc) -ne (Get-InspectionPolicyUtcTicks $native.CreationUtc) -or $native.PID -eq $intent.ControllerPID){throw 'PRIOR_HISTORY_NATIVE_IDENTITY_MISMATCH'}
    }
    return $true
}
function Invoke-InspectionQuery([string]$Operation,[int]$Sequence){
    if($Sequence -lt 1 -or $Sequence -gt 3 -or $Operation -cne @('VMInfo','DiskInfo','VMInfo')[$Sequence-1] -or $report.Commands.Count -ne ($Sequence-1) -or $clock.Elapsed.TotalSeconds -ge 90){throw 'NATIVE_BUDGET_OR_OPERATION_REFUSED'}
    $queryIntentPath=Join-Path $out ('query-'+$Sequence+'-intent.json')
    $queryResultPath=Join-Path $out ('query-'+$Sequence+'-result.json')
    Write-InspectionJson $queryIntentPath ([ordered]@{Schema=2;AttemptID=$report.AttemptID;Sequence=$Sequence;Operation=$Operation;AttemptIntentSHA256=$attemptIntentSHA;UTC=[DateTime]::UtcNow.ToString('o');State='INTENT_NO_REPLAY'}) 16384
    $queryIntentSHA=(Get-FileHash -LiteralPath $queryIntentPath -Algorithm SHA256).Hash
    $cancel=[Func[bool]]{return $clock.Elapsed.TotalSeconds -ge 90}
    $result=[AIBS.DesktopInspection.DesktopQuery]::InvokeFixed($Operation,$registry,$cancel)
    Write-InspectionJson $queryResultPath ([ordered]@{Schema=2;AttemptID=$report.AttemptID;Sequence=$Sequence;Operation=$Operation;AttemptIntentSHA256=$attemptIntentSHA;QueryIntentSHA256=$queryIntentSHA;Result=$result})
    $queryResultSHA=(Get-FileHash -LiteralPath $queryResultPath -Algorithm SHA256).Hash
    $report.Commands+=@{AttemptID=$report.AttemptID;Sequence=$Sequence;Operation=$Operation;QueryIntentSHA256=$queryIntentSHA;QueryResultSHA256=$queryResultSHA;State=$result.State;ExitCode=$result.ExitCode;ExitCodeKnown=$result.ExitCodeKnown;PID=$result.PID;CreationUtc=$result.CreationUtc;TimedOut=$result.TimedOut;OutputCapped=$result.OutputCapped;Cancelled=$result.Cancelled;OutputBytes=$result.OutputBytes;ErrorBytes=$result.ErrorBytes;ElapsedMilliseconds=$result.ElapsedMilliseconds}
    if($result.State -cne 'EXITED' -or -not $result.ExitCodeKnown -or $result.ExitCode -ne 0 -or $result.TimedOut -or $result.OutputCapped -or $result.Cancelled -or $result.ClientKillRequested -or $result.StderrLimitReached -or $result.CombinedLimitReached -or $result.Stderr.Length -ne 0){throw 'NATIVE_QUERY_UNCERTAIN_NO_RETRY'}
    return $result.Stdout
}


# Explicitly reviewed v1 read-only failure, not a general quarantine bypass.
function Assert-ReviewedV1Failure {
    $legacy='C:\AI-BS\isolated_workers\windows\runtime\desktop_inspection_v1'
    $name='inspection_20261026T0135210380212Z_4e248c90f4dc4748af3d1598ef26ed8e'
    Assert-InspectionRegularPath $legacy
    $dirs=@(Get-ChildItem -LiteralPath $legacy -Directory -Force)
    if($dirs.Count-ne 1-or $dirs[0].Name-cne $name){throw 'UNREVIEWED_LEGACY_INSPECTION_HISTORY'}
    $expected=@{
        'final.json'='556BEC79D6417964D003FB165E6E4A48984305AD90FC7EF5FA4B2D772B40103B'
        'intent.json'='A4B6AA0D3FAC6EA5A17A9B6BD1B748BE5D42046DD56BC40EDB21E6B1D18B4B20'
        'query-1-intent.json'='3C38CC1BEA3886BBD2BB03B9F6491289E13BB58706D55A66C00E085FA13A578D'
        'query-1-result.json'='A5A929941FC9725401C21F66BC93C262DADA8078C4679E17368D4436D549633C'
    }
    $dir=$dirs[0].FullName;Assert-InspectionRegularPath $dir
    $items=@(Get-ChildItem -LiteralPath $dir -Force)
    if($items.Count-ne $expected.Count){throw 'REVIEWED_LEGACY_FILE_SET_CHANGED'}
    foreach($item in $items){
        if($item.PSIsContainer-or -not $expected.ContainsKey($item.Name)){throw 'REVIEWED_LEGACY_FILE_SET_CHANGED'}
        $null=Read-InspectionHeldText $item.FullName 65536
        if((Get-InspectionHeldHash $held[$held.Count-1])-cne $expected[$item.Name]){throw 'REVIEWED_LEGACY_EVIDENCE_CHANGED'}
    }
}

try{
    # No source import/compiler/query/evidence directory occurs before real identity checks.
    $groups=& 'C:\Windows\System32\whoami.exe' /groups /fo csv /nh
    if($LASTEXITCODE -ne 0){throw 'MEDIUM_INTEGRITY_REQUIRED'}
    $null=Assert-InspectionMediumCsv $groups
    Assert-ReviewedV1Failure
    foreach($path in @($root,$registry,$vmRoot,$config,$vbox,$profilePath,$queryPath)){Assert-InspectionRegularPath $path}
    $profileText=Read-InspectionHeldText $profilePath 262144
    if((Get-InspectionHeldHash $held[$held.Count-1]) -cne $expectedProfileSHA){throw 'PROFILE_SOURCE_PIN_MISMATCH'}
    $queryText=Read-InspectionHeldText $queryPath 262144
    if((Get-InspectionHeldHash $held[$held.Count-1]) -cne $expectedQuerySHA){throw 'QUERY_SOURCE_PIN_MISMATCH'}
    $binary=New-Object IO.FileStream($vbox,[IO.FileMode]::Open,[IO.FileAccess]::Read,[IO.FileShare]::Read)
    $held.Add($binary)
    if($binary.Length -ne 2601824 -or (Get-InspectionHeldHash $binary) -cne $expectedVBoxSHA){throw 'HYPERVISOR_BINARY_PIN_MISMATCH'}
    $signature=Get-AuthenticodeSignature -LiteralPath $vbox
    if($signature.Status -ne 'Valid' -or $signature.SignerCertificate.Thumbprint -ne '2B1BD188256EB612578949A943DE0DDC52D1DF79'){throw 'VALID_PINNED_ORACLE_SIGNATURE_REQUIRED'}
    $configText=Read-InspectionHeldText $config 2097152
    $configHash=Get-InspectionHeldHash $held[$held.Count-1]
    . $profilePath
    $xml=Read-DesktopInspectionXmlSafe $configText
    $machine=$xml.SelectSingleNode('/*[local-name()="VirtualBox"]/*[local-name()="Machine"]')
    $dvd=$machine.SelectSingleNode('./*[local-name()="Hardware"]/*[local-name()="StorageControllers"]/*[local-name()="StorageController"]/*[local-name()="AttachedDevice" and @type="DVD"]/*[local-name()="Image"]')
    if($null -eq $dvd){throw 'CURRENT_OPTICAL_BINDING_MISSING'}
    $dvdUuid=$dvd.GetAttribute('uuid').Trim('{}')
    $images=@($machine.SelectNodes('./*[local-name()="MediaRegistry"]/*[local-name()="DVDImages"]/*[local-name()="Image"]')|Where-Object {$_.GetAttribute('uuid').Trim('{}') -ceq $dvdUuid})
    if($images.Count -ne 1){throw 'UNIQUE_OPTICAL_REGISTRY_BINDING_REQUIRED'}
    $dvdPath=Get-InspectionCanonicalPath $images[0].GetAttribute('location')
    $profiles=@(Get-DesktopInspectionMediaProfiles)
    $media=@($profiles|Where-Object {(Get-InspectionCanonicalPath $_.Path) -ieq $dvdPath})
    if($media.Count -ne 1){throw 'REVIEWED_OPTICAL_PROFILE_REQUIRED'}
    Assert-InspectionRegularPath $dvdPath
    $optical=New-Object IO.FileStream($dvdPath,[IO.FileMode]::Open,[IO.FileAccess]::Read,[IO.FileShare]::Read)
    $held.Add($optical)
    if($optical.Length -ne $media[0].Length -or (Get-InspectionHeldHash $optical) -cne $media[0].SHA256){throw 'OPTICAL_BYTES_PIN_MISMATCH'}
    $binding=@{UUID=$dvdUuid;Path=$dvdPath;Length=$optical.Length;SHA256=$media[0].SHA256}

    # Evidence inherits the already-private worker/SYSTEM/Administrators runtime ACL.
    if(-not(Test-Path -LiteralPath $evidenceRoot)){New-Item -ItemType Directory -Path $evidenceRoot -ErrorAction Stop|Out-Null}
    Assert-InspectionRegularPath $evidenceRoot
    $acl=Get-Acl -LiteralPath $evidenceRoot
    foreach($rule in $acl.Access){
        if($rule.AccessControlType -eq 'Allow' -and $rule.IdentityReference.Translate([Security.Principal.SecurityIdentifier]).Value -notin @($workerSid,'S-1-5-18','S-1-5-32-544')){throw 'PRIVATE_EVIDENCE_ACL_REQUIRED'}
    }
    $leasePath=Join-Path $evidenceRoot 'inspection.lease'
    if(Test-Path -LiteralPath $leasePath){Assert-InspectionRegularPath $leasePath}
    $lease=New-Object IO.FileStream($leasePath,[IO.FileMode]::OpenOrCreate,[IO.FileAccess]::ReadWrite,[IO.FileShare]::None)
    Assert-InspectionRegularPath $leasePath
    $expectedHistory=@{WorkerSID=$workerSid;VMUUID='6c5a53da-ab80-4ecb-8be6-4059266f736e';ProfileSourceSHA256=$expectedProfileSHA;QuerySourceSHA256=$expectedQuerySHA;VBoxSHA256=$expectedVBoxSHA;MediaProfiles=$profiles}
    $priorDirectories=@(Get-ChildItem -LiteralPath $evidenceRoot -Directory -Force)
    if($priorDirectories.Count -gt 64){throw 'PRIOR_HISTORY_COUNT_BOUND_NO_REPLAY'}
    foreach($prior in $priorDirectories){
        Assert-InspectionRegularPath $prior.FullName
        $expectedNames=@('intent.json','final.json','completion.json','query-1-intent.json','query-1-result.json','query-2-intent.json','query-2-result.json','query-3-intent.json','query-3-result.json')
        $items=@(Get-ChildItem -LiteralPath $prior.FullName -Force)
        if($items.Count -ne $expectedNames.Count){throw 'PRIOR_UNFINISHED_INSPECTION_NO_REPLAY'}
        foreach($item in $items){Assert-InspectionRegularPath $item.FullName;if($item.PSIsContainer -or $expectedNames -cnotcontains $item.Name){throw 'PRIOR_HISTORY_UNEXPECTED_FILE_NO_REPLAY'}}
        $priorText=Read-InspectionHeldText (Join-Path $prior.FullName 'intent.json') 65536;$priorIntentHash=Get-InspectionHeldHash $held[$held.Count-1];$priorIntent=$priorText|ConvertFrom-Json -ErrorAction Stop
        $priorText=Read-InspectionHeldText (Join-Path $prior.FullName 'final.json') 65536;$priorFinalHash=Get-InspectionHeldHash $held[$held.Count-1];$priorFinal=$priorText|ConvertFrom-Json -ErrorAction Stop
        $priorCompletion=(Read-InspectionHeldText (Join-Path $prior.FullName 'completion.json') 16384)|ConvertFrom-Json -ErrorAction Stop
        $priorQueries=@()
        foreach($number in 1..3){
            $priorText=Read-InspectionHeldText (Join-Path $prior.FullName ('query-'+$number+'-intent.json')) 16384;$priorQueryIntentHash=Get-InspectionHeldHash $held[$held.Count-1];$priorQueryIntent=$priorText|ConvertFrom-Json -ErrorAction Stop
            $priorText=Read-InspectionHeldText (Join-Path $prior.FullName ('query-'+$number+'-result.json')) 8388608;$priorQueryResultHash=Get-InspectionHeldHash $held[$held.Count-1];$priorQueryResult=$priorText|ConvertFrom-Json -ErrorAction Stop
            $priorQueries+=@{Intent=$priorQueryIntent;IntentSHA256=$priorQueryIntentHash;Result=$priorQueryResult;ResultSHA256=$priorQueryResultHash}
        }
        $null=Assert-InspectionCompletedHistory @{Intent=$priorIntent;IntentSHA256=$priorIntentHash;Final=$priorFinal;FinalSHA256=$priorFinalHash;Completion=$priorCompletion;Queries=$priorQueries} $expectedHistory
    }
    $out=Join-Path $evidenceRoot ('inspection_'+[DateTime]::UtcNow.ToString('yyyyMMddTHHmmssfffffffZ')+'_'+[Guid]::NewGuid().ToString('N'))
    New-Item -ItemType Directory -Path $out -ErrorAction Stop|Out-Null
    Assert-InspectionRegularPath $out
    $process=Get-Process -Id $PID
    $report.State='INSPECTING';$report['WorkerSID']=$identity.User.Value;$report['ControllerPID']=$PID;$report['ControllerCreationUTC']=$process.StartTime.ToUniversalTime().ToString('o')
    $report['AttemptID']=[Guid]::NewGuid().ToString('D')
    $report['StartedUTC']=[DateTime]::UtcNow.ToString('o');$report['VMUUID']='6c5a53da-ab80-4ecb-8be6-4059266f736e'
    $report['ProfileSourceSHA256']=$expectedProfileSHA;$report['QuerySourceSHA256']=$expectedQuerySHA;$report['VBoxSHA256']=$expectedVBoxSHA;$report['ConfigSHA256']=$configHash;$report['OpticalBinding']=$binding
    Write-InspectionJson (Join-Path $out 'intent.json') $report 65536
    $attemptIntentSHA=(Get-FileHash -LiteralPath (Join-Path $out 'intent.json') -Algorithm SHA256).Hash
    $report['AttemptIntentSHA256']=$attemptIntentSHA
    if('AIBS.DesktopInspection.DesktopQuery' -as [type]){throw 'QUERY_TYPE_ALREADY_LOADED_FRESH_PROCESS_REQUIRED'}
    Add-Type -Path $queryPath
    $firstText=Invoke-InspectionQuery 'VMInfo' 1
    $first=ConvertFrom-DesktopInspectionVMInfo $firstText
    $state=$first.VMState
    $profileResult=Assert-DesktopInspectionVMInfo $first $state $binding
    $xmlResult=Assert-DesktopInspectionXml $xml $first $binding
    foreach($diskId in @('9e1efe57-9da5-49f8-acea-763429616968','4241e8d4-9315-48e9-aa89-10f7d8ba6ff5')){
        Assert-InspectionRegularPath (Join-Path $vmRoot ('Snapshots\{'+$diskId+'}.vdi'))
    }
    $saved=Join-Path $vmRoot 'Snapshots\2026-10-24T19-02-47-620416800Z.sav'
    Assert-InspectionRegularPath $saved
    if((Get-Item -LiteralPath $saved).Length -ne 1558556376){throw 'PRESERVED_SNAPSHOT_STATE_LENGTH_MISMATCH'}
    $diskText=Invoke-InspectionQuery 'DiskInfo' 2
    foreach($field in @(@('UUID','9e1efe57-9da5-49f8-acea-763429616968'),@('Parent UUID','4241e8d4-9315-48e9-aa89-10f7d8ba6ff5'))){
        $found=[regex]::Matches($diskText,'(?m)^'+[regex]::Escape($field[0])+':\s*([a-fA-F0-9-]{36})\s*$')
        if($found.Count -ne 1 -or $found[0].Groups[1].Value -ine $field[1]){throw 'INDEPENDENT_DISK_IDENTITY_MISMATCH'}
    }
    $second=ConvertFrom-DesktopInspectionVMInfo (Invoke-InspectionQuery 'VMInfo' 3)
    $null=Assert-DesktopInspectionVMInfo $second $state $binding
    # Both queries must match the same complete fixed profile/state/binding.
    # Transient CLI fields and hashtable enumeration order are not identities.
    if((Get-FileHash -LiteralPath $config -Algorithm SHA256).Hash -cne $configHash){throw 'CONFIG_CHANGED_DURING_INSPECTION'}
    $report['Profile']=$profileResult;$report['XmlProfile']=$xmlResult
    $report.State='INSPECTED_PREREQUISITES_PENDING'
}catch{
    $report.State='QUARANTINED_NO_RETRY'
    $reason=$_.Exception.Message
    if($reason -notmatch '^[A-Z0-9_]{1,128}$'){$reason='INSPECTION_UNCERTAIN'}
    $report['Reason']=$reason
    Write-Host ('REFUSED: '+$reason+'. No automatic retry or VM mutation.')
}finally{
    $report['FinishedUTC']=[DateTime]::UtcNow.ToString('o')
    if($null -ne $out){
        try{
            $finalPath=Join-Path $out 'final.json'
            Write-InspectionJson $finalPath $report 65536
            if($report.State -ceq 'INSPECTED_PREREQUISITES_PENDING'){
                # Crash-consistent local completion, not authentication or task admission.
                # Never publish the accepted name until final and pending marker Flush(true)
                # both returned successfully and their exclusive write handles are closed.
                $completion=[ordered]@{Schema=2;State='COMPLETED_READ_ONLY_PREREQUISITES_PENDING';AttemptID=$report.AttemptID;FinalSHA256=(Get-FileHash -LiteralPath $finalPath -Algorithm SHA256).Hash;AttemptIntentSHA256=$attemptIntentSHA;CompletedUTC=[DateTime]::UtcNow.ToString('o');TaskAuthority=$false;RawOutputsLocalOnly=$true}
                $pending=Join-Path $out 'completion.pending.json';$committed=Join-Path $out 'completion.json'
                Write-InspectionJson $pending $completion 16384
                Assert-InspectionRegularPath $pending
                [IO.File]::Move($pending,$committed)
            }
        }catch{Write-Host 'Completion publication uncertain; missing committed marker or retained pending evidence blocks replay.';$report.State='QUARANTINED_NO_RETRY'}
        Write-Host ('Local inspection evidence: '+$out)
    }
    if($null -ne $lease){$lease.Dispose()}
    foreach($item in $held){$item.Dispose()}
}
if($report.State -cne 'INSPECTED_PREREQUISITES_PENDING'){exit 3}
Write-Host 'Read-only profile inspection complete. Runtime/licensing/transport prerequisites remain unverified; task authority DISABLED.'
exit 0
