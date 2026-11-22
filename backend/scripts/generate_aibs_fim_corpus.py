"""
AI-BS Sovereign FIM (Fill-In-The-Middle) Code Dataset Generator
Adapted from 'AI programing training.md' for local fine-tuning on RTX 4090.
Deduplicates via SHA-256, scrubs secrets, and injects control tokens:
<fim_prefix>PREFIX<fim_suffix>SUFFIX<fim_middle>MIDDLE
"""

import os
import json
import hashlib
import re
from pathlib import Path

WORKSPACE = Path(r"C:\AI-BS")
OUTPUT_PATH = WORKSPACE / "saved_data" / "aibs_fim_training_corpus.json"
OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)

SOURCE_DIRS = [
    WORKSPACE / "backend",
    WORKSPACE / "native_studio",
    WORKSPACE / "frontend" / "src",
    WORKSPACE / "scripts",
    WORKSPACE / "game_trainer"
]

TARGET_EXTS = {".py", ".jsx", ".js", ".tsx", ".ts", ".ps1", ".bat"}
EXCLUDE_SUBSTRINGS = ["node_modules", ".git", "dist", "build", "__pycache__", ".pytest_cache", "venv", "env"]

FIM_PREFIX = "<fim_prefix>"
FIM_SUFFIX = "<fim_suffix>"
FIM_MIDDLE = "<fim_middle>"

# Basic regex filters for secrets
SECRET_PATTERNS = [
    re.compile(r"(['\"]?)(?:api[_-]?key|secret|password|token|bearer)\1\s*[:=]\s*['\"][A-Za-z0-9_\-]{16,}['\"]", re.IGNORECASE),
    re.compile(r"-----BEGIN (?:RSA |EC )?PRIVATE KEY-----")
]

def contains_secret(text: str) -> bool:
    for pat in SECRET_PATTERNS:
        if pat.search(text):
            return True
    return False

def generate_corpus():
    print(f"Scanning curated AI-BS source directories for FIM training...")
    seen_hashes = set()
    records = []
    
    total_files = 0
    skipped_duplicates = 0
    skipped_secrets = 0
    
    for sdir in SOURCE_DIRS:
        if not sdir.exists():
            continue
        print(f" -> Indexing {sdir}...")
        for root, dirs, files in os.walk(sdir):
            dirs[:] = [d for d in dirs if not any(sub in d.lower() for sub in EXCLUDE_SUBSTRINGS)]
            
            for file in files:
                ext = os.path.splitext(file)[1].lower()
                if ext not in TARGET_EXTS:
                    continue
                    
                file_path = Path(root) / file
                if any(sub in str(file_path).lower() for sub in EXCLUDE_SUBSTRINGS):
                    continue
                    
                try:
                    content = file_path.read_text(encoding="utf-8", errors="ignore").strip()
                    if len(content) < 80 or len(content) > 40000:
                        continue
                        
                    total_files += 1
                    
                    if contains_secret(content):
                        skipped_secrets += 1
                        continue
                        
                    sha = hashlib.sha256(content.encode("utf-8")).hexdigest()
                    if sha in seen_hashes:
                        skipped_duplicates += 1
                        continue
                    seen_hashes.add(sha)
                    
                    c_len = len(content)
                    split1 = c_len // 3
                    split2 = (c_len * 2) // 3
                    
                    prefix = content[:split1]
                    middle = content[split1:split2]
                    suffix = content[split2:]
                    
                    fim_text = f"{FIM_PREFIX}{prefix}{FIM_SUFFIX}{suffix}{FIM_MIDDLE}{middle}"
                    
                    records.append({
                        "text": fim_text,
                        "metadata": {
                            "file": str(file_path.relative_to(WORKSPACE)),
                            "length": c_len,
                            "ext": ext
                        }
                    })
                except Exception:
                    pass
                    
    print(f"\nTotal candidate files scanned : {total_files}")
    print(f"Duplicates pruned (SHA-256)   : {skipped_duplicates}")
    print(f"Secrets filtered              : {skipped_secrets}")
    print(f"Final unique FIM samples      : {len(records)}")
    
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(records, f, indent=2, ensure_ascii=False)
        
    print(f"Saved sovereign corpus to: {OUTPUT_PATH}")

if __name__ == "__main__":
    generate_corpus()
