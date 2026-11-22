# Guest provisioning only. Never a generated-task execution endpoint.
[CmdletBinding()]
param([string]$MediaRoot='D:\')
$ErrorActionPreference='Stop'
$ProgressPreference='SilentlyContinue'

# This read-only check intentionally precedes helper imports and every disk mutation.
try {
    $identity=[Security.Principal.WindowsIdentity]::GetCurrent()
    $system=Get-CimInstance Win32_ComputerSystem -ErrorAction Stop
    $product=Get-CimInstance Win32_ComputerSystemProduct -ErrorAction Stop
    if($product.UUID -ine '6c5a53da-ab80-4ecb-8be6-4059266f736e' -or
       $system.Model -cne 'VirtualBox' -or
       $system.Manufacturer -cnotin @('innotek GmbH','Oracle Corporation') -or
       $identity.User.Value.StartsWith('S-1-5-21-2133766663-4066672948-2456486318-', [StringComparison]::Ordinal)) {
        throw 'WRONG_GUEST: this installer must not run on the AI-BS host or another VM.'
    }
} catch {
    [Console]::Error.WriteLine('WRONG_GUEST: exact dedicated guest identity was not established; no installation attempted.')
    exit 2
}

$resultDir=$null
$provisionLease=$null
$publication=0
$watch=[Diagnostics.Stopwatch]::StartNew()
$result=[ordered]@{
    Schema=1; StartedUTC=[DateTime]::UtcNow.ToString('o'); CompletedUTC=$null
    VMUUID='6c5a53da-ab80-4ecb-8be6-4059266f736e'; Status='PREFLIGHT'
    RuntimesVerified=$false; TaskAdmissionAuthorized=$false; Quarantined=$false
    Steps=@(); Versions=$null; Error=$null
}
function Assert-RegularGuestPath([string]$Path) {
    $item=Get-Item -LiteralPath $Path -Force -ErrorAction Stop
    while($null -ne $item) {
        if($item.Attributes -band [IO.FileAttributes]::ReparsePoint){throw 'Linked provisioning path rejected.'}
        $item=if($item -is [IO.FileInfo]){$item.Directory}else{$item.Parent}
    }
}
function Publish-GuestResult {
    if($null -eq $resultDir){return}
    $script:publication++
    $path=Join-Path $resultDir ('result_{0:D6}.json' -f $script:publication)
    $bytes=[Text.Encoding]::UTF8.GetBytes(($result | ConvertTo-Json -Depth 8))
    if($bytes.Length -gt 262144){throw 'Provisioning report exceeded its byte limit.'}
    $stream=New-Object IO.FileStream($path,[IO.FileMode]::CreateNew,[IO.FileAccess]::Write,[IO.FileShare]::Read)
    try {$stream.Write($bytes,0,$bytes.Length);$stream.Flush($true)}finally{$stream.Dispose()}
}
function Run-ProvisionStep([string]$Name,[string]$Executable,[string[]]$Argv,[int]$Seconds) {
    $remaining=[Math]::Floor(1800-$watch.Elapsed.TotalSeconds)
    if($remaining -lt 1){throw 'PROCESS_TIMEOUT_UNCONFIRMED: overall provisioning deadline exhausted.'}
    $result.Status=$Name+'_INTENT'
    Publish-GuestResult
    $run=Invoke-AIBSProvisionProcess -Executable $Executable -Arguments $Argv -TimeoutSeconds ([Math]::Min($Seconds,$remaining)) -OutputBytes 16384
    $result.Steps+=@{Name=$Name;PID=$run.PID;ExitCode=$run.ExitCode;Stdout=$run.Stdout;Stderr=$run.Stderr;ElapsedMilliseconds=$run.ElapsedMilliseconds}
    Publish-GuestResult
    Assert-AIBSInstallerExit $run.ExitCode
    return $run
}
try {
    # Pin the reviewed helper bytes; no caller-supplied helper/VM/destination override.
    $helperHashes=@{
        'Guest-ProvisioningPolicy.ps1'='87A1A05A0E317D182423ADC789C8A0FAA729614C218FA0D602C16BB24324B00E'
        'Guest-ProvisioningProcess.ps1'='2F83A4FBEF7064341604143F12084F47E71375AD1A7FA72D032E9FA7E369B8A2'
        'Guest-ProvisioningState.ps1'='2691A85C7592428122A50254DB9EA1F4B92B2DD502E15477ED0C2A7F0B07E8EB'
    }
    foreach($name in $helperHashes.Keys) {
        $path=Join-Path $PSScriptRoot $name
        Assert-RegularGuestPath $path
        if((Get-FileHash -LiteralPath $path -Algorithm SHA256).Hash -cne $helperHashes[$name]){throw 'Provisioning helper changed.'}
    }
    . (Join-Path $PSScriptRoot 'Guest-ProvisioningPolicy.ps1')
    . (Join-Path $PSScriptRoot 'Guest-ProvisioningProcess.ps1')
    . (Join-Path $PSScriptRoot 'Guest-ProvisioningState.ps1')
    $principal=New-Object Security.Principal.WindowsPrincipal($identity)
    $adapters=@(Get-CimInstance Win32_NetworkAdapter -ErrorAction Stop)
    Assert-AIBSGuestFacts @{
        UUID=[string]$product.UUID; Manufacturer=[string]$system.Manufacturer; Model=[string]$system.Model
        SID=$identity.User.Value;Elevated=$principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
        EnabledNICCount=@($adapters | Where-Object {$_.NetEnabled -eq $true}).Count
        Is64Bit=[Environment]::Is64BitProcess
    }
    $volumes=@(Get-CimInstance Win32_LogicalDisk -ErrorAction Stop | Where-Object {$_.DeviceID -ceq $MediaRoot.Substring(0,2)})
    if($volumes.Count -ne 1){throw 'Optical volume observation is ambiguous.'}
    Assert-AIBSGuestMedia $MediaRoot @{DeviceID=$volumes[0].DeviceID;DriveType=$volumes[0].DriveType;VolumeName=$volumes[0].VolumeName}
    $pins=@{
        'node-v24.22.1-x64.msi'='3BDA4BAF1EE709B33CF920DD633106DDB23951E322BFF9C03EC9F64AB8981B01'
        'python-3.13.17-amd64.exe'='5DA012101BA2E17113A9A1CD901E9CE1441086F2B7ECB5DE06EC94163899A190'
        'pywin32-312-cp313-cp313-win_amd64.whl'='C53E878D15A1C44788082BFE712A905433473AA38F86375B7CF8B45E3ACBAAF9'
        'psutil-7.2.2-cp37-abi3-win_amd64.whl'='EB7E81434C8D223EC4A219B5FC1C47D0417B12BE7EA866E24FB5AD6E84B3D988'
    }
    foreach($name in $pins.Keys) {
        $path=Join-Path $MediaRoot $name
        Assert-RegularGuestPath $path
        if((Get-FileHash -LiteralPath $path -Algorithm SHA256).Hash -cne $pins[$name]){throw 'Pinned offline package hash mismatch.'}
    }
    foreach($signed in @(
        @{Name='node-v24.22.1-x64.msi';Publisher='OpenJS Foundation'},
        @{Name='python-3.13.17-amd64.exe';Publisher='Python Software Foundation'}
    )) {
        $signature=Get-AuthenticodeSignature -LiteralPath (Join-Path $MediaRoot $signed.Name)
        if($signature.Status -ne 'Valid' -or -not $signature.SignerCertificate.Subject.Contains($signed.Publisher)) {
            throw 'Offline installer publisher verification failed.'
        }
    }
    # All identity/media checks above are read-only. First guest disk mutation starts here.
    $base='C:\AIBSGuestProvisioning'
    $attemptID=[Guid]::NewGuid().ToString('N')
    $provisionLease=Open-AIBSProvisionState $base $attemptID
    $attempt=Join-Path $base $attemptID
    if(Test-Path -LiteralPath $attempt){throw 'Provisioning attempt already exists.'}
    [IO.Directory]::CreateDirectory($attempt) | Out-Null
    $resultDir=$attempt
    $result.Status='PREFLIGHT_PASSED'
    Publish-GuestResult
    $node='C:\Program Files\nodejs\node.exe'
    $python='C:\Program Files\AIBSPython313\python.exe'
    $null=Run-ProvisionStep 'NODE_INSTALL' 'C:\Windows\System32\msiexec.exe' @('/i',(Join-Path $MediaRoot 'node-v24.22.1-x64.msi'),'/qn','/norestart','ALLUSERS=1','INSTALLDIR=C:\Program Files\nodejs') 600
    $null=Run-ProvisionStep 'PYTHON_INSTALL' (Join-Path $MediaRoot 'python-3.13.17-amd64.exe') @('/quiet','/norestart','InstallAllUsers=1','TargetDir=C:\Program Files\AIBSPython313','PrependPath=0','Include_launcher=0','Include_test=0','Include_pip=1','Shortcuts=0') 600
    Assert-RegularGuestPath $node
    Assert-RegularGuestPath $python
    $nodeReport=Run-ProvisionStep 'NODE_VERSION' $node @('--version') 15
    $pythonReport=Run-ProvisionStep 'PYTHON_VERSION' $python @('-I','--version') 15
    $null=Run-ProvisionStep 'WHEELS_INSTALL' $python @('-I','-m','pip','--isolated','--disable-pip-version-check','install','--no-index','--no-deps','--no-cache-dir',(Join-Path $MediaRoot 'pywin32-312-cp313-cp313-win_amd64.whl'),(Join-Path $MediaRoot 'psutil-7.2.2-cp37-abi3-win_amd64.whl')) 120
    $probe="import json, importlib.metadata as m; import psutil, win32api; print(json.dumps({'Pywin32':m.version('pywin32'),'Psutil':m.version('psutil'),'Imports':True}))"
    $imports=Run-ProvisionStep 'PACKAGE_VERSIONS_IMPORTS' $python @('-I','-c',$probe) 15
    $versions=$imports.Stdout | ConvertFrom-Json
    $report=@{Node=$nodeReport.Stdout.Trim();Python=$pythonReport.Stdout.Trim();Pywin32=$versions.Pywin32;Psutil=$versions.Psutil;Imports=$versions.Imports}
    Assert-AIBSRuntimeReport $report
    $result.Versions=$report
    $result.RuntimesVerified=$true
    $result.Status='RUNTIMES_VERIFIED_TASK_ADMISSION_DISABLED'
    $result.CompletedUTC=[DateTime]::UtcNow.ToString('o')
    Publish-GuestResult
    Write-Output "Guest runtime result directory: $resultDir"
    exit 0
} catch {
    $result.Error=$_.Exception.Message
    $result.Status='FAILED'
    if($result.Error -like 'PROCESS_*_UNCONFIRMED*'){$result.Quarantined=$true;$result.Status='QUARANTINED'}
    if($result.Error -like 'REBOOT_REQUIRED*'){$result.Status='REBOOT_REQUIRED'}
    $result.CompletedUTC=[DateTime]::UtcNow.ToString('o')
    try {Publish-GuestResult}catch{[Console]::Error.WriteLine('Durable result publication failed; provisioning is not verified.')}
    [Console]::Error.WriteLine($result.Error)
    exit 1
} finally {
    if($null -ne $provisionLease){$provisionLease.Dispose()}
    $watch.Stop()
}
