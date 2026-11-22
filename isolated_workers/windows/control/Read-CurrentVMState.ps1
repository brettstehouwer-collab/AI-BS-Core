# Read-only current-state collection. No boot, recovery, policy change or credential storage.
$ErrorActionPreference = 'Stop'
$workerSID = 'S-1-5-21-2133766663-4066672948-2456486318-1005'
$identity = [Security.Principal.WindowsIdentity]::GetCurrent()
$principal = New-Object Security.Principal.WindowsPrincipal($identity)
if ($identity.User.Value -ne $workerSID -or $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
    throw 'Run this read-only inspection as the existing standard worker aibs_vm_worker.'
}
$root = 'C:\AI-BS\isolated_workers\windows'
$vbox = 'C:\Program Files\Oracle\VirtualBox\VBoxManage.exe'
$vmID = '6c5a53da-ab80-4ecb-8be6-4059266f736e'
$env:VBOX_USER_HOME = Join-Path $root 'runtime\base_preparation_v2\vbox_config'
$out = Join-Path $root ('runtime\current_inspection_' + [DateTime]::UtcNow.ToString('yyyyMMddTHHmmssfffffffZ'))
if ((Get-AuthenticodeSignature -LiteralPath $vbox).Status -ne 'Valid') { throw 'VirtualBox signature is not valid.' }
foreach ($target in @($root, $vbox, $env:VBOX_USER_HOME)) {
    $node = Get-Item -LiteralPath $target -Force
    while ($null -ne $node) {
        if ($node.Attributes -band [IO.FileAttributes]::ReparsePoint) { throw 'Linked path rejected.' }
        if ($node -is [IO.FileInfo]) { $node = $node.Directory } else { $node = $node.Parent }
    }
}
$null = New-Item -ItemType Directory -Path $out
$report = [ordered]@{ State='INSPECTING'; SID=$identity.User.Value; Administrator=$false; VMUUID=$vmID; Commands=@(); GuestStarted=$false; ConfigurationChanged=$false; PasswordStored=$false; TimestampUTC=[DateTime]::UtcNow.ToString('o') }
try {
    foreach ($operation in @('showvminfo', 'snapshot')) {
        $start = New-Object Diagnostics.ProcessStartInfo
        $start.FileName = $vbox
        $start.Arguments = if ($operation -eq 'showvminfo') { "showvminfo $vmID --machinereadable" } else { "snapshot $vmID list --machinereadable" }
        $start.UseShellExecute = $false
        $start.CreateNoWindow = $true
        $start.RedirectStandardOutput = $true
        $start.RedirectStandardError = $true
        $process = New-Object Diagnostics.Process
        $process.StartInfo = $start
        if (-not $process.Start()) { throw 'Inspection process failed to start.' }
        $stdout = $process.StandardOutput.ReadToEndAsync()
        $stderr = $process.StandardError.ReadToEndAsync()
        if (-not $process.WaitForExit(15000)) {
            $process.Kill()
            $null = $process.WaitForExit(5000)
            throw 'Inspection exceeded15seconds; preserve state before any retry.'
        }
        $text = $stdout.GetAwaiter().GetResult()
        $errorText = $stderr.GetAwaiter().GetResult()
        [IO.File]::WriteAllText((Join-Path $out ($operation + '.stdout.txt')), $text)
        [IO.File]::WriteAllText((Join-Path $out ($operation + '.stderr.txt')), $errorText)
        $report.Commands += [ordered]@{ Operation=$operation; ExitCode=$process.ExitCode; OutputBytes=[Text.Encoding]::UTF8.GetByteCount($text); ErrorBytes=[Text.Encoding]::UTF8.GetByteCount($errorText) }
        if ($process.ExitCode -ne 0 -or $text.Length -gt 1048576 -or $errorText.Length -gt 65536) { throw 'Inspection failed or output limit exceeded.' }
    }
    $report.State = 'READ_ONLY_CURRENT_STATE_COLLECTED'
} catch {
    $report.State = 'INSPECTION_FAILED'
    $report.Error = $_.Exception.Message
    throw
} finally {
    [IO.File]::WriteAllText((Join-Path $out 'observation.json'), ($report | ConvertTo-Json -Depth 5), (New-Object Text.UTF8Encoding($false)))
    Write-Host "Current VM evidence saved: $out"
    Write-Host 'No guest was started; no VM or account setting was changed.'
}
