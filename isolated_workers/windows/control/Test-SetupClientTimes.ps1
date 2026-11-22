# Production request-client conditions against actual Windows/PowerShell date coercion.
# No VM command, subprocess or UI input is performed by this test.
$ErrorActionPreference='Stop'
$tokens=$null;$errors=$null
$path="$PSScriptRoot\Send-WorkerSetupRequest.ps1"
$ast=[Management.Automation.Language.Parser]::ParseFile($path,[ref]$tokens,[ref]$errors)
if($errors.Count){throw 'Client syntax error.'}
function Condition([string]$Message){
    $n=$ast.FindAll({param($node)$node -is [Management.Automation.Language.IfStatementAst] -and $node.Extent.Text.Contains($Message)},$true) | Sort-Object {$_.Extent.Text.Length} | Select-Object -First 1
    if($null -eq $n){throw "Client condition missing: $Message"}
    return [scriptblock]::Create('return ('+$n.Clauses[0].Item1.Extent.Text+')')
}
$fresh=Condition 'No fresh ready channel.'
$identity=Condition 'Worker process identity changed.'
$frame=Condition 'Fresh reviewed frame required.'
$session='fixture-session';$Key='Enter';$now=[datetime]::UtcNow;$created=$now.AddMinutes(-1)
$p=[pscustomobject]@{StartTime=$created.ToLocalTime()}
$results=@()
foreach($representation in @('UTC strings','UTC objects','Local objects','JSON parser output')){
    $s=[pscustomobject]@{Session=$session;State='READY';UpdatedUTC=$now.ToString('o');ProcessCreationUTC=$created.ToString('o');FrameUTC=$now.ToString('o');LastFrameSHA256=('a'*64)}
    switch($representation){
        'UTC objects' {$s.UpdatedUTC=$now;$s.ProcessCreationUTC=$created;$s.FrameUTC=$now}
        'Local objects' {$s.UpdatedUTC=$now.ToLocalTime();$s.ProcessCreationUTC=$created.ToLocalTime();$s.FrameUTC=$now.ToLocalTime()}
        'JSON parser output' {$s=$s | ConvertTo-Json | ConvertFrom-Json}
    }
    foreach($case in @(@{Name='freshness';Expression=$fresh},@{Name='creation identity';Expression=$identity},@{Name='frame age';Expression=$frame})){
        if(& $case.Expression){throw "Legitimate $representation rejected by $($case.Name)"}
        $results+=@{Case="$representation / $($case.Name)";Passed=$true}
    }
}
$s.UpdatedUTC=$now.AddSeconds(-20).ToString('o')
if(-not (& $fresh)){throw 'Stale heartbeat accepted.'}
$results+=@{Case='stale heartbeat still rejected';Passed=$true}
$s.FrameUTC=$now.AddSeconds(-70).ToString('o')
if(-not (& $frame)){throw 'Stale reviewed frame accepted.'}
$results+=@{Case='stale frame still rejected';Passed=$true}
$s.ProcessCreationUTC=$created.AddTicks(1).ToString('o')
if(-not (& $identity)){throw 'Different process creation time accepted.'}
$results+=@{Case='one-tick creation mismatch still rejected';Passed=$true}
$results | ConvertTo-Json
