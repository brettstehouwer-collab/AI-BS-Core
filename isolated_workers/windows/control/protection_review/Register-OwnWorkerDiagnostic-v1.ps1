# Run once from the existing host worker's authenticated, non-elevated shell.
# Registers a DISABLED diagnostic task only. Does not run an action or VM.
$ErrorActionPreference = 'Stop'
$env:PSModulePath = (Join-Path $PSHOME 'Modules') + ';' + (Join-Path $env:SystemRoot 'System32\WindowsPowerShell\v1.0\Modules')
$expectedSid = 'S-1-5-21-2133766663-4066672948-2456486318-1005'
$identity = [Security.Principal.WindowsIdentity]::GetCurrent()
$principal = New-Object Security.Principal.WindowsPrincipal($identity)
if ($identity.User.Value -cne $expectedSid -or $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator) -or -not [Environment]::Is64BitProcess) {
    throw 'AUTHENTICATED_STANDARD_HOST_WORKER_REQUIRED'
}
if (@($identity.Groups | Where-Object { $_.Value -in @('S-1-5-32-544', 'S-1-5-114') }).Count) {
    throw 'ADMINISTRATOR_MEMBERSHIP_REFUSED'
}
$taskName = 'AIBS_Phase4_WorkerPrerequisites_v1'
$entry = 'C:\ProgramData\AI-BS-WorkerControl\deployment\Worker-Prerequisites-v1.ps1'
$expectedHash = 'D70C69A657D109B377BB99F74E91D71CC7BEFA545512E0ABC83D1F6044CCDEA1'
$exe = 'C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe'
$arguments = '-NoProfile -NonInteractive -WindowStyle Hidden -ExecutionPolicy RemoteSigned -File "' + $entry + '"'
$receiptPath = 'C:\ProgramData\AI-BS-WorkerControl\incoming_outputs\self_registration_37c20e5e6fea43f5bbbf74ce4c48def5.json'
if ([IO.File]::Exists($receiptPath)) { throw 'EXISTING_RECEIPT_PRESERVED_NO_REPLAY' }
$sourceLock = [IO.File]::Open($entry, [IO.FileMode]::Open, [IO.FileAccess]::Read, [IO.FileShare]::Read)
try {
    $hash = [Security.Cryptography.SHA256]::Create()
    try { $actualHash = [BitConverter]::ToString($hash.ComputeHash($sourceLock)).Replace('-', '') } finally { $hash.Dispose() }
    if ($actualHash -cne $expectedHash) { throw 'PROTECTED_DIAGNOSTIC_HASH_MISMATCH' }
    $service = New-Object -ComObject Schedule.Service
    $service.Connect()
    $folder = $service.GetFolder('\')
    $existing = $null
    try { $existing = $folder.GetTask($taskName) } catch {
        $failure = $_.Exception
        while ($failure.InnerException) { $failure = $failure.InnerException }
        if ($failure.HResult -notin @(-2147024894, -2147216625)) { throw }
    }
    if ($null -ne $existing) { throw 'EXISTING_TASK_PRESERVED_NO_ADOPTION' }
    $definition = $service.NewTask(0)
    $definition.RegistrationInfo.Description = 'Disabled pending independent host review. Fixed worker identity/access diagnostics only.'
    $definition.Principal.UserId = $expectedSid
    $definition.Principal.LogonType = 2 # Same-account S4U, no password stored.
    $definition.Principal.RunLevel = 0 # Limited.
    $definition.Settings.Enabled = $false
    $definition.Settings.Hidden = $true
    $definition.Settings.AllowDemandStart = $true
    $definition.Settings.StartWhenAvailable = $false
    $definition.Settings.WakeToRun = $false
    $definition.Settings.MultipleInstances = 2
    $definition.Settings.RestartCount = 0
    $definition.Settings.ExecutionTimeLimit = 'PT1M'
    $definition.Settings.DisallowStartIfOnBatteries = $false
    $definition.Settings.StopIfGoingOnBatteries = $false
    $action = $definition.Actions.Create(0)
    $action.Path = $exe
    $action.Arguments = $arguments
    $action.WorkingDirectory = 'C:\ProgramData\AI-BS-WorkerControl\deployment'
    $sddl = 'D:P(A;;FA;;;SY)(A;;FA;;;BA)(A;;GRGX;;;' + $expectedSid + ')(A;;RC;;;OW)'
    # CREATE | DISABLE | DONT_ADD_PRINCIPAL_ACE. Never updates an existing task.
    $task = $folder.RegisterTaskDefinition($taskName, $definition, 26, $expectedSid, $null, 2, $sddl)
    if ($task.Enabled -or $task.Definition.Triggers.Count -ne 0) { throw 'DISABLED_DEMAND_ONLY_TASK_REQUIRED' }
    $receipt = [ordered]@{
        state = 'DISABLED_DIAGNOSTIC_REGISTERED_HOST_REVIEW_REQUIRED'
        utc = [DateTime]::UtcNow.ToString('o')
        task_name = $taskName
        worker_sid = $expectedSid
        entry_sha256 = $actualHash
        same_account_registration = $true
        password_supplied = $false
        task_enabled = [bool]$task.Enabled
        task_run_requested = $false
        worker_admitted = $false
        execution_authorized = $false
        apply_authorized = $false
        verification_status = 'not_run'
    }
    $bytes = [Text.Encoding]::UTF8.GetBytes(($receipt | ConvertTo-Json -Depth 4))
    $stream = [IO.File]::Open($receiptPath, [IO.FileMode]::CreateNew, [IO.FileAccess]::Write, [IO.FileShare]::None)
    try { $stream.Write($bytes, 0, $bytes.Length); $stream.Flush($true) } finally { $stream.Dispose() }
    $receipt | ConvertTo-Json -Depth 4
} finally { $sourceLock.Dispose() }
