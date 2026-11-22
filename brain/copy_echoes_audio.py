import os
import shutil

dest_dir = r"C:\AI-BS\music\Echoes_Collection"
os.makedirs(dest_dir, exist_ok=True)

files_to_copy = [
    r"C:\Users\footb\OneDrive\Desktop\AI_BS_SCREENPLAY BACKUPS\Echoes_Within\audio\ElevenLabs_Echos_Within.wav",
    r"C:\Users\footb\Desktop\pdf-download-site\book site\MasterAudiobook_Trimmed.mp3",
    r"C:\Users\footb\Desktop\pdf-download-site\book site\MasterAudiobook.mp3",
    r"C:\AI-BS\Gemini_Takeout_Dataparrent\Echoes Within_ A Journey Through Psychosis, Trauma, and the Resilience of the Human Spirit.wav",
    r"C:\AI-BS\Gemini_Takeout_Dataparrent\The Echos Within.wav",
    r"C:\Users\footb\Desktop\pdf-download-site\book site\audio\Echos_Within.mp3",
    r"C:\Users\footb\Desktop\pdf-download-site\book site\trim_and_stitch.py",
]

print(f"Target directory: {dest_dir}")
for src in files_to_copy:
    if os.path.exists(src):
        basename = os.path.basename(src)
        dst = os.path.join(dest_dir, basename)
        shutil.copy2(src, dst)
        size_mb = os.path.getsize(dst) / (1024 * 1024)
        print(f"Copied: {basename} ({size_mb:.2f} MB)")
    else:
        print(f"Source not found: {src}")

# Also create desktop shortcut via python / powershell
try:
    import subprocess
    cmd = f'''$wsh = New-Object -ComObject WScript.Shell; $s = $wsh.CreateShortcut('C:\\Users\\footb\\Desktop\\Echoes_Collection.lnk'); $s.TargetPath = '{dest_dir}'; $s.Save()'''
    subprocess.run(["powershell", "-ExecutionPolicy", "Bypass", "-Command", cmd], check=True)
    print("Desktop shortcut 'Echoes_Collection.lnk' created.")
except Exception as e:
    print(f"Shortcut creation notice: {e}")
