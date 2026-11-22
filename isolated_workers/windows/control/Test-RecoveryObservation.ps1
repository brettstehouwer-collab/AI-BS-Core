# Execute the actual observation branch with a fake VBox function; no VM operations.
$ErrorActionPreference='Stop'
. "$PSScriptRoot\VM-RecoveryGuards.ps1"
$tokens=$null; $errors=$null
$ast=[Management.Automation.Language.Parser]::ParseFile("$PSScriptRoot\Recover-CurrentWorkerVM.ps1",[ref]$tokens,[ref]$errors)
if($errors.Count){throw 'Launcher syntax error.'}
$branch=$ast.Find({param($node) $node -is [Management.Automation.Language.IfStatementAst] -and $node.Clauses[0].Item1.Extent.Text -eq '$ObserveRunning' -and $node.Extent.Text -match 'Reviewed running recovery identity differs'},$true)
if($null -eq $branch){throw 'Observation branch missing.'}
$text=$branch.Clauses[0].Item2.Extent.Text
$body=[scriptblock]::Create($text.Substring(1,$text.Length-2))
$root='C:\AI-BS\isolated_workers\windows'
$out='C:\AI-BS\scratch\unused_mock_screenshot'
$vm='6c5a53da-ab80-4ecb-8be6-4059266f736e'
$disk='59e3fed5-5878-4524-8a70-9b0dc7a5067b'
$fixture=Get-Content "$root\runtime\headless_recovery_1\vbox_07.stdout.txt" -Raw
function Invoke-RecoveryVBox([string[]]$Arguments,[int]$Timeout=20000){
    $script:calls+=($Arguments -join ' ')
    if($Arguments[0] -eq 'showvminfo'){
        if($script:saved){return $fixture.Replace('VMState="running"','VMState="saved"')}
        return $fixture
    }
    if($Arguments[0] -eq 'controlvm' -and $Arguments[2] -eq 'screenshotpng'){
        if($script:failShot){throw 'Mock0x0display'}
        return ''
    }
    if($Arguments[0] -eq 'controlvm' -and $Arguments[2] -eq 'savestate'){$script:saved=$true;return ''}
    throw 'Unexpected mock operation.'
}
$results=@()
foreach($fail in @($false,$true)){
    $script:failShot=$fail;$script:saved=$false;$script:calls=@()
    $current=ConvertFrom-RecoveryVMInfo $fixture
    $report=[ordered]@{}
    & $body
    if($report.State -ne 'RECOVERY_SAVED_REVIEW_REQUIRED' -or -not $script:saved -or $report.ScreenshotCaptured -eq $fail -or @($script:calls | Where-Object {$_ -match 'savestate$'}).Count -ne 1 -or @($script:calls | Where-Object {$_ -match '^startvm|^snapshot| reset| poweroff'}).Count){throw 'Preservation branch contract failed.'}
    $results+=@{Case="screenshot failure=$fail still saves and verifies same VM";Passed=$true}
}
$script:calls=@();$current=ConvertFrom-RecoveryVMInfo ($fixture.Replace('nic1="none"','nic1="nat"'));$report=[ordered]@{};$rejected=$false
try{& $body}catch{$rejected=$true}
if(-not $rejected -or $script:calls.Count){throw 'Unsafe running VM was operated.'}
$results+=@{Case='unsafe running settings rejected before control operation';Passed=$true}
$results | ConvertTo-Json
