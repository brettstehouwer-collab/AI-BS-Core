function Start-AIBSUnrealPixelStreaming {
    [CmdletBinding()]
    param()
    $ErrorActionPreference = 'Stop'
    $projectRoot = Split-Path -Parent $PSScriptRoot
    $pythonExe = Join-Path $projectRoot 'pyppeteer_env\Scripts\python.exe'
    $signalingScript = Join-Path $projectRoot 'backend\AI_BS_Unreal_Signaling_Server.py'
    $unrealExe = 'C:\Program Files\Epic Games\UE_5.8\Engine\Binaries\Win64\UnrealEditor.exe'
    $unrealProject = Join-Path $projectRoot 'UnrealHub\AI_BS_Hub.uproject'
    foreach ($file in @($pythonExe, $signalingScript, $unrealExe, $unrealProject)) {
        if (-not (Test-Path -LiteralPath $file -PathType Leaf)) { throw "Required streaming file is missing: $file" }
    }
    if (Get-NetTCPConnection -State Listen -LocalPort 8888 -ErrorAction SilentlyContinue) {
        throw 'Port 8888 is already in use. The existing session was left unchanged.'
    }
    $signalProcess = $null
    $signalStarted = $null
    try {
        Write-Host 'Starting an on-demand Unreal Pixel Streaming session...'
        $signalProcess = Start-Process -FilePath $pythonExe -ArgumentList @('"' + $signalingScript + '"') -WorkingDirectory (Split-Path $signalingScript) -WindowStyle Hidden -PassThru
        $signalStarted = $signalProcess.StartTime.ToUniversalTime().Ticks
        $ready = $false
        for ($attempt = 0; $attempt -lt 40; $attempt++) {
            $signalProcess.Refresh()
            if ($signalProcess.HasExited) { throw 'The signaling process exited before becoming ready.' }
            $listeners = @(Get-NetTCPConnection -State Listen -LocalPort 8888 -ErrorAction SilentlyContinue)
            if ($listeners.Count -gt 0) {
                if (@($listeners | Where-Object { $_.OwningProcess -ne $signalProcess.Id -or $_.LocalAddress -ne '127.0.0.1' }).Count -gt 0) {
                    throw 'An unexpected listener appeared on port 8888. It was left unchanged.'
                }
                $ready = $true
                break
            }
            Start-Sleep -Milliseconds 250
        }
        if (-not $ready) { throw 'The on-demand signaling service did not become ready.' }
        $arguments = @("`"$unrealProject`"", '-game', '-AudioMixer', '-PixelStreamingURL=ws://127.0.0.1:8888', '-PixelStreamingEncoderCodec=H264', '-RenderOffScreen', '-RCWebControlEnable', '-RCWebInterfaceEnable', '-AllowPixelStreamingCommands', '-Windowed', '-ResX=1280', '-ResY=720', '-stdout', '-FullStdOutLogOutput')
        $engineProcess = Start-Process -FilePath $unrealExe -ArgumentList $arguments -WorkingDirectory $projectRoot -WindowStyle Hidden -PassThru
        $engineProcess.WaitForExit()
        Write-Host 'The Unreal Pixel Streaming session ended.'
    }
    finally {
        # Terminate only the signaling instance created by this invocation.
        if ($null -ne $signalProcess -and $null -ne $signalStarted) {
            $owned = Get-Process -Id $signalProcess.Id -ErrorAction SilentlyContinue
            if ($null -ne $owned -and $owned.Path -ieq $pythonExe -and $owned.StartTime.ToUniversalTime().Ticks -eq $signalStarted) {
                Stop-Process -Id $owned.Id -ErrorAction SilentlyContinue
            }
        }
    }
}

# Importing the controller for inspection/tests never starts a session.
if ($MyInvocation.InvocationName -ne '.') {
    Start-AIBSUnrealPixelStreaming
}
