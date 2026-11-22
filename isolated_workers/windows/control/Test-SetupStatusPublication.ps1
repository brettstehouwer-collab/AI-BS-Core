# Actual controller publisher plus immutable file semantics; no VM operations.
$ErrorActionPreference='Stop'
. "$PSScriptRoot\VM-SetupStatus.ps1"
$t=$null;$e=$null
$ast=[Management.Automation.Language.Parser]::ParseFile("$PSScriptRoot\Start-WorkerSetupChannel.ps1",[ref]$t,[ref]$e)
if($e.Count){throw 'Controller syntax error.'}
$f=$ast.Find({param($n)$n -is [Management.Automation.Language.FunctionDefinitionAst] -and $n.Name -eq 'Save-SetupStatus'},$true)
Invoke-Expression $f.Extent.Text
$channel=Join-Path ([IO.Path]::GetTempPath()) ('aibs_status_wrapper_'+[guid]::NewGuid().ToString('N'))
$null=New-Item -ItemType Directory $channel
$publication=0;$sequence=1;$frameHash='';$frameTime=[datetime]::MinValue
$status=[ordered]@{State='READY';Generation=1}
Save-SetupStatus
$first=Join-Path $channel 'status_00000001.json'
$original=[IO.File]::ReadAllText($first)
if((Read-ImmutableSetupStatus $channel).Generation -ne 1){throw 'Initial status missing.'}
$results=@(@{Case='initial actual controller publication';Passed=$true})
$hold=[IO.File]::Open($first,[IO.FileMode]::Open,[IO.FileAccess]::Read,[IO.FileShare]::Read)
try{
    $status.Generation=2;Save-SetupStatus
    if((Read-ImmutableSetupStatus $channel).Generation -ne 2 -or [IO.File]::ReadAllText($first) -cne $original){throw 'Held prior reader blocked publication or changed bytes.'}
}finally{$hold.Dispose()}
$results+=@{Case='old non-delete-sharing reader survives new complete generation';Passed=$true}
$sequence=3;$frameHash='a'*64;$frameTime=[datetime]::UtcNow;$status.Generation=3
Save-SetupStatus
$r=Read-ImmutableSetupStatus $channel
if($r.Publication -ne 3 -or $r.NextSequence -ne 3 -or $r.LastFrameSHA256 -ne $frameHash -or -not $r.FrameUTC){throw 'Controller frame/sequence binding lost.'}
$results+=@{Case='sequence and frame binding preserved in newest immutable publication';Passed=$true}
$publication=2;$status.Generation=99;$rejected=$false
try{Save-SetupStatus}catch{$rejected=$true}
if(-not $rejected -or (Read-ImmutableSetupStatus $channel).Generation -ne 3){throw 'Duplicate publisher overwrote existing status.'}
$results+=@{Case='duplicate generation fails without stale/overwritten success';Passed=$true}
$results | ConvertTo-Json
Write-Host "Synthetic files retained: $channel"
