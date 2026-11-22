' start_trainer.vbs — Launches trainer_daemon.py as a background process on Windows
' Double-click this file to start the daemon, or run: cscript //Nologo start_trainer.vbs

Dim ws, pythonExe, scriptPath, shell, result

Set ws = CreateObject("WScript.Shell")
scriptPath = Left(WScript.ScriptFullName, InStrRev(WScript.ScriptFullName, "\"))
pythonExe = "python"  ' Adjust if Python is not in PATH, e.g., "C:\Users\footb\ai_bs_img_env\Scripts\python.exe"

' Check if daemon is already running
result = ws.Run("cmd /c tasklist /FI ""IMAGENAME eq python.exe"" /FO CSV 2>nul | find /i ""trainer_daemon""", 0, True)
If result = 0 Then
    WScript.Echo "Trainer daemon is already running."
    WScript.Quit(1)
End If

' Launch the daemon in a hidden window (no console popup)
ws.Run pythonExe & " """ & scriptPath & "trainer_daemon.py""", 0, False

WScript.Sleep 2000  ' Wait for daemon to initialize

' Verify it started
result = ws.Run("cmd /c tasklist /FI ""IMAGENAME eq python.exe"" /FO CSV 2>nul | find /i ""trainer_daemon""", 0, True)
If result = 0 Then
    WScript.Echo "Trainer daemon started successfully."
Else
    WScript.Echo "WARNING: Trainer daemon may have failed to start. Check trainer_daemon_logs.jsonl for details."
End If
