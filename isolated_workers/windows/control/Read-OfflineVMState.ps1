$ErrorActionPreference = 'Stop'
$root = 'C:\AI-BS\isolated_workers\windows'
$base = Join-Path $root 'runtime\base_preparation_v2'
$runtime = Join-Path $root 'runtime\vm_state_verification_1'
$progress = Join-Path $runtime 'progress.json'
$vbox = 'C:\Program Files\Oracle\VirtualBox\VBoxManage.exe'
$vmUUID = '6c5a53da-ab80-4ecb-8be6-4059266f736e'
$vmName = 'AI-BS-Eval-Base-20261023'
$step = 0
try {
    $identity = [Security.Principal.WindowsIdentity]::GetCurrent()
    $principal = New-Object Security.Principal.WindowsPrincipal($identity)
    if ($identity.User.Value -ne 'S-1-5-21-2133766663-4066672948-2456486318-1005' -or $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) { throw 'Expected standard worker identity required.' }
    if (Test-Path -LiteralPath $runtime) { throw 'Read-only probe already has retained results; do not repeat.' }
    $null = New-Item -ItemType Directory -Path $runtime
    # Reuse only the two previously verified process helpers, not the setup body.
    $tokens=$null
    $errors=$null
    $ast=[Management.Automation.Language.Parser]::ParseFile((Join-Path $root 'control\Prepare-OfflineVM.ps1'),[ref]$tokens,[ref]$errors)
    if ($errors.Count -ne 0) { throw 'Trusted process helper syntax failed.' }
    $functions=@($ast.FindAll({param($node) $node -is [Management.Automation.Language.FunctionDefinitionAst] -and $node.Name -in @('Save-Progress','Invoke-VBox')},$true))
    if ($functions.Count -ne 2) { throw 'Expected process helper definitions missing.' }
    foreach ($function in $functions) { Invoke-Expression $function.Extent.Text }
    $env:VBOX_USER_HOME=Join-Path $base 'vbox_config'
    $info=Invoke-VBox @('showvminfo',$vmUUID,'--machinereadable')
    [IO.File]::WriteAllText((Join-Path $runtime 'current_vm_info.txt'),$info)
    $disk=Join-Path $base 'vms\AI-BS-Eval-Base-20261023\system.vdi'
    $medium=Invoke-VBox @('showmediuminfo','disk',$disk)
    [IO.File]::WriteAllText((Join-Path $runtime 'current_medium_info.txt'),$medium)
    $nvram=Invoke-VBox @('modifynvram',$vmUUID,'listvars')
    [IO.File]::WriteAllText((Join-Path $runtime 'current_nvram_vars.txt'),$nvram)
    Save-Progress 'READ_ONLY_PROBE_COMPLETE' 'No guest boot or VM configuration command issued.'
} catch {
    if (Test-Path -LiteralPath $runtime) {
        $_.Exception.Message | Set-Content -LiteralPath (Join-Path $runtime 'probe_error.txt') -Encoding UTF8
    }
    exit 1
}
