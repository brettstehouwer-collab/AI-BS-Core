
Set oWS = WScript.CreateObject("WScript.Shell")
sIcon = "C:\AI-BS\game_trainer\assets\btd6_monkey_trainer.ico"

Sub UpdateShortcut(sPath)
    Set fso = CreateObject("Scripting.FileSystemObject")
    If fso.FileExists(sPath) Then
        Set oLink = oWS.CreateShortcut(sPath)
        oLink.IconLocation = sIcon
        oLink.Save
        WScript.Echo "Updated: " & sPath
    End If
End Sub

UpdateShortcut "C:\Users\footb\Desktop\Play BTD6 (Monkey Trainer).lnk"
UpdateShortcut "C:\Users\footb\OneDrive\Desktop\Play BTD6 (Monkey Trainer).lnk"
UpdateShortcut "C:\Users\Public\Desktop\Play BTD6 (Monkey Trainer).lnk"
UpdateShortcut "C:\Users\footb\Desktop\AI-BS BTD6 Trainer.lnk"
UpdateShortcut "C:\Users\footb\OneDrive\Desktop\AI-BS BTD6 Trainer.lnk"
