import os
import sqlite3
import subprocess
import requests

def get_gpu_telemetry():
    try:
        out = subprocess.check_output(
            ["nvidia-smi", "--query-gpu=temperature.gpu,power.draw,power.limit,clocks.current.graphics,clocks.current.memory,utilization.gpu", "--format=csv,noheader,nounits"],
            encoding="utf-8"
        ).strip()
        parts = [p.strip() for p in out.split(",")]
        return {
            "temp": int(parts[0]),
            "power_draw": float(parts[1]),
            "power_limit": float(parts[2]),
            "core_clock": int(parts[3]),
            "mem_clock": int(parts[4]),
            "util": int(parts[5])
        }
    except Exception as e:
        return {"error": str(e)}

def get_pearl_telemetry():
    wallet = "prl1p5r4kvz636h2pa9fuww723s4r02flt25rec9qs6yjckk7lyejkvjs67a4n5"
    url = f"https://pearl.herominers.com/api/stats_address?address={wallet}&recentBlocksAmount=10"
    try:
        r = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=5).json()
        stats = r.get("stats", {})
        nh = int(stats.get("networkHeight") or 0)
        bal = float(stats.get("balance") or 0) / 1e8
        shares = int(stats.get("shares_good") or 0)
        unconf = r.get("unconfirmed", [])
        pending = sum(float(b.get("reward") or 0) for b in unconf) / 1e8
        closest = None
        min_rem = 999
        for b in unconf:
            h = int(b.get("height") or 0)
            confs = nh - h if nh and h else 0
            rem = max(0, 100 - confs)
            if rem < min_rem:
                min_rem = rem
                closest = (h, confs, rem)
        return {
            "height": nh,
            "mature_prl": bal,
            "shares": shares,
            "pending_prl": pending,
            "pending_count": len(unconf),
            "closest": closest
        }
    except Exception as e:
        return {"error": str(e)}

def get_trader_telemetry():
    try:
        r = requests.get("http://127.0.0.1:8007/api/v1/telemetry", timeout=3).json()
        ledger = r.get("ledger", {})
        prices = ledger.get("reference_prices", {})
        return {
            "status": r.get("status", "unknown"),
            "cro_usd": prices.get("CRO/USD", 0.0),
            "strategy": ledger.get("strategy_layer", "Dual Strategy")
        }
    except Exception as e:
        return {"error": str(e)}

def get_ledger_records():
    db_path = r"C:\AI-BS\backend\aibs_master.db"
    if not os.path.exists(db_path):
        return []
    try:
        conn = sqlite3.connect(db_path)
        cur = conn.cursor()
        cur.execute("SELECT date, asset, amount, usd_total_value, source_account, dest_account, tx_hash FROM crypto_transfers ORDER BY id DESC LIMIT 5")
        rows = cur.fetchall()
        conn.close()
        return rows
    except Exception:
        return []

print("GPU:", get_gpu_telemetry())
print("Pearl:", get_pearl_telemetry())
print("Trader:", get_trader_telemetry())
print("Ledger:", get_ledger_records())
