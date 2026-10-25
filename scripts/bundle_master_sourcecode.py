"""
scripts/bundle_master_sourcecode.py
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Autonomous Master Source Code Bundler & Ecosystem Synchronizer (v5.327.0)
- Recursively gathers all legitimate source code across all subsystems:
  .agents, backend, docs, frontend, mobile-app, native_studio, scripts, skills, and root ecosystem files.
- Excludes binary files, node_modules, build caches, git bloat, and massive assets.
- Cleans and normalizes text encodings (resolves UTF-16 BOM and mixed PowerShell null bytes).
- Builds master header, formatted table of contents manifest, and full file contents blocks.
- Synchronizes output across:
  * C:\\Users\\footb\\OneDrive\\Desktop\\AI_BS_Complete_SourceCode.txt
  * C:\\Users\\footb\\OneDrive\\Desktop\\AI_BS_Complete_SourceCode.md
  * C:\\Users\\footb\\OneDrive\\Desktop\\AI_BS_Complete_SourceCode.zip
  * C:\\Users\\footb\\Desktop\\AI_BS_Complete_SourceCode.txt
  * C:\\Users\\footb\\Desktop\\AI_BS_Complete_SourceCode.md
  * C:\\Users\\footb\\Desktop\\AI_BS_Complete_SourceCode.zip
- Optionally triggers scripts/ingest_complete_sourcecode.py to update SQLite & ChromaDB vaults.
"""

import os
import sys
import time
import zipfile
import shutil
import datetime

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
VERSION_FILE = os.path.join(BASE_DIR, "version.txt")

TARGET_DIRS = [
    ".agents",
    "backend",
    "docs",
    "frontend",
    "mobile-app",
    "native_studio",
    "scripts",
    "skills",
]

ROOT_FILES = [
    "AI-BS.code-workspace",
    "AI_BS_Global_Context.md",
    "AI_BS_MASTER_ARCHITECTURAL_LEDGER.md",
    "MASTER_HANDOFF_CHRONOLOGY.md",
    "MASTER_HISTORICAL_INDEX.md",
    "MASTER_IMPLEMENTATION_PLANS_CHRONOLOGY.md",
    "MASTER_TASKS_CHRONOLOGY.md",
    "SAVED_CHECKPOINT.md",
    "version.txt",
    "package.json",
    "requirements.txt",
    "pyproject.toml",
    "Launch_Desktop_Studio_Fast.bat",
    "Launch_Native_Studio.bat",
    "Launch_AI_BS_Administrator.bat",
    "Run_Native_Desktop_Studio.bat"
]

EXCLUDE_DIRS = {
    ".git", "node_modules", "pyppeteer_env", "venv", ".venv", "__pycache__",
    ".pytest_cache", "build", "dist", "dist_bin", "dist_old_2fef7dfb", ".vscode",
    "temp_unzip", "blobs", "bin", "uploads", "output", "downloads", "downloads_archive",
    "assets", "pictures", "videos", "screenshots", "music", "datasets", "stehouwer_vector_memory",
    "chroma_db", "chroma_db_8002", "aria2-1.37.0-win-64bit-build1", "ai-bs-models",
    "miners", "pearl", "models", "installerexe's", "exe", "comfyui", "context_memory_swap",
    "vram_tensor_swap", "android", "ios", "desktop-build", "build-output", "archive_vault",
    "wgs_backups", ".expo"
}

ALLOWED_EXTS = {
    ".py", ".js", ".jsx", ".ts", ".tsx", ".json", ".md", ".html", ".css",
    ".go", ".ps1", ".bat", ".sh", ".sql", ".yaml", ".yml", ".modelfile",
    ".txt", ".toml", ".spec"
}

LANG_MAP = {
    "py": "python",
    "js": "javascript",
    "jsx": "jsx",
    "ts": "typescript",
    "tsx": "tsx",
    "json": "json",
    "md": "md",
    "html": "html",
    "css": "css",
    "go": "go",
    "ps1": "powershell",
    "bat": "bat",
    "sh": "bash",
    "sql": "sql",
    "yaml": "yaml",
    "yml": "yaml",
    "modelfile": "modelfile",
    "txt": "text",
    "toml": "toml",
    "spec": "python"
}

OUTPUT_PATHS = [
    r"C:\Users\footb\OneDrive\Desktop\AI_BS_Complete_SourceCode.txt",
    r"C:\Users\footb\OneDrive\Desktop\AI_BS_Complete_SourceCode.md",
    r"C:\Users\footb\Desktop\AI_BS_Complete_SourceCode.txt",
    r"C:\Users\footb\Desktop\AI_BS_Complete_SourceCode.md"
]

ZIP_OUTPUT_PATHS = [
    r"C:\Users\footb\OneDrive\Desktop\AI_BS_Complete_SourceCode.zip",
    r"C:\Users\footb\Desktop\AI_BS_Complete_SourceCode.zip"
]


def get_ecosystem_version() -> str:
    if os.path.exists(VERSION_FILE):
        try:
            with open(VERSION_FILE, "r", encoding="utf-8") as f:
                ver = f.read().strip()
                if ver:
                    return ver
        except Exception:
            pass
    return "v5.327.0"


def clean_read_text(file_path: str) -> str:
    """
    Safely reads file contents into clean UTF-8 text, handling UTF-16 BOM,
    PowerShell mixed-encoding append artifacts, and stripping null bytes.
    """
    try:
        with open(file_path, "rb") as f:
            raw = f.read()
        if not raw:
            return ""

        # Check BOMs
        if raw.startswith(b"\xff\xfe") or raw.startswith(b"\xfe\xff"):
            return raw.decode("utf-16", errors="replace").lstrip("\ufeff")

        # Null byte check (PowerShell UTF-16LE append or binary buffer)
        if b"\x00" in raw:
            # If the file is predominantly nulls (e.g., zeroed SHM buffer), reject it
            null_ratio = raw.count(b"\x00") / len(raw)
            if null_ratio > 0.4:
                return ""  # Treat as binary / empty
            # If UTF-16 without BOM
            if raw[1::2].count(b"\x00") > len(raw) * 0.35:
                return raw.decode("utf-16", errors="replace").lstrip("\ufeff")
            # PowerShell append artifact: strip embedded nulls
            return raw.replace(b"\x00", b"").decode("utf-8", errors="replace")

        return raw.decode("utf-8", errors="replace")
    except Exception as e:
        return ""


def discover_files() -> list:
    """
    Gathers all qualifying source files in deterministic alphabetical order.
    Returns list of dicts: {'rel_path', 'full_path', 'size', 'ext'}
    """
    collected = {}

    # 1. Root files
    for rf in ROOT_FILES:
        full_p = os.path.join(BASE_DIR, rf)
        if os.path.isfile(full_p):
            try:
                sz = os.path.getsize(full_p)
                if 0 < sz <= 1_500_000:
                    rel = rf.replace(os.sep, "/")
                    ext = os.path.splitext(rf)[1].lower().lstrip(".")
                    collected[rel] = {
                        "rel_path": rel,
                        "full_path": full_p,
                        "size": sz,
                        "ext": ext
                    }
            except Exception:
                pass

    # 2. Target directories
    for td in TARGET_DIRS:
        dp = os.path.join(BASE_DIR, td)
        if not os.path.exists(dp):
            continue
        for root, dirs, files in os.walk(dp):
            dirs[:] = [d for d in dirs if d.lower() not in EXCLUDE_DIRS]
            for f in files:
                ext = os.path.splitext(f)[1].lower()
                if ext in ALLOWED_EXTS:
                    full_p = os.path.join(root, f)
                    try:
                        sz = os.path.getsize(full_p)
                        if 0 < sz <= 1_500_000:
                            rel = os.path.relpath(full_p, BASE_DIR).replace(os.sep, "/")
                            clean_ext = ext.lstrip(".")
                            collected[rel] = {
                                "rel_path": rel,
                                "full_path": full_p,
                                "size": sz,
                                "ext": clean_ext
                            }
                    except Exception:
                        pass

    # Sort deterministically
    sorted_files = sorted(collected.values(), key=lambda x: x["rel_path"].lower())
    return sorted_files


def build_master_bundle():
    t_start = time.time()
    version = get_ecosystem_version()
    # Format timestamp like '2026-10-19 07:15:22 EDT'
    now = datetime.datetime.now()
    tz_name = time.tzname[time.daylight] if time.daylight else time.tzname[0]
    timestamp_str = f"{now.strftime('%Y-%m-%d %H:%M:%S')} {tz_name}"

    print("=" * 80)
    print(f"  AI-BS MASTER SOURCE CODE BUNDLER — ECOSYSTEM VERSION {version}")
    print(f"  Root Directory: {BASE_DIR}")
    print(f"  Timestamp:      {timestamp_str}")
    print("=" * 80)

    print("🔍 Discovering source files across all subsystems...")
    raw_files = discover_files()
    print(f"   Found {len(raw_files):,} candidate files. Validating text content...")

    valid_files = []
    total_lines = 0

    for item in raw_files:
        content = clean_read_text(item["full_path"])
        if not content.strip():
            continue  # skip empty or pure binary buffers
        lines = len(content.splitlines())
        size_bytes = len(content.encode("utf-8"))
        item["content"] = content
        item["lines"] = lines
        item["size_bytes"] = size_bytes
        valid_files.append(item)
        total_lines += lines

    total_count = len(valid_files)
    print(f"⚡ Packaged {total_count:,} valid text source files ({total_lines:,} total lines).")

    # Header construction
    banner_w = 98
    title_line = "AI-BS (AUTONOMOUS INTELLIGENCE & BUILD SYSTEM) — COMPLETE MASTER SOURCE CODE BUNDLE"
    sub_line = f"Ecosystem Version: {version} | Generated: {timestamp_str}"
    count_line = f"Total Packaged Files: {total_count}"

    top_border = "╔" + ("═" * banner_w) + "╗"
    bot_border = "╚" + ("═" * banner_w) + "╝"
    div_line = "═" * 100

    header_lines = [
        top_border,
        f"║{title_line:^{banner_w}}║",
        f"║{sub_line:^{banner_w}}║",
        f"║{count_line:^{banner_w}}║",
        bot_border,
        "",
        div_line,
        "📋 MASTER CODEBASE MANIFEST & TABLE OF CONTENTS",
        div_line
    ]
    header_block = "\n".join(header_lines) + "\n"

    manifest_lines = []
    width_idx = max(3, len(str(total_count)))
    for idx, item in enumerate(valid_files, 1):
        rel = item["rel_path"]
        kb = item["size_bytes"] / 1024.0
        manifest_lines.append(f"[{idx:0{width_idx}d}/{total_count}] {rel:<66} ({kb:>6.1f} KB)")

    manifest_block = "\n".join(manifest_lines) + "\n" + div_line + "\n\n\n"

    # Write master bundle to a temporary primary location first
    temp_bundle_path = os.path.join(BASE_DIR, "saved_data", "temp_sourcecode_bundle.txt")
    os.makedirs(os.path.dirname(temp_bundle_path), exist_ok=True)

    print(f"💾 Writing master text stream to {temp_bundle_path}...")
    t_write0 = time.time()
    with open(temp_bundle_path, "w", encoding="utf-8") as out:
        out.write(header_block)
        out.write(manifest_block)

        for idx, item in enumerate(valid_files, 1):
            rel = item["rel_path"]
            lines = item["lines"]
            size_b = item["size_bytes"]
            ext = item["ext"].upper()
            fence_lang = LANG_MAP.get(item["ext"].lower(), item["ext"].lower())

            out.write("#" * 100 + "\n")
            out.write(f"# FILE [{idx:0{width_idx}d}/{total_count}]: {rel}\n")
            out.write(f"# LINES: {lines} | SIZE: {size_b:,} BYTES | EXT: {ext}\n")
            out.write("#" * 100 + "\n\n")

            out.write(f"```{fence_lang}\n")
            out.write(item["content"])
            if not item["content"].endswith("\n"):
                out.write("\n")
            out.write("```\n\n\n")

    t_written = time.time() - t_write0
    final_size_mb = os.path.getsize(temp_bundle_path) / (1024 * 1024)
    print(f"✅ Text bundle assembled in {t_written:.2f}s ({final_size_mb:.2f} MB).")

    # Distribute to target file paths (.txt and .md)
    print("📤 Mirroring bundle across all active Desktop directories...")
    for target in OUTPUT_PATHS:
        try:
            target_dir = os.path.dirname(target)
            if os.path.exists(target_dir):
                shutil.copyfile(temp_bundle_path, target)
                print(f"   ✓ Synchronized: {target}")
            else:
                print(f"   ℹ Directory does not exist, skipped: {target_dir}")
        except Exception as e:
            print(f"   ⚠ Could not copy to {target}: {e}")

    # Build ZIP archive containing the exact relative source tree
    temp_zip_path = os.path.join(BASE_DIR, "saved_data", "temp_sourcecode_bundle.zip")
    print(f"📦 Compressing {total_count:,} files into master ZIP archive...")
    t_zip0 = time.time()
    with zipfile.ZipFile(temp_zip_path, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=6) as zf:
        for item in valid_files:
            zf.write(item["full_path"], arcname=item["rel_path"])
    t_zip = time.time() - t_zip0
    zip_size_mb = os.path.getsize(temp_zip_path) / (1024 * 1024)
    print(f"✅ Master ZIP compressed in {t_zip:.2f}s ({zip_size_mb:.2f} MB).")

    for zip_target in ZIP_OUTPUT_PATHS:
        try:
            target_dir = os.path.dirname(zip_target)
            if os.path.exists(target_dir):
                shutil.copyfile(temp_zip_path, zip_target)
                print(f"   ✓ Synchronized ZIP: {zip_target}")
        except Exception as e:
            print(f"   ⚠ Could not copy ZIP to {zip_target}: {e}")

    # Cleanup temp working files in saved_data
    try:
        if os.path.exists(temp_bundle_path):
            os.remove(temp_bundle_path)
        if os.path.exists(temp_zip_path):
            os.remove(temp_zip_path)
    except Exception:
        pass

    total_time = time.time() - t_start
    print("=" * 80)
    print(f"🎉 MASTER SOURCE CODE BUNDLE GENERATION COMPLETE ({total_time:.2f}s)")
    print(f"   Ecosystem Version:    {version}")
    print(f"   Total Packaged Files: {total_count:,}")
    print(f"   Total Code Lines:     {total_lines:,}")
    print(f"   Bundle Size:          {final_size_mb:.2f} MB")
    print(f"   ZIP Compressed Size:  {zip_size_mb:.2f} MB")
    print("=" * 80)


if __name__ == "__main__":
    build_master_bundle()
