import os

# 1. Update Noco3DCampusWalkthrough.jsx canvas height
walk_path = r"C:\AI-BS\frontend\src\components\Noco3DCampusWalkthrough.jsx"
with open(walk_path, 'r', encoding='utf-8') as f:
    w_code = f.read()

target_w = "height: '520px',"
repl_w = "height: 'clamp(300px, 45vh, 520px)',"

if target_w in w_code:
    w_code = w_code.replace(target_w, repl_w)
    with open(walk_path, 'w', encoding='utf-8') as f:
        f.write(w_code)
    print("Noco3DCampusWalkthrough.jsx updated!")
else:
    print("Target in Walkthrough not found")

# 2. Update VLCPreviewMonitor.jsx maxHeight
vlc_path = r"C:\AI-BS\frontend\src\components\VLCPreviewMonitor.jsx"
with open(vlc_path, 'r', encoding='utf-8') as f:
    v_code = f.read()

target_v = "maxHeight: '520px',"
repl_v = "maxHeight: 'clamp(220px, 45vh, 520px)',"

if target_v in v_code:
    v_code = v_code.replace(target_v, repl_v)
    with open(vlc_path, 'w', encoding='utf-8') as f:
        f.write(v_code)
    print("VLCPreviewMonitor.jsx updated!")
else:
    print("Target in VLC not found")
