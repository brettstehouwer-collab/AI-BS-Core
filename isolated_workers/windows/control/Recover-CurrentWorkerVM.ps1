# One fixed setup recovery; no generated commands, guest input or acceptance claim.
[CmdletBinding()]
param([switch]$Recover,[switch]$ObserveRunning)
$ErrorActionPreference='Stop'
if ($Recover -and $ObserveRunning) { throw 'Select one fixed operation.' }
$identity=[Security.Principal.WindowsIdentity]::GetCurrent()
$principal=New-Object Security.Principal.WindowsPrincipal($identity)
if ($identity.User.Value -ne 'S-1-5-21-2133766663-4066672948-2456486318-1005' -or $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) { throw 'Run only in the existing standard aibs_vm_worker PowerShell session.' }
$groups=& "$env:SystemRoot\System32\whoami.exe" /groups /fo csv /nh
if ($LASTEXITCODE -ne 0 -or ($groups -join "`n") -notmatch 'S-1-16-8192') { throw 'Medium integrity required.' }
. "$PSScriptRoot\VM-RecoveryGuards.ps1"
$root='C:\AI-BS\isolated_workers\windows'
$base=Join-Path $root 'runtime\base_preparation_v2'
$vm='6c5a53da-ab80-4ecb-8be6-4059266f736e'
$disk='59e3fed5-5878-4524-8a70-9b0dc7a5067b'
$snapshot='73cdeb79-50d5-418b-810c-e38840094ea4'
$vbox='C:\Program Files\Oracle\VirtualBox\VBoxManage.exe'
$env:VBOX_USER_HOME=Join-Path $base 'vbox_config'
$out=if ($ObserveRunning) { Join-Path $root 'runtime\headless_recovery_observation_1' } elseif ($Recover) { Join-Path $root 'runtime\headless_recovery_1' } else { Join-Path $root ('runtime\recovery_preflight_'+[DateTime]::UtcNow.ToString('yyyyMMddTHHmmssfffffffZ')) }
foreach ($path in @($root,$base,$env:VBOX_USER_HOME,$vbox,$PSScriptRoot)) { Assert-RecoveryRegularPath $path }
$signature=Get-AuthenticodeSignature -LiteralPath $vbox
if ($signature.Status -ne 'Valid' -or $signature.SignerCertificate.Subject -notmatch 'O="?Oracle') { throw 'Valid Oracle signature required.' }
if (Test-Path -LiteralPath $out) { throw 'Attempt already recorded; no automatic replay. Return to Codex.' }
$null=New-Item -ItemType Directory -Path $out
$report=[ordered]@{State='PREFLIGHT';SID=$identity.User.Value;PID=$PID;VMUUID=$vm;StartedUTC=[DateTime]::UtcNow.ToString('o');Commands=@();BootRequested=$false;ContainmentAccepted=$false;GuestCommandsEnabled=$false;PasswordStored=$false}
$step=0
function Invoke-RecoveryVBox([string[]]$Arguments,[int]$Timeout=20000) {
    $script:step++
    $prefix=Join-Path $out ('vbox_{0:d2}' -f $script:step)
    $psi=New-Object Diagnostics.ProcessStartInfo
    $psi.FileName=$vbox; $psi.Arguments=($Arguments -join ' ')
    $psi.UseShellExecute=$false; $psi.CreateNoWindow=$true; $psi.RedirectStandardOutput=$true; $psi.RedirectStandardError=$true
    $p=New-Object Diagnostics.Process; $p.StartInfo=$psi; $null=$p.Start()
    $stdout=$p.StandardOutput.ReadToEndAsync(); $stderr=$p.StandardError.ReadToEndAsync()
    $timedOut=-not $p.WaitForExit($Timeout)
    if ($timedOut) { $p.Kill(); $null=$p.WaitForExit(5000) }
    $text=$stdout.GetAwaiter().GetResult(); $err=$stderr.GetAwaiter().GetResult()
    [IO.File]::WriteAllText("$prefix.stdout.txt",$text); [IO.File]::WriteAllText("$prefix.stderr.txt",$err)
    $report.Commands+=@{Arguments=$Arguments;ExitCode=$p.ExitCode;TimedOut=$timedOut}
    if ($timedOut -or $p.ExitCode -ne 0) { throw "VirtualBox operation $script:step failed; no automatic retry." }
    return $text
}
try {
    $current=ConvertFrom-RecoveryVMInfo (Invoke-RecoveryVBox @('showvminfo',$vm,'--machinereadable'))
    if ($ObserveRunning) {
        # Continue ONLY the independently reviewed first attempt; never start or restore here.
        $prior=Get-Content -LiteralPath (Join-Path $root 'runtime\headless_recovery_1\observation.json') -Raw | ConvertFrom-Json
        $child='cddcb90b-9ea3-42d2-90a5-49de79b7dc0e'
        $newSnapshot='afda1952-6c48-4086-9590-897c21323990'
        if ($prior.State -ne 'FAILED_REVIEW_REQUIRED' -or -not $prior.BootRequested -or $prior.RecoveryDisk -ne $child -or $prior.SafetySnapshot -ne $newSnapshot -or $prior.PreservedDisk -ne $disk -or $prior.VMUUID -ne $vm) { throw 'Reviewed running recovery identity differs.' }
        Assert-RecoveryVMInfo $current 'running' $child $newSnapshot
        $report.RecoveryDisk=$child; $report.SafetySnapshot=$newSnapshot; $report.PreservedDisk=$disk
        try {
            $null=Invoke-RecoveryVBox @('controlvm',$vm,'screenshotpng',(Join-Path $out 'screen_current.png'))
            $report.ScreenshotCaptured=$true
        } catch {
            # Display evidence failure must not skip the independent preservation step.
            $report.ScreenshotCaptured=$false; $report.ScreenshotError=$_.Exception.Message
        }
        Assert-RecoveryVMInfo (ConvertFrom-RecoveryVMInfo (Invoke-RecoveryVBox @('showvminfo',$vm,'--machinereadable'))) 'running' $child $newSnapshot
        $null=Invoke-RecoveryVBox @('controlvm',$vm,'savestate') 60000
        Assert-RecoveryVMInfo (ConvertFrom-RecoveryVMInfo (Invoke-RecoveryVBox @('showvminfo',$vm,'--machinereadable'))) 'saved' $child $newSnapshot
        $report.State='RECOVERY_SAVED_REVIEW_REQUIRED'
        return
    }
    Assert-RecoveryVMInfo $current 'aborted' $disk $snapshot
    foreach ($path in @($current.CfgFile,$current['SATA-0-0'],$current['SATA-1-0'])) { Assert-RecoveryRegularPath ($path.Replace('\\','\')) }
    $settings=New-Object Xml.XmlReaderSettings
    $settings.DtdProcessing=[Xml.DtdProcessing]::Prohibit; $settings.XmlResolver=$null
    $reader=[Xml.XmlReader]::Create($current.CfgFile.Replace('\\','\'),$settings)
    $xml=New-Object Xml.XmlDocument; $xml.XmlResolver=$null
    try { $xml.Load($reader) } finally { $reader.Dispose() }
    $hardware=$xml.SelectSingleNode('/*[local-name()="VirtualBox"]/*[local-name()="Machine"]/*[local-name()="Hardware"]')
    $tpm=$hardware.SelectSingleNode('./*[local-name()="TrustedPlatformModule"]')
    if ($null -eq $tpm -or $tpm.type -ne 'v2_0' -or $hardware.SelectNodes('.//*[local-name()="SharedFolder"]').Count) { throw 'Current TPM/sharing guard failed.' }
    if ((Get-FileHash -LiteralPath $current['SATA-1-0'].Replace('\\','\')).Hash -ne 'BC3F24086EBADC94489066B5AD78089E2CF5C3491E90E790BB81A2B199C10E38') { throw 'Installation media hash differs.' }
    $report.SettingsSHA256=(Get-FileHash -LiteralPath $current.CfgFile.Replace('\\','\')).Hash
    if (-not $Recover) { $report.State='PREFLIGHT_PASSED_NO_BOOT'; return }
    # Reserve a full64GiB child disk,8GiB saved RAM, and64GiB host headroom.
    if ((Get-PSDrive C).Free -lt 136GB) { throw 'Storage reserve below136GiB (64disk+8RAM+64host).' }
    # Never restore the historical snapshot: its saved hardware contains NAT.
    # A fresh cold snapshot preserves the current disk before any boot writes.
    $null=Invoke-RecoveryVBox @('snapshot',$vm,'take','AIBS_PreHeadlessRecovery_1','--description=Preserve_aborted_disk_before_fixed_recovery') 60000
    $after=ConvertFrom-RecoveryVMInfo (Invoke-RecoveryVBox @('showvminfo',$vm,'--machinereadable'))
    $child=$after['SATA-ImageUUID-0-0']; $newSnapshot=$after.CurrentSnapshotUUID
    if ($child -notmatch '^[0-9a-f-]{36}$' -or $newSnapshot -notmatch '^[0-9a-f-]{36}$' -or $child -eq $disk -or $newSnapshot -eq $snapshot) { throw 'New safety snapshot not established.' }
    $bootState=$after.VMState
    if ($bootState -notin @('aborted','poweroff')) { throw 'Safety snapshot did not leave the VM stopped.' }
    Assert-RecoveryVMInfo $after $bootState $child $newSnapshot
    $medium=Invoke-RecoveryVBox @('showmediuminfo','disk',$child)
    if ($medium -notmatch "(?m)^Parent UUID:\s+$disk\s*$") { throw 'Recovery disk parent differs.' }
    $report.PreservedDisk=$disk; $report.RecoveryDisk=$child; $report.SafetySnapshot=$newSnapshot
    Assert-RecoveryVMInfo (ConvertFrom-RecoveryVMInfo (Invoke-RecoveryVBox @('showvminfo',$vm,'--machinereadable'))) $bootState $child $newSnapshot
    $report.BootRequested=$true
    $null=Invoke-RecoveryVBox @('startvm','--type=headless',$vm) 60000
    $report.State='HEADLESS_BOOT_REQUESTED'
    foreach ($n in 1..3) {
        Start-Sleep -Seconds 15
        Assert-RecoveryVMInfo (ConvertFrom-RecoveryVMInfo (Invoke-RecoveryVBox @('showvminfo',$vm,'--machinereadable'))) 'running' $child $newSnapshot
        try {
            $null=Invoke-RecoveryVBox @('controlvm',$vm,'screenshotpng',(Join-Path $out "screen_$n.png"))
        } catch {
            $report.ScreenshotError=$_.Exception.Message
            # Stop optional observation, then preserve state; never repeat failed capture.
            break
        }
    }
    $null=Invoke-RecoveryVBox @('controlvm',$vm,'savestate') 60000
    Assert-RecoveryVMInfo (ConvertFrom-RecoveryVMInfo (Invoke-RecoveryVBox @('showvminfo',$vm,'--machinereadable'))) 'saved' $child $newSnapshot
    $report.State='RECOVERY_OBSERVED_SAVED_REVIEW_REQUIRED'
} catch {
    $report.State='FAILED_REVIEW_REQUIRED'; $report.Error=$_.Exception.Message; $report.GuestStateRequiresFreshQuery=$report.BootRequested
    throw
} finally {
    $report.FinishedUTC=[DateTime]::UtcNow.ToString('o')
    [IO.File]::WriteAllText((Join-Path $out 'observation.json'),($report | ConvertTo-Json -Depth 8))
    Write-Host "Recovery evidence: $out"
}
