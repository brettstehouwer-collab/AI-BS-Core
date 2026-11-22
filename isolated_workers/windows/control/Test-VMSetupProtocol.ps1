$ErrorActionPreference='Stop'
. "$PSScriptRoot\VM-SetupProtocol.ps1"
$session='12345678-1234-1234-1234-123456789abc'
$now=[datetime]::UtcNow
$frame=('a'*64)
$valid=[ordered]@{session=$session;sequence=1;operation='key';created_utc=$now.ToString('o');frame_sha256=$frame;key='Enter'}
$results=@()
$null=ConvertFrom-SetupRequest ($valid | ConvertTo-Json -Compress) $session 1 $frame $now $now
$results+=@{Case='valid frame-bound key';Passed=$true}
foreach($op in @('resume','capture','save','stop')){
    $r=[ordered]@{session=$session;sequence=1;operation=$op;created_utc=$now.ToString('o');frame_sha256='';key=''}
    $null=ConvertFrom-SetupRequest ($r | ConvertTo-Json -Compress) $session 1 '' $now $now
    $results+=@{Case="valid $op";Passed=$true}
}
$bad=@(
    @{Name='foreign session';Field='session';Value='foreign'},
    @{Name='replayed sequence';Field='sequence';Value=0},
    @{Name='future sequence';Field='sequence';Value=2},
    @{Name='string sequence';Field='sequence';Value='1'},
    @{Name='floating sequence';Field='sequence';Value=1.5},
    @{Name='general shell';Field='operation';Value='execute'},
    @{Name='network enable';Field='operation';Value='nic'},
    @{Name='snapshot restore';Field='operation';Value='restore'},
    @{Name='case variant';Field='operation';Value='KEY'},
    @{Name='expired';Field='created_utc';Value=$now.AddSeconds(-61).ToString('o')},
    @{Name='future';Field='created_utc';Value=$now.AddSeconds(6).ToString('o')},
    @{Name='no UTC';Field='created_utc';Value='2026-10-24'},
    @{Name='wrong frame';Field='frame_sha256';Value=('b'*64)},
    @{Name='no frame';Field='frame_sha256';Value=''},
    @{Name='shell hotkey';Field='key';Value='ShiftF10'},
    @{Name='text input';Field='key';Value='cmd.exe'},
    @{Name='null key';Field='key';Value=$null}
)
foreach($case in $bad){
    $r=[ordered]@{};foreach($key in $valid.Keys){$r[$key]=$valid[$key]};$r[$case.Field]=$case.Value
    $rejected=$false
    try{$null=ConvertFrom-SetupRequest ($r | ConvertTo-Json -Compress) $session 1 $frame $now $now}catch{$rejected=$true}
    if(-not $rejected){throw "Accepted $($case.Name)"}
    $results+=@{Case="reject $($case.Name)";Passed=$true}
}
$raw=$valid | ConvertTo-Json -Compress
foreach($case in @(
    @{Name='duplicate';Raw=$raw.Replace('"sequence":1','"sequence":1,"sequence":1')},
    @{Name='unknown field';Raw=$raw.Replace('"sequence":1','"sequence":1,"command":"whoami"')},
    @{Name='escaped name';Raw=$raw.Replace('"sequence"','"\u0073equence"')},
    @{Name='oversized';Raw=(' '*2049)+$raw},
    @{Name='malformed';Raw='null'}
)){
    $rejected=$false;try{$null=ConvertFrom-SetupRequest $case.Raw $session 1 $frame $now $now}catch{$rejected=$true}
    if(-not $rejected){throw "Accepted $($case.Name)"};$results+=@{Case="reject $($case.Name)";Passed=$true}
}
$rejected=$false;try{$null=ConvertFrom-SetupRequest $raw $session 1 $frame $now.AddSeconds(-61) $now}catch{$rejected=$true}
if(-not $rejected){throw 'Accepted stale frame'};$results+=@{Case='reject stale frame';Passed=$true}
foreach($key in @('Enter','Tab','ShiftTab','Up','Down','Left','Right')){
    $codes=@(Get-SetupKeyScancodes $key)
    if($codes.Count -lt 2 -or @($codes | Where-Object {$_ -notmatch '^[a-f0-9]{2}$'}).Count){throw 'Invalid fixed scan codes.'}
    $results+=@{Case="mapped $key";Passed=$true}
}
$rejected=$false;try{$null=Get-SetupKeyScancodes 'F10'}catch{$rejected=$true}
if(-not $rejected){throw 'Accepted unapproved key'};$results+=@{Case='reject unmapped key';Passed=$true}
$results | ConvertTo-Json
