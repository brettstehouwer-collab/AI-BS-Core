# Authenticated operator launches this once in the existing standard worker session.
# This is a setup UI channel, NOT the generated-code execution/transport controller.
[CmdletBinding()]
param()
$ErrorActionPreference='Stop'
$worker='S-1-5-21-2133766663-4066672948-2456486318-1005'
$operator='S-1-5-21-2133766663-4066672948-2456486318-1001'
$identity=[Security.Principal.WindowsIdentity]::GetCurrent()
$principal=New-Object Security.Principal.WindowsPrincipal($identity)
if($identity.User.Value -ne $worker -or $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)){throw 'Start only as the existing standard aibs_vm_worker account.'}
$groups=& "$env:SystemRoot\System32\whoami.exe" /groups /fo csv /nh
if($LASTEXITCODE -ne 0 -or ($groups -join "`n") -notmatch 'S-1-16-8192'){throw 'Medium integrity required.'}
. "$PSScriptRoot\VM-RecoveryGuards.ps1"
. "$PSScriptRoot\VM-SetupProtocol.ps1"
. "$PSScriptRoot\VM-SetupStatus.ps1"
$root='C:\AI-BS\isolated_workers\windows'
$vm='6c5a53da-ab80-4ecb-8be6-4059266f736e'
$disk='cddcb90b-9ea3-42d2-90a5-49de79b7dc0e'
$snapshot='afda1952-6c48-4086-9590-897c21323990'
$vbox='C:\Program Files\Oracle\VirtualBox\VBoxManage.exe'
$env:VBOX_USER_HOME=Join-Path $root 'runtime\base_preparation_v2\vbox_config'
foreach($name in @('AI_BS_RECDEBUT_OUTBOUND_ENABLED','AI_BS_RECDEBUT_INBOUND_POLLING_ENABLED','AI_BS_DISCORD_NOTIFICATIONS_ENABLED','AI_BS_BACKEND_MANAGE_DAEMONS','AI_BS_BACKEND_BACKGROUND_ENABLED','AI_BS_ALLOW_DESTRUCTIVE_ACTIONS')){[Environment]::SetEnvironmentVariable($name,'false','Process')}
foreach($p in @($root,$PSScriptRoot,$env:VBOX_USER_HOME,$vbox)){Assert-RecoveryRegularPath $p}
$sig=Get-AuthenticodeSignature -LiteralPath $vbox
if($sig.Status -ne 'Valid' -or $sig.SignerCertificate.Subject -notmatch 'O="?Oracle'){throw 'Signed Oracle executable required.'}
$sourceHashes=@{}
foreach($p in @($PSCommandPath,"$PSScriptRoot\VM-RecoveryGuards.ps1","$PSScriptRoot\VM-SetupProtocol.ps1","$PSScriptRoot\VM-SetupStatus.ps1")){$sourceHashes[$p]=(Get-FileHash -LiteralPath $p).Hash}
$leasePath=Join-Path $root 'runtime\setup_channel.lock'
Assert-RecoveryRegularPath (Split-Path $leasePath)
if(Test-Path -LiteralPath $leasePath){Assert-RecoveryRegularPath $leasePath}
$lease=[IO.File]::Open($leasePath,[IO.FileMode]::OpenOrCreate,[IO.FileAccess]::ReadWrite,[IO.FileShare]::None)
$session=[guid]::NewGuid().ToString('D')
$channel=Join-Path $root ("runtime\setup_channel_$session")
$null=New-Item -ItemType Directory -Path $channel
# Remove inherited access only on this NEW private channel directory.
$acl=Get-Acl -LiteralPath $channel
$acl.SetAccessRuleProtection($true,$false)
foreach($sid in @($worker,$operator,'S-1-5-18','S-1-5-32-544')){
    $rule=New-Object Security.AccessControl.FileSystemAccessRule((New-Object Security.Principal.SecurityIdentifier($sid)),'FullControl','ContainerInherit,ObjectInherit','None','Allow')
    $acl.AddAccessRule($rule)
}
Set-Acl -LiteralPath $channel -AclObject $acl
$started=[datetime]::UtcNow
$clock=[Diagnostics.Stopwatch]::StartNew()
$lastAction=$clock.Elapsed.TotalSeconds
$sequence=1;$step=0;$publication=0;$frameHash='';$frameTime=[datetime]::MinValue;$stop=$false;$validated=$false
$status=[ordered]@{State='STARTING';Session=$session;PID=$PID;ProcessCreationUTC=(Get-Process -Id $PID).StartTime.ToUniversalTime().ToString('o');SID=$worker;VMUUID=$vm;Disk=$disk;Snapshot=$snapshot;StartedUTC=$started.ToString('o');NextSequence=1;LastFrameSHA256='';Phase4Accepted=$false;GeneratedExecutionEnabled=$false;Commands=@()}
function Save-SetupStatus {
    $status.UpdatedUTC=[datetime]::UtcNow.ToString('o')
    $status.NextSequence=$script:sequence
    $status.LastFrameSHA256=$script:frameHash
    $status.FrameUTC=if($script:frameHash){$script:frameTime.ToString('o')}else{''}
    $script:publication++
    $null=Publish-ImmutableSetupStatus $channel $status $script:publication
}
function Invoke-SetupVBox([string[]]$Arguments,[int]$Timeout=20000){
    $script:step++
    $prefix=Join-Path $channel ('vbox_{0:d4}' -f $script:step)
    $psi=New-Object Diagnostics.ProcessStartInfo
    $psi.FileName=$vbox;$psi.Arguments=($Arguments -join ' ');$psi.UseShellExecute=$false;$psi.CreateNoWindow=$true
    $psi.RedirectStandardOutput=$true;$psi.RedirectStandardError=$true
    $p=New-Object Diagnostics.Process;$p.StartInfo=$psi;$null=$p.Start()
    $outTask=$p.StandardOutput.ReadToEndAsync();$errTask=$p.StandardError.ReadToEndAsync()
    $timeoutHit=-not $p.WaitForExit($Timeout)
    if($timeoutHit){$p.Kill();$null=$p.WaitForExit(5000)}
    $stdout=$outTask.GetAwaiter().GetResult();$stderr=$errTask.GetAwaiter().GetResult()
    [IO.File]::WriteAllText("$prefix.stdout.txt",$stdout);[IO.File]::WriteAllText("$prefix.stderr.txt",$stderr)
    $status.Commands+=@{Step=$script:step;Arguments=$Arguments;ExitCode=$p.ExitCode;TimedOut=$timeoutHit}
    if($timeoutHit -or $p.ExitCode -ne 0){throw "VBox operation $script:step failed; no replay."}
    return $stdout
}
function Read-SetupState {
    $v=ConvertFrom-RecoveryVMInfo (Invoke-SetupVBox @('showvminfo',$vm,'--machinereadable'))
    if($v.VMState -cnotin @('saved','running')){throw 'Expected saved or running setup VM.'}
    Assert-RecoveryVMInfo $v $v.VMState $disk $snapshot
    return $v
}
function Capture-SetupFrame {
    $v=Read-SetupState
    if($v.VMState -ne 'running'){throw 'Capture requires running VM.'}
    $image=Join-Path $channel ('frame_{0:d4}.png' -f $script:sequence)
    $null=Invoke-SetupVBox @('controlvm',$vm,'screenshotpng',$image)
    $script:frameHash=(Get-FileHash -LiteralPath $image).Hash.ToLowerInvariant()
    $script:frameTime=[datetime]::UtcNow
    $status.LastFramePath=$image
}
try{
    $prior=Get-Content -LiteralPath (Join-Path $root 'runtime\headless_recovery_observation_1\observation.json') -Raw | ConvertFrom-Json
    if($prior.State -ne 'RECOVERY_SAVED_REVIEW_REQUIRED' -or $prior.RecoveryDisk -ne $disk -or $prior.SafetySnapshot -ne $snapshot){throw 'Saved recovery receipt differs.'}
    $v=Read-SetupState
    if($v.VMState -ne 'saved'){throw 'New setup channel requires verified saved state.'}
    $validated=$true;$status.State='READY';Save-SetupStatus
    Write-Host "Worker setup channel: $channel"
    Write-Host 'Leave this window open. Only fixed VM resume/capture/save and frame-bound navigation keys are accepted.'
    while(-not $stop -and $sequence -le 128 -and $clock.Elapsed.TotalSeconds -lt 1200 -and ($clock.Elapsed.TotalSeconds-$lastAction) -lt 90){
        foreach($p in $sourceHashes.Keys){if((Get-FileHash -LiteralPath $p).Hash -ne $sourceHashes[$p]){throw 'Controller source changed; stop and preserve VM.'}}
        $requestPath=Join-Path $channel ('{0:d4}.request.json' -f $sequence)
        if(-not(Test-Path -LiteralPath $requestPath)){Save-SetupStatus;Start-Sleep -Milliseconds 1000;continue}
        Assert-RecoveryRegularPath $requestPath
        if((Get-Item -LiteralPath $requestPath).Length -gt 2048){throw 'Oversized request.'}
        $r=ConvertFrom-SetupRequest (Get-Content -LiteralPath $requestPath -Raw) $session $sequence $frameHash $frameTime ([datetime]::UtcNow)
        $intent=Join-Path $channel ('{0:d4}.intent.json' -f $sequence)
        # Exclusive durable intent before control action: no replay after uncertain execution.
        $bytes=[Text.Encoding]::UTF8.GetBytes(($r | ConvertTo-Json -Compress))
        $intentHandle=[IO.File]::Open($intent,[IO.FileMode]::CreateNew,[IO.FileAccess]::Write,[IO.FileShare]::Read)
        try{$intentHandle.Write($bytes,0,$bytes.Length);$intentHandle.Flush($true)}finally{$intentHandle.Dispose()}
        $v=Read-SetupState
        switch -CaseSensitive ($r.operation){
            'resume'{if($v.VMState -ne 'saved'){throw 'Resume requires saved VM.'};$null=Invoke-SetupVBox @('startvm','--type=headless',$vm) 60000;Start-Sleep -Seconds 3;Capture-SetupFrame}
            'capture'{Capture-SetupFrame}
            'key'{
                if($v.VMState -ne 'running'){throw 'Key requires running VM.'}
                # Require the visible pixels still match the reviewed frame immediately before input.
                $check=Join-Path $channel ('before_key_{0:d4}.png' -f $sequence)
                $null=Invoke-SetupVBox @('controlvm',$vm,'screenshotpng',$check)
                if((Get-FileHash -LiteralPath $check).Hash.ToLowerInvariant() -cne $frameHash){throw 'Screen changed; key not sent.'}
                $keyArgs=@('controlvm',$vm,'keyboardputscancode')+@(Get-SetupKeyScancodes $r.key)
                $null=Invoke-SetupVBox $keyArgs
                $script:frameHash='';Start-Sleep -Seconds 3;Capture-SetupFrame
            }
            'save'{if($v.VMState -ne 'running'){throw 'Save requires running VM.'};$null=Invoke-SetupVBox @('controlvm',$vm,'savestate') 60000;if((Read-SetupState).VMState -ne 'saved'){throw 'Save not confirmed.'};$stop=$true}
            'stop'{$stop=$true}
        }
        $status.LastOperation=$r.operation;$status.LastCompletedSequence=$sequence
        $sequence++;$lastAction=$clock.Elapsed.TotalSeconds
        $status.State='READY';Save-SetupStatus
    }
    $status.State='STOPPED'
}catch{
    $status.State='FAILED_REVIEW_REQUIRED';$status.Error=$_.Exception.Message
}finally{
    if($validated){
        try{
            $v=Read-SetupState
            if($v.VMState -eq 'running'){$null=Invoke-SetupVBox @('controlvm',$vm,'savestate') 60000}
            $status.FinalVMState=(Read-SetupState).VMState
            if($status.FinalVMState -ne 'saved'){throw 'Final saved state not confirmed.'}
        }catch{$status.PreservationError=$_.Exception.Message;$status.State='PRESERVATION_UNCONFIRMED'}
    }
    $status.FinishedUTC=[datetime]::UtcNow.ToString('o')
    try{Save-SetupStatus}finally{$lease.Dispose()}
    Write-Host "Setup channel ended: $($status.State). Evidence: $channel"
}
