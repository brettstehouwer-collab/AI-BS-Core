' AI-BS Native Studio Silent VBS Launcher (v5.313.0)
' Runs AI_BS_Studio.exe natively without console flicker.

Set WshShell = CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")

strScriptDir = fso.GetParentFolderName(WScript.ScriptFullName)
strExePath = strScriptDir & "\native_studio\dist\AI_BS_Studio\AI_BS_Studio.exe"

If fso.FileExists(strExePath) Then
    WshShell.CurrentDirectory = strScriptDir & "\native_studio\dist\AI_BS_Studio"
    WshShell.Run """" & strExePath & """", 1, False
Else
    strBatPath = strScriptDir & "\Launch_Native_Studio.bat"
    WshShell.CurrentDirectory = strScriptDir
    WshShell.Run """" & strBatPath & """", 0, False
End If

Set WshShell = Nothing
Set fso = Nothing
