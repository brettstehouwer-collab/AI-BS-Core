# Operator-side request writer. It never runs commands as the worker account.
[CmdletBinding()]
param(
    [Parameter(Mandatory=$true)][string]$Channel,
    [Parameter(Mandatory=$true)][ValidateSet('resume','capture','save','key','stop')][string]$Operation,
    [ValidateSet('','Enter','Tab','ShiftTab','Up','Down','Left','Right')][string]$Key=''
)
$ErrorActionPreference='Stop'
. "$PSScriptRoot\VM-RecoveryGuards.ps1"
. "$PSScriptRoot\VM-SetupStatus.ps1"
$channelPath=[IO.Path]::GetFullPath($Channel)
if($channelPath -notmatch '^C:\\AI-BS\\isolated_workers\\windows\\runtime\\setup_channel_([0-9a-f-]{36})$'){throw 'Unexpected channel path.'}
$session=$matches[1]
Assert-RecoveryRegularPath $channelPath
$s=Read-ImmutableSetupStatus $channelPath
if($s.Session -cne $session -or $s.State -cne 'READY' -or ([datetime]::UtcNow-([datetime]$s.UpdatedUTC).ToUniversalTime()).TotalSeconds -gt 10){throw 'No fresh ready channel.'}
$p=Get-Process -Id $s.PID -ErrorAction Stop
if($p.StartTime.ToUniversalTime().Ticks -ne ([datetime]$s.ProcessCreationUTC).ToUniversalTime().Ticks){throw 'Worker process identity changed.'}
$cim=Get-CimInstance Win32_Process -Filter "ProcessId=$($s.PID)"
$owner=Invoke-CimMethod -InputObject $cim -MethodName GetOwnerSid
if($owner.ReturnValue -ne 0 -or $owner.Sid -ne 'S-1-5-21-2133766663-4066672948-2456486318-1005'){throw 'Channel is not owned by approved worker.'}
if($Operation -ne 'key' -and $Key -ne ''){throw 'Unexpected key.'}
$frame=''
if($Operation -eq 'key'){
    if(-not $Key -or $s.LastFrameSHA256 -notmatch '^[a-f0-9]{64}$' -or ([datetime]::UtcNow-([datetime]$s.FrameUTC).ToUniversalTime()).TotalSeconds -gt 60){throw 'Fresh reviewed frame required.'}
    Assert-RecoveryRegularPath $s.LastFramePath
    if((Get-FileHash -LiteralPath $s.LastFramePath).Hash.ToLowerInvariant() -cne $s.LastFrameSHA256){throw 'Frame bytes changed.'}
    $frame=$s.LastFrameSHA256
}
$r=[ordered]@{session=$session;sequence=[int]$s.NextSequence;operation=$Operation;created_utc=[datetime]::UtcNow.ToString('o');frame_sha256=$frame;key=$Key}
$dest=Join-Path $channelPath ('{0:d4}.request.json' -f $r.sequence)
$temp=Join-Path $channelPath ([guid]::NewGuid().ToString('N')+'.pending')
$bytes=[Text.Encoding]::UTF8.GetBytes(($r | ConvertTo-Json -Compress))
$file=[IO.File]::Open($temp,[IO.FileMode]::CreateNew,[IO.FileAccess]::Write,[IO.FileShare]::None)
try{$file.Write($bytes,0,$bytes.Length);$file.Flush($true)}finally{$file.Dispose()}
[IO.File]::Move($temp,$dest)
[pscustomobject]@{Session=$session;Sequence=$r.sequence;Operation=$Operation;Request=$dest} | ConvertTo-Json
