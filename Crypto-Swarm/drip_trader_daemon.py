"""
AI-BS Crypto Swarm - TWAP Drip Trader Daemon
Performs algorithmic Time-Weighted Average Price (TWAP) micro-allocations,
order slicing with randomized time-jitter, and transaction queue dispatching.
"""

import time
import json
import os
import sqlite3
import random
import argparse
import tempfile
from contextlib import closing
from pathlib import Path

DB_PATH = r"C:\AI-BS\Crypto-Swarm\trade_queue.db"
LOG_PATH = r"C:\AI-BS\logs\drip_trader_daemon.log"

_paper_db = None


def configure_paper_storage(directory):
    """Only a new database in an explicit OS temporary directory is a fixture."""
    global DB_PATH, _paper_db
    directory = Path(directory).resolve(strict=True)
    temp_root = Path(tempfile.gettempdir()).resolve()
    project = Path(__file__).resolve().parent.parent
    if not directory.is_relative_to(temp_root) or directory.is_relative_to(project):
        raise ValueError("Paper storage must be outside the project, under the OS temporary directory")
    candidate = directory / "paper_trade_queue.db"
    if candidate.exists():
        raise ValueError("Paper database must be new")
    DB_PATH = str(candidate)
    _paper_db = candidate


def require_paper_storage():
    path = Path(DB_PATH).resolve()
    if _paper_db is None or path != _paper_db or (path.exists() and path.stat().st_nlink != 1):
        raise RuntimeError("Simulation requires explicit isolated temporary paper storage")


def init_db():
    require_paper_storage()
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA synchronous=NORMAL;")
    conn.execute("""
        CREATE TABLE IF NOT EXISTS twap_plans (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            plan_id TEXT UNIQUE,
            asset TEXT,
            side TEXT,
            total_amount REAL,
            executed_amount REAL DEFAULT 0.0,
            remaining_amount REAL,
            num_slices INTEGER,
            executed_slices INTEGER DEFAULT 0,
            interval_seconds INTEGER,
            max_slippage_pct REAL,
            start_time REAL,
            next_slice_time REAL,
            status TEXT DEFAULT 'ACTIVE',
            created_at REAL
        );
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS drip_orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            plan_id TEXT,
            timestamp REAL,
            asset TEXT,
            side TEXT,
            amount REAL,
            price REAL,
            slippage_pct REAL,
            status TEXT,
            tx_hash TEXT
        );
    """)
    conn.commit()
    conn.close()

def create_twap_order(asset="SOL/USDC", side="BUY", total_amount=10.0, duration_minutes=60, num_slices=12, max_slippage_pct=0.5):
    init_db()
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    
    plan_id = f"twap_{int(time.time())}_{random.randint(1000, 9999)}"
    base_interval = int((duration_minutes * 60) / max(num_slices, 1))
    
    # Injected jitter for first slice (Â±10%)
    jitter = random.uniform(-0.1, 0.1) * base_interval
    first_slice_time = time.time() + max(2.0, base_interval + jitter)
    
    cur.execute("""
        INSERT INTO twap_plans (
            plan_id, asset, side, total_amount, executed_amount,
            remaining_amount, num_slices, executed_slices,
            interval_seconds, max_slippage_pct, start_time,
            next_slice_time, status, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        plan_id, asset, side, total_amount, 0.0,
        total_amount, num_slices, 0,
        base_interval, max_slippage_pct, time.time(),
        first_slice_time, 'ACTIVE', time.time()
    ))
    conn.commit()
    conn.close()
    
    print(f"[TWAP_DAEMON] Created TWAP plan {plan_id}: {side} {total_amount} {asset} across {num_slices} slices over {duration_minutes}m.")
    return plan_id

def process_active_twap_orders(simulated_price=142.50):
    """Paper execution only; this function never represents live fills."""
    init_db()
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    
    now = time.time()
    cur.execute("SELECT * FROM twap_plans WHERE status = 'ACTIVE' AND next_slice_time <= ?", (now,))
    active_plans = cur.fetchall()
    
    executed_count = 0
    for plan in active_plans:
        slice_amount = plan['total_amount'] / plan['num_slices']
        slice_amount = min(slice_amount, plan['remaining_amount'])
        
        # Calculate simulated slippage
        random_slippage = random.uniform(0.01, 0.15)
        if random_slippage > plan['max_slippage_pct']:
            print(f"[TWAP_DAEMON] Slippage threshold exceeded ({random_slippage:.2f}% > {plan['max_slippage_pct']}%). Retrying next tick.")
            continue
            
        executed_slices = plan['executed_slices'] + 1
        executed_amount = plan['executed_amount'] + slice_amount
        remaining_amount = max(0.0, plan['total_amount'] - executed_amount)
        
        # Next randomized jitter interval
        jitter = random.uniform(-0.15, 0.15) * plan['interval_seconds']
        next_time = now + max(5.0, plan['interval_seconds'] + jitter)
        new_status = 'COMPLETED' if remaining_amount <= 0.0001 or executed_slices >= plan['num_slices'] else 'ACTIVE'
        
        cur.execute("""
            UPDATE twap_plans
            SET executed_slices = ?, executed_amount = ?, remaining_amount = ?,
                next_slice_time = ?, status = ?
            WHERE plan_id = ?
        """, (executed_slices, executed_amount, remaining_amount, next_time, new_status, plan['plan_id']))
        
        # Record execution
        tx_hash = f"tx_sim_{int(now)}_{random.randint(100000, 999999)}"
        cur.execute("""
            INSERT INTO drip_orders (
                plan_id, timestamp, asset, side, amount, price, slippage_pct, status, tx_hash
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (plan['plan_id'], now, plan['asset'], plan['side'], slice_amount, simulated_price, random_slippage, 'PAPER_FILLED', tx_hash))
        
        executed_count += 1
        print(f"[TWAP_DAEMON] Executed slice {executed_slices}/{plan['num_slices']} for {plan['plan_id']}: {plan['side']} {slice_amount:.4f} {plan['asset']} @ ${simulated_price} (Tx: {tx_hash})")
        
    conn.commit()
    conn.close()
    return executed_count

def get_twap_status():
    init_db()
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    
    cur.execute("SELECT * FROM twap_plans ORDER BY created_at DESC LIMIT 10")
    plans = [dict(row) for row in cur.fetchall()]
    
    cur.execute("SELECT * FROM drip_orders ORDER BY timestamp DESC LIMIT 15")
    orders = [dict(row) for row in cur.fetchall()]
    
    conn.close()
    return {"plans": plans, "recent_orders": orders}

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="AI-BS Crypto Swarm TWAP Drip Trader")
    parser.add_argument("--simulate", action="store_true", help="Create and process a simulation TWAP order")
    parser.add_argument("--status", action="store_true", help="Print active TWAP plans and orders")
    args = parser.parse_args()
    
    if args.simulate:
        with tempfile.TemporaryDirectory(prefix="aibs_crypto_paper_") as directory:
            configure_paper_storage(directory)
            pid = create_twap_order("SOL/USDC", "BUY", 12.0, 10, 6, 0.5)
            with closing(sqlite3.connect(DB_PATH)) as conn, conn:
                conn.execute("UPDATE twap_plans SET next_slice_time = ? WHERE plan_id = ?", (time.time() - 1, pid))
            process_active_twap_orders()
            print(json.dumps({"mode": "paper", **get_twap_status()}, indent=2))
    elif args.status:
        # Read-only inspection must not initialize or migrate the canonical queue.
        uri = Path(DB_PATH).resolve().as_uri() + "?mode=ro"
        with closing(sqlite3.connect(uri, uri=True)) as conn:
            conn.row_factory = sqlite3.Row
            plans = [dict(row) for row in conn.execute("SELECT * FROM twap_plans ORDER BY created_at DESC LIMIT 10")]
            print(json.dumps({"mode": "historical_unverified", "plans": plans}, indent=2))
    else:
        print("[TWAP_DAEMON] Standby; live dispatch held. --simulate uses isolated temporary storage.")
