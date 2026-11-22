param(
    [ValidateSet('Initial','ColdBootAfterFirmwareStall','RestoreInstallerAfterSnapshot')]
    [string]$Attempt='Initial'
)
$ErrorActionPreference='Stop'
$root='C:\AI-BS\isolated_workers\windows'
$base=Join-Path $root 'runtime\base_preparation_v2'
$vmUUID='6c5a53da-ab80-4ecb-8be6-4059266f736e'
$runtime=Join-Path $root 'runtime\first_setup_boot'
if ($Attempt -eq 'ColdBootAfterFirmwareStall') { $runtime=Join-Path $root 'runtime\cold_setup_boot_1' }
if ($Attempt -eq 'RestoreInstallerAfterSnapshot') { $runtime=Join-Path $root 'runtime\snapshot_installer_recovery_1' }
$progress=Join-Path $runtime 'progress.json'
$vbox='C:\Program Files\Oracle\VirtualBox\VBoxManage.exe'
$vmName='AI-BS-Eval-Base-20261023'
$step=0
$bootRequested=$false
$ownsAttempt=$false
function Assert-OriginalBootRecord($record,[string]$expectedVM) {
    if ($null -eq $record -or $record.State -ne 'SETUP_GUI_REQUESTED' -or $record.VMUUID -ne $expectedVM) {
        throw 'Expected original setup identity missing. Stop for review.'
    }
}
function ConvertFrom-VMInfo([string]$text) {
    $values=@{}
    foreach ($line in ($text -split "`r?`n")) {
        if ($line -match '^("[^"]+"|[^=]+)=(.*)$') { $values[$matches[1].Trim('"')]=$matches[2].Trim('"') }
    }
    return $values
}
function Test-ExactVMPath([string]$reported,[string]$approved) {
    if ([string]::IsNullOrWhiteSpace($reported)) { return $false }
    $path=[IO.Path]::GetFullPath($reported.Replace('\\','\').Replace('/','\'))
    return [string]::Equals($path,[IO.Path]::GetFullPath($approved),[StringComparison]::OrdinalIgnoreCase)
}
function Assert-RegularVMFile([string]$path) {
    $node=Get-Item -LiteralPath $path -Force
    if ($node.PSIsContainer) { throw 'Expected a regular media file.' }
    while ($null -ne $node) {
        if ($node.Attributes -band [IO.FileAttributes]::ReparsePoint) { throw 'Media path traverses a reparse point.' }
        if ($node -is [IO.FileInfo]) { $node=$node.Directory } else { $node=$node.Parent }
    }
}
try {
    $identity=[Security.Principal.WindowsIdentity]::GetCurrent()
    $principal=New-Object Security.Principal.WindowsPrincipal($identity)
    if ($identity.User.Value -ne 'S-1-5-21-2133766663-4066672948-2456486318-1005' -or $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) { throw 'Start only as the approved standard worker.' }
    $groups=& "$env:SystemRoot\System32\whoami.exe" /groups /fo csv /nh
    if ($LASTEXITCODE -ne 0 -or ($groups -join "`n") -notmatch 'S-1-16-8192') { throw 'Expected medium-integrity worker.' }
    if ($Attempt -ne 'Initial') {
        $original=Get-Content -LiteralPath (Join-Path $root 'runtime\first_setup_boot\progress.json') -Raw | ConvertFrom-Json
        Assert-OriginalBootRecord $original $vmUUID
    }
    if (Test-Path -LiteralPath $runtime) { throw 'A first-boot record already exists. Return to Codex; do not replay.' }
    if ((Get-PSDrive C).Free -lt (80GB+64GB)) { throw 'Insufficient host storage reserve.' }
    $readProbe=Join-Path $root 'runtime\vm_state_verification_1'
    if (-not (Test-Path -LiteralPath $readProbe)) {
        & (Join-Path $root 'control\Read-OfflineVMState.ps1')
        if (-not $?) { throw 'Fresh VM state collection failed.' }
    }
    $probeStatus=Get-Content -LiteralPath (Join-Path $readProbe 'progress.json') -Raw | ConvertFrom-Json
    if ($probeStatus.State -ne 'READ_ONLY_PROBE_COMPLETE') { throw 'Incomplete read-only VM inspection. Stop for reconciliation.' }
    $readResults=@(Get-ChildItem -LiteralPath $readProbe -Filter '*.result.json')
    if ($readResults.Count -ne 3) { throw 'Missing VM inspection command records.' }
    foreach ($resultPath in $readResults) {
        $result=Get-Content -LiteralPath $resultPath.FullName -Raw | ConvertFrom-Json
        if ($null -eq $result.ExitCode -or $result.ExitCode -ne 0 -or $result.TimedOut) { throw 'VM inspection did not succeed.' }
    }
    $tokens=$null
    $errors=$null
    $ast=[Management.Automation.Language.Parser]::ParseFile((Join-Path $root 'control\Prepare-OfflineVM.ps1'),[ref]$tokens,[ref]$errors)
    if ($errors.Count) { throw 'Process helper syntax failure.' }
    $functions=@($ast.FindAll({param($node) $node -is [Management.Automation.Language.FunctionDefinitionAst] -and $node.Name -in @('Save-Progress','Invoke-VBox')},$true))
    if ($functions.Count -ne 2) { throw 'Process helpers missing.' }
    foreach ($function in $functions) { Invoke-Expression $function.Extent.Text }
    $null=New-Item -ItemType Directory -Path $runtime
    $ownsAttempt=$true
    $env:VBOX_USER_HOME=Join-Path $base 'vbox_config'
    # Query again immediately before boot; retained status alone never authorizes boot.
    $current=Invoke-VBox @('showvminfo',$vmUUID,'--machinereadable')
    $settings=ConvertFrom-VMInfo $current
    $expected=@{UUID=$vmUUID;VMState='poweroff';memory='8192';cpus='4';firmware='EFI';SecureBoot='on';clipboard='disabled';clipboard_file_transfers='off';draganddrop='disabled';usb='off';ehci='off';xhci='off';audio='none';audio_in='off';audio_out='off';vrde='off';accelerate3d='off';boot1='dvd';boot2='disk'}
    $expected['storagecontrollername0']='SATA'
    $expected['storagecontrollertype0']='IntelAhci'
    $expected['storagecontrollerportcount0']='2'
    foreach ($number in 1..8) { $expected["nic$number"]='none' }
    foreach ($key in $expected.Keys) { if ($settings[$key] -cne $expected[$key]) { throw "Unexpected VM setting $key. Guest not started." } }
    if (@($settings.Keys | Where-Object { $_ -match '^storagecontrollername\d+$' }).Count -ne 1 -or @($settings.Keys | Where-Object { $_ -match '^SATA-\d+-\d+$' }).Count -ne 2) { throw 'Unexpected additional storage attachment.' }
    if (@($settings.Keys | Where-Object { $_ -match 'SharedFolderName' }).Count) { throw 'Shared folders are forbidden.' }
    $baseDisk=Join-Path $base 'vms\AI-BS-Eval-Base-20261023\system.vdi'
    $disk=$baseDisk
    if ($Attempt -eq 'RestoreInstallerAfterSnapshot') { $disk=Join-Path $base 'vms\AI-BS-Eval-Base-20261023\Snapshots\{a33ecdc9-9aa5-46d4-b99e-5cd44ef2f721}.vdi' }
    $iso='C:\Users\footb\Downloads\26300.9457.260913-1737.26h2_ge_release_svc_refresh_CLIENTENTERPRISEEVAL_OEMRET_x64FRE_en-us.iso'
    if (-not (Test-ExactVMPath $settings['SATA-0-0'] $disk)) { throw 'Unexpected attached storage.' }
    $dvdMatches=Test-ExactVMPath $settings['SATA-1-0'] $iso
    $knownAdditions='C:\Program Files\Oracle\VirtualBox\VBoxGuestAdditions.iso'
    if (-not $dvdMatches -and ($Attempt -ne 'RestoreInstallerAfterSnapshot' -or -not (Test-ExactVMPath $settings['SATA-1-0'] $knownAdditions))) { throw 'Unexpected attached storage.' }
    foreach ($mediaPath in @($disk,$baseDisk,$iso)) { Assert-RegularVMFile $mediaPath }
    if ((Get-FileHash -LiteralPath $iso -Algorithm SHA256).Hash -ne 'BC3F24086EBADC94489066B5AD78089E2CF5C3491E90E790BB81A2B199C10E38') { throw 'ISO content changed.' }
    $machinePath=Join-Path $base 'vms\AI-BS-Eval-Base-20261023\AI-BS-Eval-Base-20261023.vbox'
    if ((Get-Item -LiteralPath $machinePath).Length -gt 131072) { throw 'Oversized VM settings.' }
    $readerSettings=New-Object Xml.XmlReaderSettings
    $readerSettings.DtdProcessing=[Xml.DtdProcessing]::Prohibit
    $readerSettings.XmlResolver=$null
    $reader=[Xml.XmlReader]::Create($machinePath,$readerSettings)
    $xml=New-Object Xml.XmlDocument
    $xml.XmlResolver=$null
    try { $xml.Load($reader) } finally { $reader.Dispose() }
    $machine=$xml.SelectSingleNode('/*[local-name()="VirtualBox"]/*[local-name()="Machine"]')
    $tpm=$machine.SelectSingleNode('./*[local-name()="Hardware"]/*[local-name()="TrustedPlatformModule"]')
    if ($null -eq $tpm -or $tpm.type -ne 'v2_0') { throw 'TPM2 configuration missing.' }
    if ($xml.SelectNodes('//*[local-name()="SharedFolder"]').Count) { throw 'Shared folder XML detected.' }
    $medium=Invoke-VBox @('showmediuminfo','disk',$disk)
    if ($medium -notmatch '(?m)^Capacity:\s+65536\s+MBytes\s*$') { throw '64-GB virtual disk capacity not verified.' }
    if ($Attempt -eq 'RestoreInstallerAfterSnapshot') {
        if ($machine.currentSnapshot -ne '{5dd088ca-9939-4c13-b285-8eb7b54d8f1c}') { throw 'Snapshot identity changed; stop for review.' }
        if ($settings['SATA-ImageUUID-0-0'] -ne 'a33ecdc9-9aa5-46d4-b99e-5cd44ef2f721') { throw 'Unexpected active disk UUID.' }
        if ($medium -notmatch '(?m)^UUID:\s+a33ecdc9-9aa5-46d4-b99e-5cd44ef2f721\s*$' -or $medium -notmatch '(?m)^Parent UUID:\s+3f632eb6-4348-4aaa-a21d-12b9fdb0f99a\s*$') { throw 'Snapshot disk parent chain differs from the admitted base.' }
        $parent=Invoke-VBox @('showmediuminfo','disk',$baseDisk)
        if ($parent -notmatch '(?m)^UUID:\s+3f632eb6-4348-4aaa-a21d-12b9fdb0f99a\s*$' -or $parent -notmatch '(?m)^Parent UUID:\s+base\s*$') { throw 'Base disk identity changed.' }
        if (-not $dvdMatches) {
            # Repair only the installation DVD; preserve the active snapshot disk.
            $null=Invoke-VBox @('storageattach',$vmUUID,'--storagectl=SATA','--port=1','--device=0','--type=dvddrive',"--medium=$iso",'--passthrough=off')
        }
        $current=Invoke-VBox @('showvminfo',$vmUUID,'--machinereadable')
        $settings=ConvertFrom-VMInfo $current
        foreach ($key in $expected.Keys) { if ($settings[$key] -cne $expected[$key]) { throw "VM setting changed during DVD recovery: $key" } }
        if (@($settings.Keys | Where-Object { $_ -match '^storagecontrollername\d+$' }).Count -ne 1 -or @($settings.Keys | Where-Object { $_ -match '^SATA-\d+-\d+$' }).Count -ne 2) { throw 'Additional storage detected after recovery.' }
        if (-not (Test-ExactVMPath $settings['SATA-0-0'] $disk) -or -not (Test-ExactVMPath $settings['SATA-1-0'] $iso)) { throw 'Reattached storage did not match the admitted media.' }
    }
    [IO.File]::WriteAllText((Join-Path $runtime 'preboot_vm_info.txt'),$current)
    Save-Progress 'BOOT_INTENT' 'Open official Windows installer for human review only; no license acceptance or network enablement.'
    $bootRequested=$true
    $null=Invoke-VBox @('startvm','--type=gui',$vmUUID)
    [ordered]@{State='SETUP_GUI_REQUESTED';VMUUID=$vmUUID;PID=$PID;AcceptedWindowsTerms=$false;NetworkEnabled=$false;TaskExecutionEnabled=$false;TimestampUTC=[DateTime]::UtcNow.ToString('o')} | ConvertTo-Json | Set-Content -LiteralPath $progress -Encoding UTF8
    Write-Host 'Windows Setup requested. If prompted, click inside the VM and press a key to boot the DVD.' -ForegroundColor Green
    Write-Host 'Review the Windows evaluation/license terms yourself. Do not enter personal account credentials yet.'
    Write-Host 'Tell Codex what screen appears. Do not enable networking or bypass setup requirements.'
} catch {
    Write-Host $_.Exception.Message -ForegroundColor Red
    if ($ownsAttempt) {
        $detail=$_.Exception.Message
        $detail | Set-Content -LiteralPath (Join-Path $runtime 'setup_error.txt') -Encoding UTF8
        [ordered]@{State='FAILED_REVIEW_REQUIRED';Detail=$detail;VMUUID=$vmUUID;PID=$PID;BootRequested=$bootRequested;GuestStateRequiresFreshQuery=$bootRequested;TimestampUTC=[DateTime]::UtcNow.ToString('o')} | ConvertTo-Json | Set-Content -LiteralPath $progress -Encoding UTF8
    }
    Write-Host 'Stop here and return to Codex. Preserve the existing VM and all logs.'
} finally {
    Read-Host 'Press Enter to close this launcher window' | Out-Null
}
