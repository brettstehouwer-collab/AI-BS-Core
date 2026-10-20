import os
import glob

SCAN_DIRS = [
    r"C:\AI-BS",
    r"C:\AI-BS\backend",
    r"C:\AI-BS\frontend",
    r"C:\AI-BS\scripts",
    r"C:\AI-BS\database"
]

EXCLUDE_DIRS = {"node_modules", ".git", ".venv", "dist", "build-output", "desktop-build", "release-build", "__pycache__", "pyppeteer_env"}
TEXT_EXTS = {".py", ".json", ".js", ".jsx", ".ts", ".tsx", ".html", ".css", ".txt", ".md", ".bat", ".ps1", ".spec", ".jsonl", ".yaml", ".yml"}

utf16_found = []
converted_count = 0

for base_dir in SCAN_DIRS:
    if not os.path.exists(base_dir):
        continue
    for root, dirs, files in os.walk(base_dir):
        dirs[:] = [d for d in dirs if d not in EXCLUDE_DIRS]
        for f in files:
            ext = os.path.splitext(f)[1].lower()
            if ext not in TEXT_EXTS:
                continue
            fpath = os.path.join(root, f)
            try:
                with open(fpath, "rb") as fp:
                    raw = fp.read(4)
                # Check for UTF-16LE BOM (\xff\xfe) or UTF-16BE BOM (\xfe\xff) or null bytes in ASCII range
                if raw.startswith(b"\xff\xfe") or raw.startswith(b"\xfe\xff"):
                    utf16_found.append((fpath, "BOM Header"))
                elif len(raw) >= 2 and raw[1] == 0 and raw[0] != 0:
                    utf16_found.append((fpath, "Null Byte Pattern (UTF-16LE)"))
            except Exception:
                pass

print("=" * 70)
print("             AI-BS UTF-16LE DETECTION & AUTO-NORMALIZER")
print("=" * 70)
print(f"Total UTF-16LE / Non-UTF8 Text Files Found: {len(utf16_found)}")

for fpath, reason in utf16_found:
    print(f"  [CONVERTING] {os.path.relpath(fpath, r'C:\AI-BS')} ({reason})")
    try:
        with open(fpath, "rb") as fp:
            content = fp.read()
        # Decode as utf-16 and strip BOM
        text = content.decode("utf-16", errors="ignore").lstrip("\ufeff")
        with open(fpath, "w", encoding="utf-8") as fp:
            fp.write(text)
        converted_count += 1
    except Exception as e:
        print(f"    [!] Error converting {fpath}: {e}")

print("=" * 70)
print(f"[SUCCESS] Converted {converted_count} files to clean standard UTF-8 (no BOM).")
print("=" * 70)