# Actual dispatcher/finalizer AST with fake VBox calls; no live VM operations.
$ErrorActionPreference='Stop'
. "$PSScriptRoot\VM-SetupProtocol.ps1"
$t=$null;$e=$null
$ast=[Management.Automation.Language.Parser]::ParseFile("$PSScriptRoot\Start-WorkerSetupChannel.ps1",[ref]$t,[ref]$e)
if($e.Count){throw 'Controller syntax failed.'}
$node=$ast.Find({param($n)$n -is [Management.Automation.Language.SwitchStatementAst] -and $n.Condition.Extent.Text -eq '$r.operation'},$true)
if($null -eq $node){throw 'Dispatcher missing.'}
$dispatch=[scriptblock]::Create($node.Extent.Text)
$outer=$ast.Find({param($n)$n -is [Management.Automation.Language.TryStatementAst] -and $null -ne $n.Finally -and $n.Finally.Extent.Text -match 'PRESERVATION_UNCONFIRMED'},$true)
$body=$outer.Finally.Extent.Text
$finalize=[scriptblock]::Create($body.Substring(1,$body.Length-2))
$vm='fixed-mock-vm';$sequence=1
$channel=Join-Path ([IO.Path]::GetTempPath()) ('aibs_setup_test_'+[guid]::NewGuid().ToString('N'))
$null=New-Item -ItemType Directory $channel
$frameHash=(Get-FileHash "$PSScriptRoot\VM-SetupProtocol.ps1").Hash.ToLowerInvariant()
function Start-Sleep {param($Seconds)}
function Read-SetupState {if($script:unsafe){throw 'Mock changed guard'};return @{VMState=$script:fakeState}}
function Capture-SetupFrame {$script:captures++}
function Invoke-SetupVBox([string[]]$Arguments,[int]$Timeout=20000){
    $script:calls+=($Arguments -join ' ')
    if($Arguments[0] -eq 'startvm'){$script:fakeState='running';return ''}
    if($Arguments[2] -eq 'savestate'){$script:fakeState='saved';return ''}
    if($Arguments[2] -eq 'screenshotpng'){
        if($script:changed){[IO.File]::WriteAllText($Arguments[3],'changed')}else{Copy-Item "$PSScriptRoot\VM-SetupProtocol.ps1" $Arguments[3] -Force}
        return ''
    }
    if($Arguments[2] -eq 'keyboardputscancode'){return ''}
    throw 'Unexpected VBox operation.'
}
function Save-SetupStatus {if($script:failStatus){throw 'Mock status publication failure'};$script:statusSaved=$true}
$lease=New-Object PSObject
$lease | Add-Member ScriptMethod Dispose {$script:leaseDisposed=$true}
$results=@()
$script:unsafe=$false;$script:changed=$false;$script:captures=0;$script:calls=@();$script:fakeState='saved'
$r=@{operation='resume'};$v=@{VMState='saved'}
& $dispatch
if($script:fakeState -ne 'running' -or $script:captures -ne 1 -or $script:calls.Count -ne 1){throw 'Resume contract failed.'}
$results+=@{Case='resume only saved VM and capture';Passed=$true}
foreach($changed in @($false,$true)){
    $script:calls=@();$script:changed=$changed;$script:fakeState='running';$script:frameHash=(Get-FileHash "$PSScriptRoot\VM-SetupProtocol.ps1").Hash.ToLowerInvariant()
    $v=@{VMState='running'};$r=@{operation='key';key='Enter'};$rejected=$false
    try{& $dispatch}catch{$rejected=$true}
    $keyCalls=@($script:calls | Where-Object {$_ -match 'keyboardputscancode'})
    if($changed -and (-not $rejected -or $keyCalls.Count)){throw 'Changed pixels received key.'}
    if(-not $changed -and ($rejected -or $keyCalls.Count -ne 1 -or $keyCalls[0] -notmatch '1c 9c$' -or $script:frameHash -ne '')){throw 'Valid Enter dispatch failed.'}
    $results+=@{Case="pixel change=$changed gates key";Passed=$true}
}
foreach($state in @('running','saved')){
    $script:calls=@();$script:fakeState=$state;$script:statusSaved=$false;$script:leaseDisposed=$false;$validated=$true;$status=[ordered]@{State='FAILED_REVIEW_REQUIRED'}
    & $finalize
    if($script:fakeState -ne 'saved' -or -not $script:statusSaved -or -not $script:leaseDisposed -or @($script:calls | Where-Object {$_ -match 'savestate$'}).Count -ne [int]($state -eq 'running')){throw 'Final preservation contract failed.'}
    $results+=@{Case="finalizer preserves $state without boot";Passed=$true}
}
$script:unsafe=$true;$script:calls=@();$validated=$true;$status=[ordered]@{State='FAILED'}
& $finalize
if($status.State -ne 'PRESERVATION_UNCONFIRMED' -or $script:calls.Count){throw 'Unsafe state received control operation.'}
$results+=@{Case='changed guard prevents final control and records unknown preservation';Passed=$true}
$script:unsafe=$false;$script:fakeState='saved';$script:failStatus=$true;$script:leaseDisposed=$false;$validated=$true;$status=[ordered]@{State='FAILED'};$rejected=$false
try{& $finalize}catch{$rejected=$true}
if(-not $rejected -or -not $script:leaseDisposed){throw 'Status failure retained lease.'}
$results+=@{Case='status publication failure still releases lease after preservation';Passed=$true}
$results | ConvertTo-Json
Write-Host "Synthetic evidence retained: $channel"
