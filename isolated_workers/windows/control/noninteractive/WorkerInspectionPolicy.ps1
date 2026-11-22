# Pure description/validation of one non-elevated, demand-only inspection task.
function Get-WorkerInspectionSpec {
    return [pscustomobject]@{
        TaskName='AIBS_Phase4_Inspect_v2'
        UserId='S-1-5-21-2133766663-4066672948-2456486318-1005'
        LogonType=2;RunLevel=0;ActionCount=1;ActionType=0
        Path='C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe'
        Arguments='-NoProfile -NonInteractive -WindowStyle Hidden -ExecutionPolicy RemoteSigned -File "C:\AI-BS\isolated_workers\windows\control\Inspect-CurrentWorkerDesktopV2.ps1"'
        WorkingDirectory='C:\AI-BS\isolated_workers\windows\control'
        TriggerCount=0;RestartCount=0;MultipleInstances=2;ExecutionTimeLimit='PT3M'
        EntrySHA256='85B39D4FA51412002ADF2E37D22356AD19572C7D80969BDEAD4FB77197D2657B'
        ConfigurationPath='C:\AI-BS\isolated_workers\windows\runtime\base_preparation_v2\vms\AI-BS-Eval-Base-20261023\AI-BS-Eval-Base-20261023.vbox'
        ConfigurationSHA256='6C5E94B14B57C7DF1D3097F549C363124B797BB434D937415239D95B649C64B1'
    }
}
function Assert-WorkerInspectionConfiguration([string]$Path,[string]$ExpectedSHA256){
    if($ExpectedSHA256-cnotmatch '^[A-F0-9]{64}$'){throw 'EXACT_CONFIG_PIN_REQUIRED'}
    $node=Get-Item -LiteralPath $Path -Force -ErrorAction Stop
    if($node.PSIsContainer){throw 'REGULAR_CONFIG_FILE_REQUIRED'}
    while($null-ne $node){
        if($node.Attributes-band [IO.FileAttributes]::ReparsePoint){throw 'LINKED_CONFIG_PATH_REFUSED'}
        $node=if($node-is [IO.FileInfo]){$node.Directory}else{$node.Parent}
    }
    if((Get-FileHash -LiteralPath $Path -Algorithm SHA256).Hash-cne $ExpectedSHA256){throw 'CONFIGURATION_REVIEW_REQUIRED_NO_REGISTRATION'}
    return $true
}
function Assert-WorkerInspectionSpec($Value) {
    if($null-eq $Value){throw 'TASK_DESCRIPTION_REQUIRED'}
    $expected=Get-WorkerInspectionSpec
    foreach($name in @('TaskName','UserId','LogonType','RunLevel','ActionCount','ActionType','Path','Arguments','WorkingDirectory','TriggerCount','RestartCount','MultipleInstances','ExecutionTimeLimit')){
        $property=$Value.PSObject.Properties[$name]
        if($null-eq $property-or $null-eq $property.Value-or $property.Value-cne $expected.$name){throw ('UNEXPECTED_INSPECTION_TASK_'+$name)}
    }
    return $true
}
