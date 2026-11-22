# Opens the existing VM manager only. Does not start, reset, restore or alter a VM.
# Passwords are entered only in the user's runas console; never stored here.
$ErrorActionPreference = 'Stop'
$workerSID = 'S-1-5-21-2133766663-4066672948-2456486318-1005'
$identity = [Security.Principal.WindowsIdentity]::GetCurrent()
$principal = New-Object Security.Principal.WindowsPrincipal($identity)
if ($identity.User.Value -ne $workerSID -or $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
    throw 'Open this manager only as the approved standard worker aibs_vm_worker.'
}
$integrity = & "$env:SystemRoot\System32\whoami.exe" /groups /fo csv /nh
if ($LASTEXITCODE -ne 0 -or ($integrity -join "`n") -notmatch 'S-1-16-8192') {
    throw 'Expected the medium-integrity worker session.'
}
$vmRegistry = 'C:\AI-BS\isolated_workers\windows\runtime\base_preparation_v2\vbox_config'
$manager = 'C:\Program Files\Oracle\VirtualBox\VirtualBox.exe'
foreach ($itemPath in @($vmRegistry, $manager)) {
    $entry = Get-Item -LiteralPath $itemPath -Force
    while ($null -ne $entry) {
        if ($entry.Attributes -band [IO.FileAttributes]::ReparsePoint) {
            throw 'Unexpected reparse point in manager or registry path.'
        }
        if ($entry -is [IO.FileInfo]) { $entry = $entry.Directory } else { $entry = $entry.Parent }
    }
}
if (-not (Test-Path -LiteralPath (Join-Path $vmRegistry 'VirtualBox.xml') -PathType Leaf)) {
    throw 'The existing worker VM registry is missing. Do not create a replacement.'
}
if ((Get-AuthenticodeSignature -LiteralPath $manager).Status -ne 'Valid') {
    throw 'The installed manager signature is not valid.'
}
$env:VBOX_USER_HOME = $vmRegistry
Start-Process -FilePath $manager -WorkingDirectory (Split-Path -Parent $manager) -WindowStyle Normal
Write-Host 'Existing worker VM manager requested. No virtual machine was started or changed.'
Write-Host 'Leave the manager open for Codex to verify the current state before recovery.'
