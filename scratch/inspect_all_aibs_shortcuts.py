import os
import glob
import subprocess

ps_script = """
$sh = New-Object -ComObject WScript.Shell
$folders = @('C:\\Users\\footb\\OneDrive\\Desktop', 'C:\\Users\\footb\\Desktop')
Get-ChildItem -Path $folders -Filter '*.lnk' | ForEach-Object {
    try {
        $s = $sh.CreateShortcut($_.FullName)
        Write-Output "$($_.Name)|$($s.TargetPath)|$($s.Arguments)|$($s.WorkingDirectory)"
    } catch {}
}
"""

with open(r'c:\AI-BS\scratch\dump_shortcuts.ps1', 'w', encoding='utf-8') as f:
    f.write(ps_script)

res = subprocess.run(['powershell', '-ExecutionPolicy', 'Bypass', '-File', r'c:\AI-BS\scratch\dump_shortcuts.ps1'], capture_output=True, text=True, encoding='utf-8', errors='ignore')

print("All Desktop Shortcuts to AI-BS or Studio:")
for line in res.stdout.strip().split('\n'):
    parts = line.strip().split('|')
    if len(parts) >= 2:
        name, target = parts[0], parts[1]
        args = parts[2] if len(parts) > 2 else ""
        if any(k in name.lower() or k in target.lower() for k in ['ai-bs', 'aibs', 'stehouwer', 'launch', 'shutdown', 'studio']):
            print(f"- Name: {name}")
            print(f"  Target: {target}")
            if args:
                print(f"  Arguments: {args}")
            print()
