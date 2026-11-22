Set WshShell = CreateObject("WScript.Shell")
WshShell.CurrentDirectory = "C:\AI-BS"
Set CoreEnvironment = WshShell.Environment("PROCESS")
For Each FlagName In Array("AI_BS_RECDEBUT_OUTBOUND_ENABLED", "AI_BS_RECDEBUT_INBOUND_POLLING_ENABLED", "AI_BS_DISCORD_NOTIFICATIONS_ENABLED", "AI_BS_BACKEND_MANAGE_DAEMONS", "AI_BS_BACKEND_BACKGROUND_ENABLED", "AI_BS_ALLOW_DESTRUCTIVE_ACTIONS")
    CoreEnvironment(FlagName) = "false"
Next
Set FileSystem = CreateObject("Scripting.FileSystemObject")
PythonExe = WshShell.ExpandEnvironmentStrings("%LOCALAPPDATA%\Programs\Python\Python312\pythonw.exe")
If Not FileSystem.FileExists(PythonExe) Then
    PythonExe = "C:\AI-BS\pyppeteer_env\Scripts\pythonw.exe"
End If
WshShell.Run Chr(34) & PythonExe & Chr(34) & " " & Chr(34) & "C:\AI-BS\scripts\core_boot.py" & Chr(34), 0, False
