import os
import shutil
import json
import requests
import time
from typing import List, Optional
from cryptography.fernet import Fernet

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
VAULTS_DIR = os.path.join(BASE_DIR, "AI-BS_Knowledge_Vaults")

ALLOWED_EXTENSIONS = [".md"]
MAX_FILE_SIZE_BYTES = 50 * 1024 * 1024  # 50 MB
IGNORE_FOLDERS = [
    "Windows",
    "AppData",
    "node_modules",
    ".git",
    "Program Files",
    "Program Files (x86)",
    "System32",
    "AI-BS_Knowledge_Vaults",
]

VAULT_KEYWORDS = {
    "NoCo_Ventures": [
        "noco",
        "ventures",
        "startup",
        "equity",
        "investment",
        "cap table",
        "pitch deck",
        "founder",
    ],
    "Fire_Writing": [
        "fire writing",
        "novel",
        "plot",
        "chapter",
        "character arc",
        "storyboard",
        "prose",
        "manuscript",
        "fiction",
    ],
    "Marketing": [
        "marketing",
        "seo",
        "campaign",
        "funnel",
        "conversion",
        "lead gen",
        "social media",
        "ad spend",
        "analytics",
    ],
    "AI_Architecture": [
        "llm",
        "rag",
        "neural",
        "vector database",
        "ollama",
        "transformers",
        "pytorch",
        "tensor",
        "model weights",
        "gpu",
        "cuda",
    ],
    "Trading_Algos": [
        "trading",
        "algorithm",
        "crypto",
        "forex",
        "moving average",
        "macd",
        "rsi",
        "ohlc",
        "backtest",
        "arbitrage",
        "stop loss",
    ],
    "Personal_Journal": [
        "journal",
        "diary",
        "personal",
        "feelings",
        "goals",
        "reflections",
        "today i",
    ],
    "Code_Snippets": [
        "def ",
        "class ",
        "import ",
        "function(",
        "const ",
        "let ",
        "var ",
        "=>",
        "struct ",
        "package ",
    ],
    "System_Logs": [
        "error",
        "warning",
        "info",
        "debug",
        "trace",
        "exception",
        "stacktrace",
        "log level",
        "timestamp",
    ],
}


def classify_content(content: str) -> Optional[str]:
    content_lower = content.lower()

    best_vault = None
    max_hits = 0

    for vault, keywords in VAULT_KEYWORDS.items():
        hits = sum(1 for kw in keywords if kw in content_lower)
        if hits > max_hits:
            max_hits = hits
            best_vault = vault

    if max_hits > 0:
        return best_vault
    return None


def should_ignore_dir(dirpath: str) -> bool:
    parts = dirpath.replace("\\", "/").split("/")
    for ignore in IGNORE_FOLDERS:
        if ignore.lower() in [p.lower() for p in parts]:
            return True
    return False


def scan_and_ingest(target_paths: List[str]):
    print(f"Starting Auto-Ingestion Scan on paths: {target_paths}")
    total_scanned = 0
    total_ingested = 0

    for base_path in target_paths:
        if not os.path.exists(base_path):
            print(f"[WARNING] Path does not exist: {base_path}")
            continue

        for root, dirs, files in os.walk(base_path):
            if should_ignore_dir(root):
                continue

            for filename in files:
                ext = os.path.splitext(filename)[1].lower()
                if ext not in ALLOWED_EXTENSIONS:
                    continue

                filepath = os.path.join(root, filename)

                # Check size
                try:
                    if os.path.getsize(filepath) > MAX_FILE_SIZE_BYTES:
                        continue
                except OSError:
                    continue

                total_scanned += 1

                # Read content snippet
                try:
                    with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
                        snippet = f.read(
                            2000
                        )  # Read first 2000 chars for classification
                except Exception as e:
                    continue

                target_vault = classify_content(snippet)

                if target_vault:
                    vault_path = os.path.join(VAULTS_DIR, target_vault)
                    os.makedirs(vault_path, exist_ok=True)

                    dest_file = os.path.join(vault_path, filename)

                    # Avoid overwriting existing identical filenames by appending a timestamp if it exists
                    if os.path.exists(dest_file):
                        base, extension = os.path.splitext(filename)
                        dest_file = os.path.join(
                            vault_path, f"{base}_{int(time.time())}{extension}"
                        )

                    try:
                        shutil.copy2(filepath, dest_file)
                        total_ingested += 1
                        try:
                            print(f"[INGESTED] {filename} -> {target_vault}/")
                        except UnicodeEncodeError:
                            print(
                                f"[INGESTED] (unprintable filename) -> {target_vault}/"
                            )
                    except Exception as e:
                        try:
                            print(f"[ERROR] Could not copy {filename}: {e}")
                        except UnicodeEncodeError:
                            print(f"[ERROR] Could not copy (unprintable filename)")

    print(f"\n--- Scan Complete ---")
    print(f"Total files analyzed: {total_scanned}")
    print(f"Total files successfully categorized and ingested: {total_ingested}")


def encrypt_env_keys():
    print("--- Starting ENV Key Encryption ---")
    env_path = os.path.join(BASE_DIR, "backend", ".env")
    key_path = os.path.join(BASE_DIR, "backend", "vault_master.key")
    
    if not os.path.exists(env_path):
        print("[ERROR] .env file not found!")
        return
        
    if not os.path.exists(key_path):
        master_key = Fernet.generate_key()
        with open(key_path, "wb") as f:
            f.write(master_key)
        print(f"[SUCCESS] Generated new vault master key at {key_path}")
    else:
        with open(key_path, "rb") as f:
            master_key = f.read()
            
    cipher = Fernet(master_key)
    target_keys = ["PAYOUT_WALLET_PRIVATE_KEY", "CRYPTO_COM_SECRET_KEY", "CRYPTOCOM_APP_AGENT_KEY"]
    
    with open(env_path, "r") as f:
        lines = f.readlines()
        
    modified = False
    new_lines = []
    
    for line in lines:
        if "=" in line and not line.strip().startswith("#"):
            k, v = line.strip().split("=", 1)
            if k in target_keys:
                if not v.startswith("gAAAAA"): # check if already encrypted
                    encrypted_val = cipher.encrypt(v.encode()).decode()
                    new_lines.append(f"{k}={encrypted_val}\n")
                    print(f"[ENCRYPTED] Secured {k} in .env")
                    modified = True
                    continue
        new_lines.append(line)
        
    if modified:
        with open(env_path, "w") as f:
            f.writelines(new_lines)
        print("[SUCCESS] Updated .env with encrypted keys.")
    else:
        print("[INFO] No plaintext target keys found to encrypt.")


if __name__ == "__main__":
    # WARNING: To scan the whole C: and G: drive, you would pass ["C:\\", "G:\\"]
    # We highly recommend starting with a smaller test directory to avoid classifying thousands of system text files.

    print("Welcome to the Bullshit AI Vault Auto-Scanner!")
    print(
        "WARNING: Scanning entire drives may take a significant amount of time and ingest unexpected files."
    )

    # User requested to encrypt .env keys using this module first
    encrypt_env_keys()

    # User requested all drives, specifically markdown files
    target_scan_paths = ["C:\\", "G:\\", "S:\\", "F:\\", "D:\\"]

    scan_and_ingest(target_scan_paths)
