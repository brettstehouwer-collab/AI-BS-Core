"""
Autonomous 24-Hour Recurring Batch Dispatcher for Recreational Debut
Orchestrates 400-email batches every 24 hours until all student-athletes are contacted.
Preserves Dennis Bell Caller ID, ensures $0.00 zero-cost via Google SMTP,
and enforces strict 400/day pacing to protect email reputation.
"""

import os
import sys
import time
import json
import sqlite3
import argparse
import urllib.request
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Any, Optional

BASE_DIR = Path(__file__).resolve().parent.parent.parent
DB_PATH = BASE_DIR / "saved_data" / "rec_debut.db"
STATE_PATH = BASE_DIR / "saved_data" / "rec_debut_scheduler_state.json"
LOG_PATH = BASE_DIR / "saved_data" / "rec_debut_daily_scheduler.log"

API_BASE = "http://127.0.0.1:8080/api/v1/recdebut"
BATCH_SIZE = 400
INTERVAL_SECONDS = 86400  # 24 Hours

PROMPT = """Hey {first_name}, this is Dennis Bell, former New York Knick and President of Recreational Debut.

Your talent caught our attention in Las Vegas, and we believe you have the potential to play at the college level.

We’ve helped more than 100 student-athletes get recruited, and we want to help get your athletic profile in front of 850+ college coaches nationwide.

If playing college sports is your goal, don’t wait for coaches to find you.

📱 Call or text: +1-616-291-5227
✅ Register FREE: RecDebut.com
📧 dbell002@sbcglobal.net

Let’s get you recruited!

Dennis Bell
Former New York Knicks
President, Recreational Debut"""

def log(msg: str):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    formatted = f"[{timestamp}] {msg}"
    print(formatted, flush=True)
    try:
        LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(LOG_PATH, "a", encoding="utf-8") as f:
            f.write(formatted + "\n")
    except Exception:
        pass

def load_state() -> Dict[str, Any]:
    if STATE_PATH.exists():
        try:
            with open(STATE_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            log(f"Warning: Failed to load scheduler state file: {e}")

    # Default state if not existing
    now = time.time()
    return {
        "scheduler_active": False,
        "batch_size": BATCH_SIZE,
        "interval_seconds": INTERVAL_SECONDS,
        "last_batch_time": 1791733374.0,  # Batch 1 launch timestamp (Oct 11, ~11:42 AM)
        "last_batch_job_id": "broadcast_1791733374",
        "next_batch_number": 2,
        "next_batch_scheduled_at": 1791733374.0 + INTERVAL_SECONDS,
        "next_batch_scheduled_iso": datetime.fromtimestamp(1791733374.0 + INTERVAL_SECONDS).strftime("%Y-%m-%d %H:%M:%S"),
        "batches": [
            {
                "batch_number": 1,
                "job_id": "broadcast_1791733374",
                "started_at": 1791733374.0,
                "started_iso": datetime.fromtimestamp(1791733374.0).strftime("%Y-%m-%d %H:%M:%S"),
                "recipients_targeted": 400,
                "status": "RUNNING",
                "sent": 0,
                "failed": 0
            }
        ],
        "created_at": now,
        "updated_at": now
    }

def save_state(state: Dict[str, Any]):
    state["updated_at"] = time.time()
    try:
        STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(STATE_PATH, "w", encoding="utf-8") as f:
            json.dump(state, f, indent=2)
    except Exception as e:
        log(f"Error saving scheduler state: {e}")

def get_pending_count() -> int:
    try:
        conn = sqlite3.connect(str(DB_PATH))
        c = conn.cursor()
        count = c.execute(
            "SELECT COUNT(id) FROM rec_debut_athletes WHERE (email IS NOT NULL AND email != '') AND (status IS NULL OR status = 'Pending' OR status = 'Selected')"
        ).fetchone()[0]
        conn.close()
        return count
    except Exception as e:
        log(f"Error querying pending athletes: {e}")
        return 0

def get_total_contacted_count() -> int:
    try:
        conn = sqlite3.connect(str(DB_PATH))
        c = conn.cursor()
        count = c.execute(
            "SELECT COUNT(id) FROM rec_debut_athletes WHERE status = 'Contacted' OR status = 'Messaged'"
        ).fetchone()[0]
        conn.close()
        return count
    except Exception as e:
        return 0

def get_broadcast_status() -> Dict[str, Any]:
    url = f"{API_BASE}/broadcast/status"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "AI-BS-Scheduler/1.0"})
        with urllib.request.urlopen(req, timeout=5) as res:
            return json.loads(res.read().decode())
    except Exception:
        return {"success": False, "active": False, "status": "OFFLINE"}

def trigger_batch(batch_limit: int = 400) -> Optional[Dict[str, Any]]:
    raise RuntimeError("RecDebut review hold: automated dispatch is disabled.")
    payload = {
        "message_text": PROMPT,
        "campaign_type": "email",
        "subject_line": "Dennis Bell (Former New York Knick) - Recreational Debut",
        "caller_id_email": "dbell002@sbcglobal.net",
        "caller_id_phone": "+1-616-291-5227",
        "caller_id_name": "Dennis Bell (+1-616-291-5227)",
        "batch_limit": batch_limit,
        "dry_run": False,
        "use_swarm": True
    }
    url = f"{API_BASE}/broadcast"
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=10) as res:
            res_data = json.loads(res.read().decode())
            log(f"Batch dispatch request succeeded: {res_data.get('message')}")
            return res_data
    except Exception as e:
        log(f"Error triggering batch broadcast: {e}")
        return None

def format_countdown(seconds: float) -> str:
    if seconds <= 0:
        return "NOW (Ready to dispatch)"
    td = timedelta(seconds=int(seconds))
    hours, remainder = divmod(td.seconds, 3600)
    minutes, secs = divmod(remainder, 60)
    days = td.days
    parts = []
    if days > 0:
        parts.append(f"{days}d")
    if hours > 0 or days > 0:
        parts.append(f"{hours}h")
    parts.append(f"{minutes}m")
    parts.append(f"{secs}s")
    return " ".join(parts)

def show_status():
    state = load_state()
    pending = get_pending_count()
    contacted = get_total_contacted_count()
    b_status = get_broadcast_status()

    next_run = state.get("next_batch_scheduled_at", 0)
    remaining_sec = next_run - time.time()

    print("\n=======================================================")
    print("   RECREATIONAL DEBUT 24-HOUR AUTONOMOUS SCHEDULER")
    print("=======================================================")
    print(f"Status:               {'ACTIVE' if state.get('scheduler_active') else 'INACTIVE'}")
    print(f"Pending Athletes:     {pending}")
    print(f"Contacted Athletes:   {contacted}")
    print(f"Live Broadcast:       {b_status.get('status')} (Active: {b_status.get('active', False)})")
    if b_status.get("active"):
        print(f" - Progress:          {b_status.get('sent', 0)} / {b_status.get('total', 0)} ({b_status.get('progress_pct', 0)}%)")
        print(f" - Current Recipient: {b_status.get('current_athlete')} ({b_status.get('current_phone')})")
    print(f"Next Batch:           Batch #{state.get('next_batch_number', 2)}")
    print(f"Next Scheduled Time:  {state.get('next_batch_scheduled_iso')} (Local)")
    print(f"Countdown:            {format_countdown(remaining_sec)}")
    print(f"Batch Size:           {state.get('batch_size', 400)} emails per cycle")
    print(f"Interval:             {state.get('interval_seconds', 86400) // 3600} hours (24h cooldown)")
    print("\nBatch History:")
    for b in state.get("batches", []):
        print(f" - Batch #{b.get('batch_number')}: {b.get('status')} | Targeted: {b.get('recipients_targeted', 0)} | Sent: {b.get('sent', 0)} | Started: {b.get('started_iso')}")
    print("=======================================================\n")

def run_scheduler_daemon():
    raise RuntimeError("RecDebut review hold: automated dispatch is disabled.")
    log("================================================================")
    log("=== Recreational Debut 24-Hour Autonomous Scheduler Activated ===")
    log("================================================================")

    state = load_state()
    last_heartbeat = 0

    while True:
        try:
            state = load_state()
            if not state.get("scheduler_active"):
                log("Scheduler is marked INACTIVE in state. Halting daemon loop.")
                break

            # 1. Check live broadcast status
            b_status = get_broadcast_status()
            is_broadcasting = b_status.get("active", False) or b_status.get("status") == "RUNNING"

            # Update batch history if active batch finished
            if state.get("batches"):
                latest_batch = state["batches"][-1]
                if latest_batch.get("status") == "RUNNING":
                    if is_broadcasting:
                        latest_batch["sent"] = b_status.get("sent", 0)
                        latest_batch["failed"] = b_status.get("failed", 0)
                    else:
                        terminal_status = b_status.get("status", "COMPLETED")
                        latest_batch["status"] = terminal_status if terminal_status != "IDLE" else "COMPLETED"
                        latest_batch["sent"] = b_status.get("sent", latest_batch.get("recipients_targeted", 400))
                        latest_batch["failed"] = b_status.get("failed", 0)
                        latest_batch["completed_at"] = time.time()
                        latest_batch["completed_iso"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        log(f"Batch #{latest_batch.get('batch_number')} marked {latest_batch['status']} with {latest_batch['sent']} sent, {latest_batch['failed']} failed.")
                        save_state(state)

            # 2. Check if all athletes reached
            pending = get_pending_count()
            if pending <= 0 and not is_broadcasting:
                log("🎉 100% OF ELIGIBLE STUDENT-ATHLETES HAVE BEEN CONTACTED!")
                log("All campaign targets reached. Scheduler cycle completed.")
                state["scheduler_active"] = False
                save_state(state)
                break

            # 3. If currently broadcasting, wait for batch completion
            if is_broadcasting:
                log(f"[MONITOR] Batch #{state.get('batches', [{}])[-1].get('batch_number', 1)} transmitting: {b_status.get('sent', 0)}/{b_status.get('total', 400)} ({b_status.get('progress_pct', 0)}%)")
                time.sleep(30)
                continue

            # 4. Check time until next batch
            now = time.time()
            next_batch_time = state.get("next_batch_scheduled_at", now)
            seconds_remaining = next_batch_time - now

            # Heartbeat log every 10 minutes (600s)
            if now - last_heartbeat >= 600:
                contacted = get_total_contacted_count()
                log(f"[HEARTBEAT] Next Batch #{state.get('next_batch_number', 2)} in {format_countdown(seconds_remaining)} | Contacted: {contacted} | Remaining: {pending}")
                last_heartbeat = now

            if seconds_remaining <= 0:
                # Time to fire next batch!
                batch_num = state.get("next_batch_number", 2)
                batch_limit = min(state.get("batch_size", 400), pending)
                log(f"\n🚀 [TIME TRIGGER] 24-Hour Cooldown Expired! Launching Batch #{batch_num} ({batch_limit} athletes)...")
                
                res = trigger_batch(batch_limit)
                if res and res.get("success"):
                    job_id = res.get("job_id", f"broadcast_{int(now)}")
                    new_batch = {
                        "batch_number": batch_num,
                        "job_id": job_id,
                        "started_at": now,
                        "started_iso": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        "recipients_targeted": batch_limit,
                        "status": "RUNNING",
                        "sent": 0,
                        "failed": 0
                    }
                    state["batches"].append(new_batch)
                    state["last_batch_time"] = now
                    state["last_batch_job_id"] = job_id
                    state["next_batch_number"] = batch_num + 1
                    next_run = now + INTERVAL_SECONDS
                    state["next_batch_scheduled_at"] = next_run
                    state["next_batch_scheduled_iso"] = datetime.fromtimestamp(next_run).strftime("%Y-%m-%d %H:%M:%S")
                    save_state(state)
                    log(f"Batch #{batch_num} dispatched! Next Batch #{batch_num + 1} scheduled for {state['next_batch_scheduled_iso']} (24h cooldown).")
                    time.sleep(30)
                else:
                    log(f"⚠️ Batch #{batch_num} trigger encountered an issue. Retrying in 15 minutes...")
                    time.sleep(900)
            else:
                # Sleep in short increments for responsiveness
                sleep_duration = min(60, max(5, seconds_remaining))
                time.sleep(sleep_duration)

                # 5. Check for new student-athlete replies and auto-route to Dennis Bell (+1-616-291-5227)
                try:
                    sync_url = f"{API_BASE}/sms/sync-replies"
                    req_sync = urllib.request.Request(sync_url, headers={"User-Agent": "AI-BS-Scheduler/1.0"}, data=b"", method="POST")
                    with urllib.request.urlopen(req_sync, timeout=10) as s_res:
                        s_data = json.loads(s_res.read().decode())
                        if s_data.get("new_replies_count", 0) > 0:
                            log(f"💬 [INBOUND ROUTER] Detected {s_data['new_replies_count']} new athlete replies! Routed directly to Dennis Bell (+1-616-291-5227).")
                except Exception:
                    pass

        except Exception as e:
            log(f"Scheduler exception: {e}")
            time.sleep(60)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Recreational Debut 24-Hour Autonomous Scheduler")
    parser.add_argument("--status", action="store_true", help="Print scheduler status and exit")
    parser.add_argument("--trigger-now", action="store_true", help="Trigger next batch immediately")
    parser.add_argument("--daemon", action="store_true", default=True, help="Run scheduler daemon continuously")
    args = parser.parse_args()

    if args.status:
        show_status()
    elif args.trigger_now:
        p = get_pending_count()
        if p <= 0:
            print("No pending athletes remaining to message.")
        else:
            limit = min(400, p)
            print(f"Triggering immediate batch of {limit} athletes...")
            trigger_batch(limit)
    else:
        run_scheduler_daemon()
