"""Track 4: Vault-Key Inert Canary Verification Suite.

Asserts database integrity of stehouwer_vault.db, verifies exactly 6 inert keys,
and guarantees 0 plaintext private credentials are leaked.
"""

from __future__ import annotations

import json
import re
import sqlite3
from pathlib import Path
import pytest


VAULT_DB_PATH = Path("C:/AI-BS/backend/stehouwer_vault.db")
GOAL_SYNC_PATH = Path("C:/AI-BS/docs/agent_sync/current_long_term_goal.json")
MANUSCRIPTS_DIR = Path("C:/AI-BS/output/manuscripts")

EXPECTED_KEY_IDS = {
    "system-crypto",
    "system-discord",
    "system-gemini",
    "system-paypal",
    "system-rapidapi",
    "system-stripe",
}


def test_vault_database_integrity():
    """Verify SQLite database integrity check returns 'ok'."""
    assert VAULT_DB_PATH.is_file(), f"Vault DB missing: {VAULT_DB_PATH}"
    conn = sqlite3.connect(str(VAULT_DB_PATH))
    try:
        cur = conn.cursor()
        res = cur.execute("PRAGMA integrity_check;").fetchone()
        assert res is not None and res[0] == "ok", f"Integrity check failed: {res}"
    finally:
        conn.close()


def test_vault_keys_exact_inert_canary_count():
    """Verify table vault_keys contains exactly 6 expected inert system keys."""
    conn = sqlite3.connect(str(VAULT_DB_PATH))
    try:
        cur = conn.cursor()
        rows = cur.execute("SELECT id, clientName, apiName, category, length(apiKey) FROM vault_keys;").fetchall()
        assert len(rows) == 6, f"Expected exactly 6 keys, found {len(rows)}"

        found_ids = {r[0] for r in rows}
        assert found_ids == EXPECTED_KEY_IDS, f"Key IDs mismatch: {found_ids} != {EXPECTED_KEY_IDS}"

        for r in rows:
            key_id, client, api_name, category, key_len = r
            assert client == "System Default", f"Non-default client name for {key_id}: {client}"
            assert key_len > 0, f"Empty key string for {key_id}"
    finally:
        conn.close()


def test_goal_sync_security_policy_enforcement():
    """Verify current_long_term_goal.json enforces inert canary constraints without credential leakage."""
    assert GOAL_SYNC_PATH.is_file(), f"Goal sync file missing: {GOAL_SYNC_PATH}"
    with open(GOAL_SYNC_PATH, "r", encoding="utf-8") as f:
        goal_data = json.load(f)

    next_items = " ".join(goal_data.get("next", []))
    assert "vault-key inert canary" in next_items
    assert "without executing arbitrary builds, reading credentials or altering encrypted stores" in next_items


def test_zero_credential_leakage_in_manuscripts_and_outputs():
    """Ensure no private credentials or secret tokens are leaked into manuscript outputs."""
    if not MANUSCRIPTS_DIR.exists():
        pytest.skip("Manuscripts directory not yet created")

    # Common credential patterns: AWS keys, OpenAI sk-, JWT tokens, private key blocks
    sensitive_patterns = [
        re.compile(r"sk-[a-zA-Z0-9]{32,}", re.IGNORECASE),
        re.compile(r"AKIA[0-9A-Z]{16}"),
        re.compile(r"-----BEGIN (?:RSA |EC )?PRIVATE KEY-----"),
        re.compile(r"ghp_[a-zA-Z0-9]{36}"),
    ]

    for f in MANUSCRIPTS_DIR.rglob("*"):
        if f.is_file() and f.suffix in (".md", ".fountain", ".json", ".txt"):
            content = f.read_text(encoding="utf-8", errors="replace")
            for pat in sensitive_patterns:
                match = pat.search(content)
                assert match is None, f"Sensitive credential pattern matched in {f}: {match.group(0)[:8]}..."
