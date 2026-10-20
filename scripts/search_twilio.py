import os
from pathlib import Path

for root, dirs, files in os.walk(r"C:\AI-BS"):
    if any(ignore in root for ignore in ["node_modules", ".git", "venv", "desktop-build", "build-output"]):
        continue
    for f in files:
        if f.endswith((".py", ".env", ".json", ".txt")):
            full_path = Path(root) / f
            try:
                content = full_path.read_text(encoding="utf-8", errors="ignore")
                if "TWILIO" in content or "twilio" in content:
                    print(f"Found Twilio reference in: {full_path}")
            except Exception:
                pass
