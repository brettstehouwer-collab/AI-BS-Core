import os
import time
import sqlite3
import logging
import json
import re
from datetime import datetime

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger("ContextIngestor")


class ContextIngestorDaemon:
    def __init__(self):
        self.backend_dir = os.path.dirname(os.path.abspath(__file__))
        self.root_dir = os.path.dirname(self.backend_dir)
        self.frontend_dir = os.path.join(self.root_dir, "frontend")

        self.output_file = os.path.join(self.root_dir, "AI_BS_Global_Context.md")
        self.manifest_path = os.path.join(self.root_dir, "ingest_manifest.json")
        self.recovered_path = os.path.join(
            self.backend_dir, "recovered_intelligence.json"
        )

        # Target Drives from user system (Prioritize E: Datasets)
        self.target_drives = ["E:\\AI_BS_Resources\\Datasets", "C:\\", "D:\\", "E:\\", "F:\\", "G:\\"]
        self.active_drives = [d for d in self.target_drives if os.path.exists(d)]

        self.ignore_dirs = {
            "Windows",
            "Program Files",
            "Program Files (x86)",
            "ProgramData",
            "$Recycle.Bin",
            "System Volume Information",
            "AppData\\Local\\Temp",
            "node_modules",
            ".git",
            "pyppeteer_env",
            "__pycache__",
            ".venv",
            "venv",
            "env",
            "dist",
            "build",
            ".vscode",
            "ComfyUI",
            "Agent Vector Memory",
            "MP4 medial screen recordings",
            ".gradle",
            ".cargo",
        }
        self.include_extensions = {
            ".py",
            ".js",
            ".jsx",
            ".css",
            ".html",
            ".md",
            ".json",
            ".yml",
            ".bat",
            ".txt",
            ".sql",
            ".csv",
        }
        self.max_file_size = 150 * 1024  # 150KB limit per text snippet

        self.ignore_files = {
            "package-lock.json",
            "active_agent_transcript.jsonl",
            "trainer_daemon_logs.jsonl",
            "AI_BS_Global_Context.md",
            "session_history_archive.json",
            "package.json",
        }

    def _should_include_file(self, filepath):
        if not os.path.exists(filepath):
            return False

        filename = os.path.basename(filepath)
        if filename in self.ignore_files:
            return False

        ext = os.path.splitext(filename)[1].lower()
        if ext not in self.include_extensions:
            return False

        try:
            if os.path.getsize(filepath) > self.max_file_size:
                return False
        except Exception:
            return False

        return True

    def _audit_recovery_intelligence(self):
        """Safely inspects config & env files for lost API keys and script tools without modifying any files."""
        recovered = []

        # Pre-compile regex patterns for massive performance boost during drive walk
        compiled_patterns = [
            re.compile(r"AIzaSy[A-Za-z0-9_-]{33}"),  # Google/Gemini API Key
            re.compile(r"sk-proj-[A-Za-z0-9_-]{40,}"),  # OpenAI Key
            re.compile(r"sk-ant-api[A-Za-z0-9_-]{40,}"),  # Anthropic Key
            re.compile(r"rk_[a-zA-Z0-9_]{30,}"),  # RapidAPI Key
            re.compile(r"DOGE:[A-Za-z0-9]{30,}"),  # Crypto Wallet Addr
        ]

        for drive in self.active_drives:
            # Scan top-level folders and key config files safely
            for root, dirs, files in os.walk(drive):
                # Skip heavy system dirs
                dirs[:] = [
                    d
                    for d in dirs
                    if d not in self.ignore_dirs and not d.startswith("$")
                ]

                # Limit depth to keep audit fast and non-blocking
                rel_depth = root.replace(drive, "").count(os.sep)
                if rel_depth > 4:
                    dirs.clear()
                    continue

                for f in files:
                    if (
                        f.endswith(
                            (".env", ".env.local", "config.json", "settings.json")
                        )
                        or f == "config"
                    ):
                        fp = os.path.join(root, f)
                        try:
                            if os.path.getsize(fp) > 50 * 1024:
                                continue
                            with open(fp, "r", encoding="utf-8", errors="ignore") as ef:
                                text = ef.read()
                                for pat in compiled_patterns:
                                    matches = pat.findall(text)
                                    for m in matches:
                                        recovered.append(
                                            {
                                                "type": "Discovered API/Secret Key",
                                                "source_file": fp,
                                                "key_snippet": m[:8] + "..." + m[-4:],
                                                "detected_at": datetime.now().strftime(
                                                    "%Y-%m-%d %I:%M:%S %p"
                                                ),
                                            }
                                        )
                        except Exception:
                            continue

        # Save recovered findings to isolated vault
        vault_data = {
            "last_audited": datetime.now().strftime("%Y-%m-%d %I:%M:%S %p"),
            "total_recovered_assets": len(recovered),
            "recovered_items": recovered[:30],  # Keep top 30
        }
        try:
            with open(self.recovered_path, "w", encoding="utf-8") as rf:
                json.dump(vault_data, rf, indent=2)
        except Exception as e:
            logger.warning(f"Failed to write recovered intelligence vault: {e}")

    def _walk_drive(self, drive_path, max_files=1500):
        code_map = {}
        count = 0
        for root, dirs, files in os.walk(drive_path):
            dirs[:] = [
                d for d in dirs if d not in self.ignore_dirs and not d.startswith("$")
            ]

            # Bound search depth per drive for performance
            rel_depth = root.replace(drive_path, "").count(os.sep)
            if rel_depth > 5:
                dirs.clear()
                continue

            for file in files:
                if count >= max_files:
                    break
                filepath = os.path.join(root, file)
                if self._should_include_file(filepath):
                    try:
                        with open(
                            filepath, "r", encoding="utf-8", errors="ignore"
                        ) as f:
                            snippet = f.read(
                                5000
                            )  # Store first 5000 chars for snippet RAG
                            code_map[filepath] = snippet
                            count += 1
                    except Exception:
                        continue
        return code_map

    def generate_context(self):
        logger.info(
            f"Generating global context payload across drives: {self.active_drives}"
        )
        start_time = time.time()

        all_grabbed_files = []
        all_snippets = {}

        # 1. Scan all active drives
        for drive in self.active_drives:
            drive_files = self._walk_drive(drive, max_files=800)
            for fp, snippet in drive_files.items():
                all_snippets[fp] = snippet
                try:
                    sz = os.path.getsize(fp)
                    mtime = os.path.getmtime(fp)
                except Exception:
                    sz = len(snippet.encode("utf-8"))
                    mtime = time.time()

                all_grabbed_files.append(
                    {
                        "path": fp,
                        "size": sz,
                        "ext": os.path.splitext(fp)[1],
                        "mtime": datetime.fromtimestamp(mtime).strftime(
                            "%Y-%m-%d %I:%M:%S %p"
                        ),
                        "snippet": snippet[:300],
                    }
                )

        # 2. Run Intelligence Recovery Audit
        self._audit_recovery_intelligence()

        # 3. Write Manifest
        manifest = {
            "last_updated": datetime.now().strftime("%Y-%m-%d %I:%M:%S %p"),
            "active_drives": self.active_drives,
            "total_files": len(all_grabbed_files),
            "total_bytes": sum(item["size"] for item in all_grabbed_files),
            "status": "Active (5-Drive Full PC RAG Ingestion)",
            "grabbed_files": all_grabbed_files,
        }

        with open(self.manifest_path, "w", encoding="utf-8") as mf:
            json.dump(manifest, mf, indent=2)

        logger.info(
            f"Context payload generated across {len(self.active_drives)} drives ({len(all_grabbed_files)} files) in {time.time() - start_time:.2f}s"
        )

    def run(self):
        logger.info("Context Ingestor Daemon started.")
        while True:
            try:
                self.generate_context()
            except Exception as e:
                logger.error(f"Error in generation loop: {e}")

            # Sleep for 60 seconds
            time.sleep(60)


if __name__ == "__main__":
    daemon = ContextIngestorDaemon()
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "--dry-run":
        daemon.generate_context()
    else:
        daemon.run()
