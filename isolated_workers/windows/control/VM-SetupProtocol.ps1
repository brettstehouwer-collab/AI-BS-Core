# Pure setup-channel schema and fixed keyboard mapping; no processes on import.
function ConvertFrom-SetupRequest([string]$Raw,[string]$Session,[int]$Sequence,[string]$FrameHash,[datetime]$FrameTime,[datetime]$Now) {
    if ([Text.Encoding]::UTF8.GetByteCount($Raw) -gt 2048 -or $Raw -match '\\') { throw 'Request size/escaping rejected.' }
    $fields=@('session','sequence','operation','created_utc','frame_sha256','key')
    foreach($field in $fields) { if([regex]::Matches($Raw,('"'+$field+'"\s*:'),[Text.RegularExpressions.RegexOptions]::IgnoreCase).Count -ne 1){throw 'Missing/duplicate request field.'} }
    $r=ConvertFrom-Json -InputObject $Raw -ErrorAction Stop
    if($null -eq $r -or @($r.PSObject.Properties).Count -ne 6){throw 'Request shape rejected.'}
    foreach($p in $r.PSObject.Properties){if($p.Name -cnotin $fields){throw 'Unknown request field.'}}
    if($r.session -isnot [string] -or $r.session -cne $Session -or $r.sequence -isnot [int] -or $r.sequence -ne $Sequence -or $Sequence -lt 1 -or $Sequence -gt 128){throw 'Session/sequence rejected.'}
    if($r.operation -isnot [string] -or $r.operation -cnotin @('resume','capture','save','key','stop')){throw 'Operation rejected.'}
    if($r.created_utc -isnot [string] -or $r.created_utc -notmatch '^\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d(\.\d{1,7})?Z$'){throw 'UTC request timestamp required.'}
    $created=[datetime]::Parse($r.created_utc,[Globalization.CultureInfo]::InvariantCulture,[Globalization.DateTimeStyles]::RoundtripKind)
    if(($Now-$created).TotalSeconds -gt 60 -or ($created-$Now).TotalSeconds -gt 5){throw 'Expired/future request rejected.'}
    if($r.key -isnot [string] -or $r.frame_sha256 -isnot [string]){throw 'Typed request fields required.'}
    if($r.operation -eq 'key'){
        if($r.key -cnotin @('Enter','Tab','ShiftTab','Up','Down','Left','Right') -or $FrameHash -notmatch '^[a-f0-9]{64}$' -or $r.frame_sha256 -cne $FrameHash -or ($Now-$FrameTime).TotalSeconds -gt 60 -or ($Now-$FrameTime).TotalSeconds -lt 0){throw 'Key/frame binding rejected.'}
    }elseif($r.key -cne '' -or $r.frame_sha256 -cne ''){throw 'Unexpected key/frame payload.'}
    return $r
}
function Get-SetupKeyScancodes([string]$Key){
    switch -CaseSensitive ($Key){
        'Enter' {return @('1c','9c')}
        'Tab' {return @('0f','8f')}
        'ShiftTab' {return @('2a','0f','8f','aa')}
        'Up' {return @('e0','48','e0','c8')}
        'Down' {return @('e0','50','e0','d0')}
        'Left' {return @('e0','4b','e0','cb')}
        'Right' {return @('e0','4d','e0','cd')}
        default {throw 'Key is not approved.'}
    }
}
