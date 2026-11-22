# Real disposable filesystem tests; never touch the guest/host installation directory.
$ErrorActionPreference='Stop'
$helper=Join-Path $PSScriptRoot 'Guest-ProvisioningState.ps1'
if(-not(Test-Path -LiteralPath $helper)){throw 'Required provisioning state helper is missing.'}
. $helper
$checkpoint=(Get-Content -LiteralPath 'C:\AI-BS\scratch\phase4_guest_media_v2_checkpoint.txt' -Raw).Trim()
$testRoot=Join-Path $checkpoint ('state_test_'+[Guid]::NewGuid().ToString('N'))
[IO.Directory]::CreateDirectory($testRoot)|Out-Null
$attempt=[Guid]::NewGuid().ToString('N')
$base=Join-Path $testRoot 'guest_state'
$lease=Open-AIBSProvisionState $base $attempt
try {
    $record=Get-Content -LiteralPath (Join-Path $base 'attempt_intent.json') -Raw|ConvertFrom-Json
    if($record.Attempt -cne $attempt -or $record.AutomaticReplayAllowed -ne $false){throw 'Durable intent is wrong.'}
    Write-Output 'PASS durable intent binds exact attempt and denies replay'
    $blocked=$false
    try {$other=Open-AIBSProvisionState $base ([Guid]::NewGuid().ToString('N'));$other.Dispose()}catch{$blocked=$true}
    if(-not $blocked){throw 'Concurrent provisioning was admitted.'}
    Write-Output 'PASS exclusive live provisioning lease'
} finally {$lease.Dispose()}
$blocked=$false
try {$other=Open-AIBSProvisionState $base ([Guid]::NewGuid().ToString('N'));$other.Dispose()}catch{$blocked=$true}
if(-not $blocked){throw 'Uncertain prior attempt was replayed.'}
Write-Output 'PASS retained intent blocks replay after process lease release'
$invalidBase=Join-Path $testRoot 'invalid_attempt'
$blocked=$false
try {$other=Open-AIBSProvisionState $invalidBase '..\escape';$other.Dispose()}catch{$blocked=$true}
if(-not $blocked -or(Test-Path -LiteralPath $invalidBase)){throw 'Invalid attempt mutated the filesystem.'}
Write-Output 'PASS invalid attempt rejected before writes'
$corrupt=Join-Path $testRoot 'corrupt_state';[IO.Directory]::CreateDirectory($corrupt)|Out-Null
[IO.File]::WriteAllText((Join-Path $corrupt 'attempt_intent.json'),'{partial')
$blocked=$false
try {$other=Open-AIBSProvisionState $corrupt ([Guid]::NewGuid().ToString('N'));$other.Dispose()}catch{$blocked=$true}
if(-not $blocked){throw 'Corrupt prior intent allowed replay.'}
Write-Output 'PASS partial/corrupt intent fails closed without stale fallback'
Write-Output 'RESULT 5 state tests passed; test files retained, no installers executed.'
