# Trusted provisioning processes only. This is not a task executor or containment boundary.
function ConvertTo-AIBSNativeArgument([string]$Value) {
    if ($null -eq $Value -or $Value -match '["\x00\r\n]') {throw 'Unsafe provisioning argument.'}
    # No embedded quotes are allowed. Escape trailing slashes before the closing quote.
    return '"' + [regex]::Replace($Value,'(\\+)$','$1$1') + '"'
}

function Invoke-AIBSProvisionProcess {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory=$true)][string]$Executable,
        [Parameter(Mandatory=$true)][AllowEmptyCollection()][string[]]$Arguments,
        [ValidateRange(1,900)][int]$TimeoutSeconds=30,
        [ValidateRange(128,65536)][int]$OutputBytes=16384
    )
    if (-not [IO.Path]::IsPathRooted($Executable) -or
        [IO.Path]::GetExtension($Executable) -ine '.exe' -or
        $Executable -match '["\x00\r\n]') {throw 'Expected a fixed absolute native executable.'}
    $quoted=@($Arguments | ForEach-Object {ConvertTo-AIBSNativeArgument $_})
    $start=New-Object Diagnostics.ProcessStartInfo
    $start.FileName=$Executable
    $start.Arguments=$quoted -join ' '
    $start.UseShellExecute=$false
    $start.CreateNoWindow=$true
    $start.RedirectStandardOutput=$true
    $start.RedirectStandardError=$true
    foreach($key in @('PYTHONPATH','PYTHONHOME','PIP_INDEX_URL','PIP_EXTRA_INDEX_URL','HTTP_PROXY','HTTPS_PROXY','ALL_PROXY')) {
        $start.EnvironmentVariables.Remove($key)
    }
    $start.EnvironmentVariables['PYTHONNOUSERSITE']='1'
    $start.EnvironmentVariables['PIP_NO_INDEX']='1'
    $start.EnvironmentVariables['PIP_DISABLE_PIP_VERSION_CHECK']='1'
    $process=New-Object Diagnostics.Process
    $process.StartInfo=$start
    $stdout=New-Object IO.MemoryStream
    $stderr=New-Object IO.MemoryStream
    $watch=[Diagnostics.Stopwatch]::StartNew()
    $started=$false
    try {
        if(-not $process.Start()){throw 'Provisioning process failed to start.'}
        $started=$true
        $pidValue=$process.Id
        $outBuffer=New-Object byte[] 4096
        $errBuffer=New-Object byte[] 4096
        $outStream=$process.StandardOutput.BaseStream
        $errStream=$process.StandardError.BaseStream
        $outTask=$outStream.ReadAsync($outBuffer,0,$outBuffer.Length)
        $errTask=$errStream.ReadAsync($errBuffer,0,$errBuffer.Length)
        $outOpen=$true; $errOpen=$true
        while($outOpen -or $errOpen -or -not $process.HasExited) {
            if($watch.Elapsed.TotalSeconds -ge $TimeoutSeconds) {
                throw 'PROCESS_TIMEOUT_UNCONFIRMED: stop provisioning and quarantine this guest base; installer descendants may remain.'
            }
            if($outOpen -and $outTask.IsCompleted) {
                $count=$outTask.GetAwaiter().GetResult()
                if($count -eq 0){$outOpen=$false} else {
                    if($stdout.Length+$stderr.Length+$count -gt $OutputBytes) {
                        throw 'PROCESS_OUTPUT_LIMIT_UNCONFIRMED: stop provisioning and quarantine this guest base.'
                    }
                    $stdout.Write($outBuffer,0,$count)
                    $outTask=$outStream.ReadAsync($outBuffer,0,$outBuffer.Length)
                }
            }
            if($errOpen -and $errTask.IsCompleted) {
                $count=$errTask.GetAwaiter().GetResult()
                if($count -eq 0){$errOpen=$false} else {
                    if($stdout.Length+$stderr.Length+$count -gt $OutputBytes) {
                        throw 'PROCESS_OUTPUT_LIMIT_UNCONFIRMED: stop provisioning and quarantine this guest base.'
                    }
                    $stderr.Write($errBuffer,0,$count)
                    $errTask=$errStream.ReadAsync($errBuffer,0,$errBuffer.Length)
                }
            }
            [Threading.Thread]::Sleep(10)
        }
        if(-not $process.WaitForExit(1000)){throw 'Process exit was not confirmed.'}
        return [pscustomobject]@{
            PID=$pidValue; ExitCode=$process.ExitCode
            Stdout=[Text.Encoding]::UTF8.GetString($stdout.ToArray())
            Stderr=[Text.Encoding]::UTF8.GetString($stderr.ToArray())
            ElapsedMilliseconds=$watch.ElapsedMilliseconds
        }
    } finally {
        # Parent termination is best effort. Never claim installer-tree containment here.
        if($started -and -not $process.HasExited) {
            try {$process.Kill(); $null=$process.WaitForExit(1000)} catch { }
        }
        $process.Dispose(); $stdout.Dispose(); $stderr.Dispose(); $watch.Stop()
    }
}
