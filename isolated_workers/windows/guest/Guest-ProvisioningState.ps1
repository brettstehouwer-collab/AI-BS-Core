# Single-attempt provisioning state, not task admission or a hostile-admin boundary.
function Assert-AIBSProvisionStatePath([string]$Path) {
    $node=Get-Item -LiteralPath $Path -Force -ErrorAction Stop
    while($null -ne $node) {
        if($node.Attributes -band [IO.FileAttributes]::ReparsePoint){throw 'Linked provisioning state rejected.'}
        $node=if($node -is [IO.FileInfo]){$node.Directory}else{$node.Parent}
    }
}

function Open-AIBSProvisionState([string]$Base,[string]$Attempt) {
    if(-not [IO.Path]::IsPathRooted($Base) -or $Base -match '^\\\\' -or $Attempt -cnotmatch '^[a-f0-9]{32}$') {
        throw 'Invalid provisioning state identity.'
    }
    $ancestor=$Base
    while(-not(Test-Path -LiteralPath $ancestor)) {
        $ancestor=[IO.Path]::GetDirectoryName($ancestor)
        if([string]::IsNullOrEmpty($ancestor)){throw 'Missing provisioning state ancestor.'}
    }
    Assert-AIBSProvisionStatePath $ancestor
    [IO.Directory]::CreateDirectory($Base)|Out-Null
    Assert-AIBSProvisionStatePath $Base
    $lockPath=Join-Path $Base 'provisioning.lock'
    if(Test-Path -LiteralPath $lockPath){Assert-AIBSProvisionStatePath $lockPath}
    $lease=New-Object IO.FileStream($lockPath,[IO.FileMode]::OpenOrCreate,[IO.FileAccess]::ReadWrite,[IO.FileShare]::None)
    try {
        $intent=Join-Path $Base 'attempt_intent.json'
        if(Test-Path -LiteralPath $intent){throw 'PRIOR_PROVISIONING_ATTEMPT: inspect retained results before any reviewed recovery; automatic replay denied.'}
        $bytes=[Text.Encoding]::UTF8.GetBytes((@{
            Schema=1;Attempt=$Attempt;StartedUTC=[DateTime]::UtcNow.ToString('o')
            AutomaticReplayAllowed=$false;TaskAdmissionAuthorized=$false
        }|ConvertTo-Json))
        $stream=New-Object IO.FileStream($intent,[IO.FileMode]::CreateNew,[IO.FileAccess]::Write,[IO.FileShare]::Read)
        try{$stream.Write($bytes,0,$bytes.Length);$stream.Flush($true)}finally{$stream.Dispose()}
        return $lease
    } catch {$lease.Dispose();throw}
}
