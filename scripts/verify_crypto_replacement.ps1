$ErrorActionPreference = 'Stop'
$taskRoot = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..'))
$taskPython = Join-Path $taskRoot 'runtime\recovery-20261110\Scripts\python.exe'
$taskVerifier = Join-Path $taskRoot 'scripts\verify_crypto_replacement.py'
if ($taskRoot -ne 'C:\AI-BS' -or -not (Test-Path -LiteralPath $taskPython) -or -not (Test-Path -LiteralPath $taskVerifier)) {
    throw 'The AI-BS verifier and qualified Python runtime must exist in C:\AI-BS.'
}
$taskIdentity = [Security.Principal.WindowsIdentity]::GetCurrent()
$taskPrincipal = New-Object Security.Principal.WindowsPrincipal($taskIdentity)
if (-not $taskPrincipal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
    Write-Host 'Run this launcher from an Administrator terminal: the verifier binds the existing local_admin scope.'
    exit 2
}
Write-Host 'Crypto.com replacement-key verification: read-only probe; no orders or trial initialization.'
Write-Host 'Enter credentials here privately. They are passed only to this verification child process.'
$taskKey = $null; $taskSecret = $null
$taskKeyBuffer = [IntPtr]::Zero; $taskSecretBuffer = [IntPtr]::Zero
$taskChild = $null; $taskStart = $null; $taskExit = 1; $taskStarted = $false
try {
    $taskKey = Read-Host 'Replacement API key' -AsSecureString
    $taskSecret = Read-Host 'Replacement API secret' -AsSecureString
    if ($taskKey.Length -eq 0 -or $taskSecret.Length -eq 0) { throw 'Both replacement values are required.' }
    $taskKeyBuffer = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($taskKey)
    $taskSecretBuffer = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($taskSecret)
    $taskStart = New-Object Diagnostics.ProcessStartInfo
    $taskStart.FileName = $taskPython
    $taskTrial = [Guid]::NewGuid().ToString('D')
    $taskStart.Arguments = '-B "' + $taskVerifier + '" --probe-only --local-trial-uuid ' + $taskTrial
    $taskStart.WorkingDirectory = $taskRoot
    $taskStart.UseShellExecute = $false
    $taskStart.CreateNoWindow = $true
    $taskStart.RedirectStandardOutput = $true
    $taskStart.RedirectStandardError = $true
    $taskStart.EnvironmentVariables['REPLACEMENT_API_KEY'] = [Runtime.InteropServices.Marshal]::PtrToStringBSTR($taskKeyBuffer)
    $taskStart.EnvironmentVariables['REPLACEMENT_API_SECRET'] = [Runtime.InteropServices.Marshal]::PtrToStringBSTR($taskSecretBuffer)
    $taskChild = New-Object Diagnostics.Process
    $taskChild.StartInfo = $taskStart
    if (-not $taskChild.Start()) { throw 'Verification child did not start.' }
    $taskStarted = $true
    $taskStart.EnvironmentVariables.Remove('REPLACEMENT_API_KEY')
    $taskStart.EnvironmentVariables.Remove('REPLACEMENT_API_SECRET')
    $taskOutput = $taskChild.StandardOutput.ReadToEndAsync()
    $taskError = $taskChild.StandardError.ReadToEndAsync()
    if (-not $taskChild.WaitForExit(120000)) { throw 'Verification deadline reached.' }
    $taskExit = $taskChild.ExitCode
    $taskText = $taskOutput.GetAwaiter().GetResult()
    $taskDiagnostic = $taskError.GetAwaiter().GetResult()
    if ($taskText) { Write-Output $taskText }
    if ($taskDiagnostic) { Write-Output $taskDiagnostic }
} catch {
    Write-Host 'Verification did not finish. Any captured private evidence remains local.'
    $taskExit = 1
} finally {
    if ($taskChild) {
        try {
            if ($taskStarted -and -not $taskChild.HasExited) { $taskChild.Kill(); $taskChild.WaitForExit(10000) | Out-Null }
        } catch {
            # Child may already have exited; continue credential-buffer cleanup.
        } finally { $taskChild.Dispose() }
    }
    if ($taskStart) {
        $taskStart.EnvironmentVariables.Remove('REPLACEMENT_API_KEY')
        $taskStart.EnvironmentVariables.Remove('REPLACEMENT_API_SECRET')
    }
    if ($taskKeyBuffer -ne [IntPtr]::Zero) { [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($taskKeyBuffer) }
    if ($taskSecretBuffer -ne [IntPtr]::Zero) { [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($taskSecretBuffer) }
    if ($taskKey) { $taskKey.Dispose() }
    if ($taskSecret) { $taskSecret.Dispose() }
}
exit $taskExit
