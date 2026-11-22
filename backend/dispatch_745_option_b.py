import os
import re
import csv
import time
import json
import hashlib
import sqlite3
import requests
from pathlib import Path

DB_PATH = Path(r"C:\AI-BS\saved_data\rec_debut.db")


def load_credentials():
    creds = {}
    env_paths = [
        Path(r"C:\AI-BS\.env"),
        Path(r"C:\AI-BS\backend\.env"),
        Path(r"C:\Recreational-Debut\.env"),
    ]
    for p in env_paths:
        if p.exists():
            for line in p.read_text(encoding="utf-8", errors="ignore").splitlines():
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, v = line.split("=", 1)
                    creds[k.strip()] = v.strip().strip('"').strip("'")
    return creds


def get_personal_exclusion_set():
    personal_phones = {
        "6164023628",
        "6162915227",
        "6164067993",
        "6168027774",
        "6162995026",
    }
    csv_candidates = [
        Path(r"C:\AI-BS\MyPhoneContacts.csv"),
        Path(r"C:\AI-BS\saved_data\MyPhoneContacts.csv"),
        Path(r"C:\Users\footb\Downloads\MyPhoneContacts.csv"),
    ]
    for cp in csv_candidates:
        if cp.exists():
            try:
                with open(cp, "r", encoding="utf-8", errors="ignore") as f:
                    for row in csv.reader(f):
                        for cell in row:
                            digits = re.sub(r"\D", "", cell or "")
                            if len(digits) == 10:
                                personal_phones.add(digits)
                            elif len(digits) == 11 and digits.startswith("1"):
                                personal_phones.add(digits[-10:])
            except Exception:
                pass
    return personal_phones


def safe_sqlite_backup(src_conn: sqlite3.Connection):
    targets = [
        r"C:\AI-BS\backend\rec_debut.db",
        r"C:\Recreational-Debut\saved_data\rec_debut.db",
        r"C:\Recreational-Debut\backend\rec_debut.db",
    ]
    for t in targets:
        os.makedirs(os.path.dirname(t), exist_ok=True)
        dst_conn = sqlite3.connect(t, timeout=30.0)
        src_conn.backup(dst_conn)
        dst_conn.close()
    print("[DB BACKUP] Atomic SQLite backup completed across all 4 mirrors.", flush=True)


def main():
    creds = load_credentials()
    textbee_device = (
        os.environ.get("TEXTBEE_DEVICE_ID")
        or creds.get("TEXTBEE_DEVICE_ID")
        or "6ad7b28560b1138230badd0a"
    ).strip()
    textbee_key = (
        os.environ.get("TEXTBEE_API_KEY")
        or creds.get("TEXTBEE_API_KEY")
        or "txb_rAZOZNMuTEKtlxQ30hfcJd05dL2KlVRu"
    ).strip()

    conn = sqlite3.connect(str(DB_PATH), timeout=30.0)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("PRAGMA journal_mode=WAL")
    cursor.execute("PRAGMA busy_timeout=30000")

    cursor.execute("SELECT phone FROM rec_debut_excluded_coaches")
    excluded_phones = set()
    for cr in cursor.fetchall():
        cp = re.sub(r"\D", "", cr["phone"] or "")
        if len(cp) >= 10:
            excluded_phones.add(cp[-10:])

    excluded_phones.update(get_personal_exclusion_set())

    cursor.execute("SELECT DISTINCT athlete_id FROM rec_debut_dispatches WHERE athlete_id IS NOT NULL")
    already_dispatched = {r[0] for r in cursor.fetchall()}

    cursor.execute("""
        SELECT DISTINCT a.phone
        FROM rec_debut_dispatches d
        JOIN rec_debut_athletes a ON a.id = d.athlete_id
        WHERE a.phone IS NOT NULL
    """)
    dispatched_phones = set()
    for pr in cursor.fetchall():
        dp = re.sub(r"\D", "", pr[0] or "")
        if len(dp) >= 10:
            dispatched_phones.add(dp[-10:])

    cursor.execute("""
        SELECT id, name, phone, email, sport, high_school, grad_year
        FROM rec_debut_athletes
        WHERE grad_year = '2027'
          AND phone IS NOT NULL AND length(phone) >= 10
        ORDER BY id ASC
    """)
    candidate_rows = [r for r in cursor.fetchall() if r["id"] not in already_dispatched]

    template = (
        "Hi {first_name}, a former NBA player wants to endorse your athletic portfolio! "
        "Dennis Bell, former NY Knick, can help your recruiting profile stand out. "
        "Free registration: recdebut-recruit.org/r/{athlete_id} "
        "616-291-5227 Dbell002@sbcglobal.net"
    )

    staged = []
    blocked_coaches = 0
    seen_batch_phones = set(dispatched_phones)

    for row in candidate_rows:
        raw_p = row["phone"] or ""
        clean_p = re.sub(r"\D", "", raw_p)
        if len(clean_p) < 10:
            continue
        ten_digit = clean_p[-10:]
        if ten_digit[0] in ("0", "1"):
            continue
        if ten_digit in excluded_phones:
            blocked_coaches += 1
            continue
        if ten_digit in seen_batch_phones:
            continue
        seen_batch_phones.add(ten_digit)

        e164_p = f"+1{ten_digit}"
        full_name = (row["name"] or "").strip()
        first_name = full_name.split()[0] if full_name else "Athlete"

        msg_body = (
            template.replace("{first_name}", first_name)
            .replace("{name}", full_name)
            .replace("{sport}", row["sport"] or "Basketball")
            .replace("{grad_year}", str(row["grad_year"] or "2027"))
            .replace("{athlete_id}", str(row["id"]))
        )

        staged.append({
            "athlete_id": row["id"],
            "name": full_name,
            "first_name": first_name,
            "phone": e164_p,
            "message": msg_body,
        })

    total_staged = len(staged)
    print("==================================================")
    print(f"RESUMING CLASS OF 2027 OPTION B DISPATCH: {total_staged} REMAINING (410/745 ALREADY DELIVERED)")
    if staged:
        print(f"Sample [0]: {staged[0]['message']} -> {staged[0]['phone']}")
    print("==================================================", flush=True)

    send_url = f"https://api.textbee.dev/api/v1/gateway/devices/{textbee_device}/send-sms"
    headers = {"x-api-key": textbee_key, "Content-Type": "application/json"}

    dispatched_count = 0
    failed_count = 0
    session = requests.Session()

    for idx, item in enumerate(staged, 1):
        resp_id = ""
        last_status = 0
        last_text = ""
        for attempt in range(6):
            try:
                r = session.post(
                    send_url,
                    headers=headers,
                    json={"recipients": [item["phone"]], "message": item["message"]},
                    timeout=15.0,
                )
                last_status = r.status_code
                last_text = r.text[:200]
                if r.status_code in (200, 201):
                    res_json = r.json()
                    data_obj = res_json.get("data", {})
                    if isinstance(data_obj, dict):
                        resp_id = data_obj.get("smsBatchId") or data_obj.get("_id") or str(data_obj)
                    else:
                        resp_id = str(data_obj)
                    if resp_id:
                        break
                elif r.status_code == 429:
                    wait_s = 4.0 * (attempt + 1)
                    print(f"[RATE LIMIT 429] Athlete {item['athlete_id']} attempt {attempt+1}, sleeping {wait_s}s...", flush=True)
                    time.sleep(wait_s)
                else:
                    time.sleep(2.0 * (attempt + 1))
            except Exception as ex:
                last_text = str(ex)
                time.sleep(2.0 * (attempt + 1))

        if resp_id:
            now_ts = time.time()
            cursor.execute(
                """
                INSERT INTO rec_debut_dispatches (athlete_id, channel, status, message_body, dispatched_at, response_status)
                VALUES (?, 'SMS', 'QUEUED', ?, ?, ?)
                """,
                (item["athlete_id"], item["message"], now_ts, resp_id),
            )
            cursor.execute(
                """
                UPDATE rec_debut_athletes
                SET status = 'SMS Queued', last_messaged_at = ?
                WHERE id = ?
                """,
                (now_ts, item["athlete_id"]),
            )
            conn.commit()
            dispatched_count += 1
        else:
            failed_count += 1
            print(f"[FAIL] Athlete {item['athlete_id']} ({item['phone']}): HTTP {last_status} {last_text}", flush=True)

        if idx % 25 == 0 or idx == total_staged:
            print(
                f"[PROGRESS] {idx}/{total_staged} processed (Total: {410 + dispatched_count}/745) | Failed: {failed_count} | Last ID: {item['athlete_id']} ({item['first_name']}) -> BatchID: {resp_id}",
                flush=True,
            )
        if idx % 100 == 0:
            safe_sqlite_backup(conn)

        time.sleep(0.35)

    safe_sqlite_backup(conn)
    conn.close()
    print("==================================================")
    print(f"COMPLETED ALL 745! Final Wave Dispatched: {dispatched_count}/{total_staged} | Total: {410 + dispatched_count}/745 | Failed: {failed_count}")
    print("==================================================", flush=True)


if __name__ == "__main__":
    main()
