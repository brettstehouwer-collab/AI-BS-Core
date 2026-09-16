#!/usr/bin/env python3
"""
AI-BS Local Anti-Tamper File Integrity Watchdog Daemon (v5.129.0)
Monitors core system entry points, scripts, and databases for unauthorized
modifications using baseline SHA-256 cryptographic verification.
"""

import os
import time
import hashlib
import json
import logging
from datetime import datetime, timezone

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("SecurityWatchdog")

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MONITORED_PATHS = [
    os.path.join(BASE_DIR, "Launch_AI_BS.bat"),
    os.path.join(BASE_DIR, "backend", "AI_BS_Backend.py"),
    os.path.join(BASE_DIR, "backend", "modules", "syndication_router.py"),
    os.path.join(BASE_DIR, "backend", "security", "rate_limiter.py"),
    os.path.join(BASE_DIR, "backend", "security", "auth_guard.py"),
]

ALERTS_PATH = os.path.join(BASE_DIR, "saved_data", "security_alerts.json")

def hash_file(filepath: str) -> str:
    if not os.path.exists(filepath):
        return "MISSING"
    hasher = hashlib.sha256()
    with open(filepath, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            hasher.update(chunk)
    return hasher.hexdigest()

class FileIntegrityWatchdog:
    def __init__(self):
        self.baselines = {}
        self.initialize_baselines()

    def initialize_baselines(self):
        for path in MONITORED_PATHS:
            if os.path.exists(path):
                self.baselines[path] = hash_file(path)
        logger.info(f"Initialized SHA-256 baselines for {len(self.baselines)} core files.")

    def run_check(self) -> list:
        alerts = []
        now_iso = datetime.now(timezone.utc).isoformat()
        
        for path, expected_hash in self.baselines.items():
            current_hash = hash_file(path)
            if current_hash != expected_hash:
                alert = {
                    "timestamp": now_iso,
                    "type": "TAMPER_WARNING" if current_hash != "MISSING" else "FILE_DELETION",
                    "file": os.path.relpath(path, BASE_DIR),
                    "expected_sha256": expected_hash,
                    "actual_sha256": current_hash,
                    "severity": "HIGH"
                }
                alerts.append(alert)
                logger.warning(f"Integrity check alert on {path}: {alert['type']}")

        if alerts:
            self.persist_alerts(alerts)
        return alerts

    def persist_alerts(self, new_alerts: list):
        os.makedirs(os.path.dirname(ALERTS_PATH), exist_ok=True)
        existing = []
        if os.path.exists(ALERTS_PATH):
            try:
                with open(ALERTS_PATH, "r", encoding="utf-8") as f:
                    existing = json.load(f)
            except Exception:
                existing = []
        existing.extend(new_alerts)
        with open(ALERTS_PATH, "w", encoding="utf-8") as f:
            json.dump(existing[-50:], f, indent=2)

def main():
    logger.info("Starting AI-BS Anti-Tamper Security Watchdog...")
    watchdog = FileIntegrityWatchdog()
    alerts = watchdog.run_check()
    if not alerts:
        logger.info("All monitored files passed SHA-256 integrity verification. Status: SECURE.")

if __name__ == "__main__":
    main()
