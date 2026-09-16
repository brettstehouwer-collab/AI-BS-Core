import os

paths = [
    "C:/AI-BS/frontend/components/ChatTab.jsx",
    "C:/AI-BS/frontend/src/components/ChatTab.jsx",
    "C:/AI-BS/backend/core/hybrid_reasoning_engine.py",
    "C:/AI-BS/backend/aibs_reasoning_engine.py"
]

for path in paths:
    if os.path.exists(path):
        with open(path, "rb") as f:
            raw = f.read()
            
        # Check for UTF-8 BOM
        if raw.startswith(b"\xef\xbb\xbf"):
            print(f"BOM found in {path}, removing it.")
            raw = raw[3:]
            
        # Also decode/encode to ensure it's valid UTF-8
        try:
            text = raw.decode("utf-8")
        except UnicodeDecodeError:
            # It might have been corrupted by PowerShell into ANSI
            text = raw.decode("cp1252", errors="replace")
            print(f"File {path} was NOT valid UTF-8! Decoded as cp1252.")
            
        with open(path, "w", encoding="utf-8", newline="") as f:
            f.write(text)

print("Files normalized to strict UTF-8 without BOM.")
