"""Comprehensive Verification Script for Milestone M1 Concurrency Gate."""
import json
from pathlib import Path
import sqlite3
import sys
import tempfile

ROOT = Path("C:/AI-BS")
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "backend"))

from backend.db.swarm_sqlite import SQLiteStore, SQLitePolicy, DATABASES
from backend.core.swarm_orchestration import (
    SwarmRegistry, Policy, ROLES, AdmissionError, OwnershipViolation, load_policy
)

def verify_databases():
    print("=== Verifying Databases ===")
    
    # 1. backend/aibs_master.db
    backend_db = ROOT / "backend/aibs_master.db"
    assert backend_db.exists(), f"Backend DB missing: {backend_db}"
    cb = sqlite3.connect(f"file:{backend_db}?mode=ro", uri=True)
    b_mode = cb.execute("PRAGMA journal_mode;").fetchone()[0]
    b_qc = cb.execute("PRAGMA quick_check;").fetchall()
    b_tbls = len(cb.execute("SELECT name FROM sqlite_master WHERE type='table';").fetchall())
    cb.close()
    print(f"Backend DB ({backend_db}): mode={b_mode}, quick_check={b_qc}, tables={b_tbls}")
    assert b_mode.lower() == "wal", f"Backend DB not WAL: {b_mode}"
    assert b_qc == [("ok",)], f"Backend DB integrity failed: {b_qc}"
    assert b_tbls >= 40, f"Backend DB unexpected table count: {b_tbls}"

    # 2. database/aibs_master.db
    cdz_db = ROOT / "database/aibs_master.db"
    assert cdz_db.exists(), f"CDZ DB missing: {cdz_db}"
    cc = sqlite3.connect(f"file:{cdz_db}?mode=ro", uri=True)
    c_mode = cc.execute("PRAGMA journal_mode;").fetchone()[0]
    c_qc = cc.execute("PRAGMA quick_check;").fetchall()
    c_tbls = [row[0] for row in cc.execute("SELECT name FROM sqlite_master WHERE type='table';").fetchall()]
    cc.close()
    print(f"CDZ DB ({cdz_db}): mode={c_mode}, quick_check={c_qc}, tables={c_tbls}")
    assert c_mode.lower() == "wal", f"CDZ DB not WAL: {c_mode}"
    assert c_qc == [("ok",)], f"CDZ DB integrity failed: {c_qc}"
    assert "cdz_audit_ledger" in c_tbls, "cdz_audit_ledger missing"

    # 3. database/aibs_master_backup_pre_wal.db
    backup_db = ROOT / "database/aibs_master_backup_pre_wal.db"
    assert backup_db.exists(), f"Pre-activation backup missing: {backup_db}"
    cbk = sqlite3.connect(f"file:{backup_db}?mode=ro", uri=True)
    bk_mode = cbk.execute("PRAGMA journal_mode;").fetchone()[0]
    bk_qc = cbk.execute("PRAGMA quick_check;").fetchall()
    bk_tbls = [row[0] for row in cbk.execute("SELECT name FROM sqlite_master WHERE type='table';").fetchall()]
    cbk.close()
    print(f"Backup DB ({backup_db}): mode={bk_mode}, quick_check={bk_qc}, tables={bk_tbls}")
    assert bk_qc == [("ok",)], f"Backup DB integrity failed: {bk_qc}"
    assert sorted(c_tbls) == sorted(bk_tbls), "Table mismatch between CDZ DB and backup"

    print("[PASS] All database checks passed successfully.\n")

def verify_bounded_writer_parameters():
    print("=== Verifying Bounded Writer Parameters ===")
    policy = SQLitePolicy()
    print(f"SQLitePolicy: max_readers={policy.max_readers}, max_pending_writes={policy.max_pending_writes}, busy_timeout_ms={policy.busy_timeout_ms}, cache_size_kib={policy.cache_size_kib}")
    assert policy.max_readers == 8, f"Expected max_readers=8, got {policy.max_readers}"
    assert policy.max_pending_writes == 128, f"Expected max_pending_writes=128, got {policy.max_pending_writes}"
    
    # Verify store single writer thread & reader semaphore
    store = SQLiteStore(ROOT, "cdz_audit", policy)
    assert store._read_slots._value == 8, "Reader bounded semaphore not initialized to 8"
    assert store._queue.maxsize == 128, "Queue maxsize not initialized to 128"
    print("[PASS] Bounded writer queue parameters verified (max 1 writer thread, max 8 readers).\n")

def verify_orchestration_config_and_roles():
    print("=== Verifying Swarm Orchestration Config & Admission Ceiling ===")
    config_path = ROOT / "config/swarm_orchestration.json"
    conf = json.loads(config_path.read_text())
    
    # Check activation flags
    print(f"Activation: {conf['activation']}")
    assert conf["activation"] == {"automatic_start": True, "live_database_changes": True, "provider_calls": False}
    
    # Check 5 roles
    print(f"Roles ({len(conf['roles'])}): {conf['roles']}")
    expected_roles = ["lead_orchestrator", "test_runner", "frontend_ui_worker", "native_ui_worker", "database_state_worker"]
    assert conf["roles"] == expected_roles, f"Roles mismatch: {conf['roles']}"
    assert tuple(expected_roles) == ROLES
    
    # Check admission ceiling (4 agents, 3 workers)
    adm = conf["admission"]
    print(f"Admission: max_active_agents={adm['max_active_agents']}, max_active_workers={adm['max_active_workers']}")
    assert adm["max_active_agents"] == 4, f"Expected 4 active agents, got {adm['max_active_agents']}"
    assert adm["max_active_workers"] == 3, f"Expected 3 active workers, got {adm['max_active_workers']}"
    
    # Test load_policy
    loaded_pol = load_policy(config_path)
    assert loaded_pol == Policy(max_active_agents=4, max_active_workers=3)
    print("load_policy returned matching Policy object.")
    
    # Test SwarmRegistry admission enforcement
    with tempfile.TemporaryDirectory() as tmp:
        reg = SwarmRegistry(tmp, loaded_pol)
        
        # Test 1: Reject invalid role
        try:
            reg.acquire("t0", "rogue_agent", [])
            assert False, "Should have rejected rogue role"
        except AdmissionError as e:
            print(f"Invalid role rejected: {e}")
            
        # Test 2: Acquire lead + 3 workers = 4 slots
        l_lead = reg.acquire("task_lead", "lead_orchestrator", [])
        l_w1 = reg.acquire("task_w1", "test_runner", [])
        l_w2 = reg.acquire("task_w2", "frontend_ui_worker", [])
        l_w3 = reg.acquire("task_w3", "native_ui_worker", [])
        
        # Test 3: 5th role rejected due to 4-slot ceiling
        try:
            reg.acquire("task_db", "database_state_worker", [])
            assert False, "Should have rejected 5th concurrent task"
        except AdmissionError as e:
            print(f"5th concurrent task rejected at ceiling: {e}")
            
        # Release 1 worker, then 5th role database_state_worker succeeds
        reg.finish(l_w3)
        l_db = reg.acquire("task_db", "database_state_worker", [])
        print("database_state_worker admitted after slot release.")
        
        # Clean up
        reg.finish(l_lead)
        reg.finish(l_w1)
        reg.finish(l_w2)
        reg.finish(l_db)
        assert reg.is_drained()
        print("SwarmRegistry drained cleanly.")
        
    print("[PASS] 5-role / 4-slot scheduling ceiling verified across registry.\n")

if __name__ == "__main__":
    verify_databases()
    verify_bounded_writer_parameters()
    verify_orchestration_config_and_roles()
    print("ALL M1 VERIFICATIONS PASSED WITH ZERO ERRORS!")
