$ErrorActionPreference='Stop'
. "$PSScriptRoot\ImmutableSetupStatus.ps1"
$root=Join-Path ([IO.Path]::GetTempPath()) ('aibs_append_status_'+[guid]::NewGuid().ToString('N'))
$null=New-Item -ItemType Directory $root
$results=@();$status=[ordered]@{State='READY';Generation=1}
$first=Publish-ImmutableSetupStatus $root $status 1
$original=[IO.File]::ReadAllText($first)
if((Read-ImmutableSetupStatus $root).Generation -ne 1){throw 'Initial status missing.'}
$results+=@{Case='complete initial publication';Passed=$true}
$readerHandle=[IO.File]::Open($first,[IO.FileMode]::Open,[IO.FileAccess]::Read,[IO.FileShare]::Read)
try{
    $status.Generation=2
    $second=Publish-ImmutableSetupStatus $root $status 2
    if((Read-ImmutableSetupStatus $root).Generation -ne 2 -or [IO.File]::ReadAllText($first) -cne $original){throw 'Held reader prevented new immutable publication.'}
}finally{$readerHandle.Dispose()}
$results+=@{Case='non-delete-sharing reader does not block new generation or change old bytes';Passed=$true}
$rejected=$false
try{$null=Publish-ImmutableSetupStatus $root $status 2}catch{$rejected=$true}
if(-not $rejected -or (Read-ImmutableSetupStatus $root).Generation -ne 2){throw 'Duplicate publication damaged previous record.'}
$results+=@{Case='duplicate generation rejected without overwriting';Passed=$true}
[IO.File]::WriteAllText((Join-Path $root 'status_00000003.pending'),'{')
if((Read-ImmutableSetupStatus $root).Generation -ne 2){throw 'Incomplete pending file was admitted.'}
$results+=@{Case='pending partial JSON is invisible to readers';Passed=$true}
[IO.File]::WriteAllText((Join-Path $root 'status_00000003.json'),'{')
$rejected=$false;try{$null=Read-ImmutableSetupStatus $root}catch{$rejected=$true}
if(-not $rejected){throw 'Corrupt newest record fell back to stale success.'}
$results+=@{Case='corrupt newest record fails closed';Passed=$true}
$bad=Join-Path $root 'bad';$null=New-Item -ItemType Directory $bad
[IO.File]::WriteAllText((Join-Path $bad 'status_00000001.json'),'{"Publication":2}')
$rejected=$false;try{$null=Read-ImmutableSetupStatus $bad}catch{$rejected=$true}
if(-not $rejected){throw 'Mismatched publication identity accepted.'}
$results+=@{Case='publication/file identity mismatch rejected';Passed=$true}
foreach($n in @(0,4097)){
    $rejected=$false;try{$null=Publish-ImmutableSetupStatus $root $status $n}catch{$rejected=$true}
    if(-not $rejected){throw 'Out-of-bound status number accepted.'}
    $results+=@{Case="publication bound rejects $n";Passed=$true}
}
$status.Huge='x'*2097153;$rejected=$false
try{$null=Publish-ImmutableSetupStatus $root $status 4}catch{$rejected=$true}
if(-not $rejected){throw 'Oversized status accepted.'}
$results+=@{Case='oversized record rejected before file mutation';Passed=$true}
$results | ConvertTo-Json
Write-Host "Synthetic evidence retained: $root"
