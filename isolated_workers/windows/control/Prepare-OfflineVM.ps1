$ErrorActionPreference = 'Stop'
$root = 'C:\AI-BS\isolated_workers\windows'
$runtime = Join-Path $root 'runtime\base_preparation_v2'
$vbox = 'C:\Program Files\Oracle\VirtualBox\VBoxManage.exe'
$iso = 'C:\Users\footb\Downloads\26300.9457.260913-1737.26h2_ge_release_svc_refresh_CLIENTENTERPRISEEVAL_OEMRET_x64FRE_en-us.iso'
$isoHash = 'BC3F24086EBADC94489066B5AD78089E2CF5C3491E90E790BB81A2B199C10E38'
$vmName = 'AI-BS-Eval-Base-20261023'
$progress = Join-Path $runtime 'vm_preparation.json'
$vmUUID = $null
$step = 0
function Save-Progress([string]$state, [string]$detail) {
    [ordered]@{State=$state; Detail=$detail; VMName=$vmName; VMUUID=$vmUUID; Step=$step; PID=$PID; TimestampUTC=[DateTime]::UtcNow.ToString('o'); StartedGuest=$false; AcceptedWindowsTerms=$false} | ConvertTo-Json | Set-Content -LiteralPath $progress -Encoding UTF8
}
function Invoke-VBox([string[]]$VBoxArguments) {
    $script:step++
    $stdout = Join-Path $runtime ('vbox_{0:D2}.stdout.txt' -f $script:step)
    $stderr = Join-Path $runtime ('vbox_{0:D2}.stderr.txt' -f $script:step)
    Save-Progress 'PREPARING' ('VBoxManage ' + ($VBoxArguments -join ' '))
    # Every argument is fixed below; reject whitespace/quotes before passing to Windows.
    foreach ($argument in $VBoxArguments) { if ($argument -match '[\s"]') { throw 'Unexpected argument requiring quoting.' } }
    # Own the process handle directly; Start-Process lost the short-lived version
    # process's exit code on this host. Drain both pipes concurrently.
    $child = New-Object Diagnostics.Process
    $child.StartInfo.FileName = $vbox
    $child.StartInfo.Arguments = $VBoxArguments -join ' '
    $child.StartInfo.UseShellExecute = $false
    $child.StartInfo.CreateNoWindow = $true
    $child.StartInfo.RedirectStandardOutput = $true
    $child.StartInfo.RedirectStandardError = $true
    $timedOut = $false
    try {
        if (-not $child.Start()) { throw 'Could not start VBoxManage.' }
        $stdoutTask = $child.StandardOutput.ReadToEndAsync()
        $stderrTask = $child.StandardError.ReadToEndAsync()
        if (-not $child.WaitForExit(120000)) {
            $timedOut = $true
            $child.Kill()
            if (-not $child.WaitForExit(5000)) { throw 'VBoxManage termination is unconfirmed. Inspect retained state.' }
        }
        if (-not [Threading.Tasks.Task]::WaitAll([Threading.Tasks.Task[]]@($stdoutTask,$stderrTask),5000)) { throw 'VBoxManage output collection did not finish. Inspect retained state.' }
        $outText = $stdoutTask.GetAwaiter().GetResult()
        $errText = $stderrTask.GetAwaiter().GetResult()
        [IO.File]::WriteAllText($stdout,$outText)
        [IO.File]::WriteAllText($stderr,$errText)
        $exitCode = $child.ExitCode
        [ordered]@{Arguments=$VBoxArguments;PID=$child.Id;ExitCode=$exitCode;TimedOut=$timedOut;TimestampUTC=[DateTime]::UtcNow.ToString('o')} | ConvertTo-Json -Depth 3 | Set-Content -LiteralPath (Join-Path $runtime ('vbox_{0:D2}.result.json' -f $script:step)) -Encoding UTF8
        if ($timedOut) { throw 'VBoxManage exceeded its preparation deadline. Inspect retained state before retrying.' }
        if ($exitCode -ne 0) { throw "VBoxManage step $script:step failed with exit code $exitCode. See retained stdout/stderr." }
        return $outText
    } finally {
        $child.Dispose()
    }
}
try {
    $identity = [Security.Principal.WindowsIdentity]::GetCurrent()
    $principal = New-Object Security.Principal.WindowsPrincipal($identity)
    if ($identity.User.Value -ne 'S-1-5-21-2133766663-4066672948-2456486318-1005' -or $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) { throw 'Must run as the approved standard worker, never as administrator.' }
    $groups = & "$env:SystemRoot\System32\whoami.exe" /groups /fo csv /nh
    if ($LASTEXITCODE -ne 0 -or ($groups -join "`n") -notmatch 'S-1-16-8192') { throw 'Medium-integrity worker required.' }
    if (Test-Path -LiteralPath $progress) { throw 'Preparation record already exists. Return to Codex for reconciliation; do not repeat VM creation.' }
    if ((Get-PSDrive C).Free -lt (80GB + 64GB)) { throw 'Insufficient space to reserve a 64-GB disk and 80-GB host margin.' }
    if ((Get-FileHash -LiteralPath $iso -Algorithm SHA256).Hash -ne $isoHash) { throw 'Evaluation media hash mismatch or media unreadable.' }
    $env:VBOX_USER_HOME = Join-Path $runtime 'vbox_config'
    if (Test-Path -LiteralPath $env:VBOX_USER_HOME) { throw 'VM registry already exists; inspect before proceeding.' }
    $vmBase = Join-Path $runtime 'vms'
    if (Test-Path -LiteralPath $vmBase) { throw 'VM storage already exists; inspect before proceeding.' }
    $null = New-Item -ItemType Directory -Path $env:VBOX_USER_HOME
    $null = New-Item -ItemType Directory -Path $vmBase
    $version = (Invoke-VBox @('--version')).Trim()
    if ($version -ne '7.2.22r175245') { throw 'Unexpected VirtualBox version.' }
    $vmUUID = [guid]::NewGuid().ToString()
    Save-Progress 'CREATE_INTENT' 'Creating one powered-off base VM; no guest boot or license acceptance.'
    $null = Invoke-VBox @('createvm',"--name=$vmName",'--platform-architecture=x86',"--basefolder=$vmBase",'--ostype=Windows11_64',"--uuid=$vmUUID",'--register')
    $settings = @('modifyvm',$vmUUID,'--memory=8192','--cpus=4','--acpi=on','--ioapic=on','--firmware=efi','--tpm-type=2.0','--graphicscontroller=vboxsvga','--accelerate-3d=off','--vram=128','--mouse=ps2','--keyboard=ps2','--clipboard-mode=disabled','--clipboard-file-transfers=disabled','--drag-and-drop=disabled','--usb-ohci=off','--usb-ehci=off','--usb-xhci=off','--usb-card-reader=off','--audio-enabled=off','--audio-in=off','--audio-out=off','--vrde=off','--boot1=dvd','--boot2=disk','--boot3=none','--boot4=none')
    foreach ($number in 1..8) { $settings += "--nic$number=none" }
    $null = Invoke-VBox $settings
    $null = Invoke-VBox @('modifynvram',$vmUUID,'inituefivarstore')
    $null = Invoke-VBox @('modifynvram',$vmUUID,'enrollmssignatures')
    $null = Invoke-VBox @('modifynvram',$vmUUID,'enrollorclpk')
    $null = Invoke-VBox @('modifynvram',$vmUUID,'secureboot','--enable')
    $diskPath = Join-Path (Join-Path $vmBase $vmName) 'system.vdi'
    $null = Invoke-VBox @('createmedium','disk',"--filename=$diskPath",'--size=65536','--format=VDI','--variant=Standard')
    $null = Invoke-VBox @('storagectl',$vmUUID,'--name=SATA','--add=sata','--controller=IntelAhci','--portcount=2','--bootable=on')
    $null = Invoke-VBox @('storageattach',$vmUUID,'--storagectl=SATA','--port=0','--device=0','--type=hdd',"--medium=$diskPath",'--nonrotational=on')
    $null = Invoke-VBox @('storageattach',$vmUUID,'--storagectl=SATA','--port=1','--device=0','--type=dvddrive',"--medium=$iso",'--passthrough=off')
    $machineInfo = Invoke-VBox @('showvminfo',$vmUUID,'--machinereadable')
    [IO.File]::WriteAllText((Join-Path $runtime 'prepared_vm_info.txt'),$machineInfo)
    Save-Progress 'PREPARED_AWAITING_HOST_VERIFICATION' 'Powered-off VM only. Host must inspect actual configuration before first boot. No Windows terms accepted.'
    Write-Host 'Powered-off VM prepared. Return to Codex; leave this window open for verification.' -ForegroundColor Green
} catch {
    if (-not (Test-Path -LiteralPath $progress)) { Save-Progress 'FAILED_BEFORE_CREATION' $_.Exception.Message }
    else {
        $existing = Get-Content -LiteralPath $progress -Raw | ConvertFrom-Json
        # Never overwrite a previous run's task identity when a repeated launch is refused.
        if ($existing.PID -eq $PID) { Save-Progress 'FAILED_REVIEW_REQUIRED' $_.Exception.Message }
    }
    Write-Host $_.Exception.Message -ForegroundColor Red
    Write-Host 'Stopped without starting a guest. Preserve all files and return to Codex.'
} finally {
    Read-Host 'Press Enter only after Codex verifies preparation' | Out-Null
}
