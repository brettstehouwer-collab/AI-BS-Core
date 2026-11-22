"""
FE Express — Real Live Public Load Board Ingestor (Zero-Mock)
Fetches real, live, unauthenticated freight loads from Trulos Public Load Board API,
enriches each qualifying box-truck / partial / light van / hotshot load with:
  1. Real Broker Company, Contact Name, and Direct Phone Number (/load-detail.php?id=<id>&format=json)
  2. Real Highway Loaded Miles & Driving Hours (AWS Lambda Route Calculator API)
  3. Real Deadhead Miles from Home Base (default: Grand Rapids, MI)
  4. BoxTruckFilterEngine & LaneScoringEngine evaluation
Persists ONLY real loads into C:\AI-BS\saved_data\fe_express.db without deleting saved/manual rows.
"""

import os
import re
import sys
import json
import time
import math
import sqlite3
import logging
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any, Optional
import requests
from fe_express_scoring import FilterScoringEngine

sys.stdout.reconfigure(encoding="utf-8")
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("FE_Live_Ingestor")

DB_PATH = Path(r"C:\AI-BS\saved_data\fe_express.db")
TRULOS_PAGE_URL = "https://www.trulos.com/load-board/"
TRULOS_API_URL = "https://www.trulos.com/loadboard.php"
TRULOS_DETAIL_URL = "https://www.trulos.com/load-detail.php"
ROUTE_API_URL = "https://rypd2x43ypo6jorvsfee6bzapm0hbcyb.lambda-url.us-east-2.on.aws/"

# Cache road distances in memory so repeated city pairs are instant
_DISTANCE_CACHE: Dict[str, float] = {}


def get_highway_miles(session: requests.Session, origin: str, destination: str) -> Optional[float]:
    key = f"{origin.strip().upper()}->{destination.strip().upper()}"
    if key in _DISTANCE_CACHE:
        return _DISTANCE_CACHE[key]
    if origin.strip().upper() == destination.strip().upper():
        return 0.0
    try:
        r = session.get(
            ROUTE_API_URL,
            params={"origin": origin, "destination": destination},
            headers={"Referer": "https://www.trulos.com/"},
            timeout=8.0,
        )
        if r.status_code == 200:
            data = r.json()
            miles = float(data.get("distance_miles") or 0.0)
            if math.isfinite(miles) and miles > 0:
                _DISTANCE_CACHE[key] = round(miles, 1)
                return _DISTANCE_CACHE[key]
    except Exception as e:
        logger.debug(f"Route API fallback for {key}: {e}")
    return None  # Missing routes must never become invented mileage.


def format_phone(raw_phone: str) -> str:
    digits = re.sub(r"\D", "", str(raw_phone or ""))
    if len(digits) == 10:
        return f"({digits[:3]}) {digits[3:6]}-{digits[6:]}"
    if len(digits) == 11 and digits.startswith("1"):
        d = digits[1:]
        return f"({d[:3]}) {d[3:6]}-{d[6:]}"
    return str(raw_phone or "").strip()


def fetch_real_public_loads(
    home_base: str = "Grand Rapids, MI",
    max_weight_lbs: float = 10000.0,
    target_states: str = "MI,IL,IN,OH,WI,PA,KY,MO,MN,IA,TN,GA,NC,SC,TX,VA,WV",
    max_results: int = 35,
) -> List[Dict[str, Any]]:
    session = requests.Session()
    session.headers.update({
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
        "Referer": TRULOS_PAGE_URL,
    })

    # 1. Obtain live public token from Trulos Load Board page
    r_page = session.get(TRULOS_PAGE_URL, timeout=10)
    r_page.raise_for_status()
    m = re.search(r'TRULOS_PUBLIC_LOADBOARD_TOKEN\s*=\s*["\']([^"\']+)["\']', r_page.text)
    token = m.group(1) if m else ""
    api_headers = {
        "X-Requested-With": "XMLHttpRequest",
        "X-Trulos-Loadboard-Token": token,
    }

    raw_candidates = []
    seen_ids = set()

    # Priority 1: Query each Midwest / Core state sorted by pickupDate so Michigan & Midwest loads come first
    priority_states = [s.strip() for s in target_states.split(",") if s.strip()]
    for st in priority_states:
        try:
            url = f"{TRULOS_API_URL}?page=1&limit=100&sortColumn=pickupDate&sortOrder=asc&filterRate=true&originStates={st}"
            r = session.get(url, headers=api_headers, timeout=10)
            if r.status_code != 200:
                continue
            loads = r.json().get("loads", [])
            for l in loads:
                lid = str(l.get("LoadID") or "")
                if not lid or lid in seen_ids:
                    continue
                w_raw = float(re.sub(r"[^\d.]", "", str(l.get("Weight") or "0")) or 0)
                w_lbs = w_raw * 1000.0 if (0 < w_raw < 100) else w_raw
                rate = float(re.sub(r"[^\d.]", "", str(l.get("Rate") or "0")) or 0)
                eq = str(l.get("Equipment") or "").strip()
                load_size = str(l.get("loadSize") or "").strip()
                comment = str(l.get("comment") or "").strip()

                # Reject explicit 53' trailer only requirements
                if "53" in comment or "53'" in eq:
                    continue
                # Must have a real rate (> $50) and weight <= max_weight_lbs
                if rate < 50 or w_lbs <= 0 or w_lbs > max_weight_lbs:
                    continue

                seen_ids.add(lid)
                raw_candidates.append((w_lbs, rate, l))
        except Exception as e:
            logger.warning(f"Error polling state {st}: {e}")

    # Also scan multi-state pages 1..5 to catch any additional light/partial loads
    for page in range(1, 6):
        if len(raw_candidates) >= max_results:
            break
        try:
            url = f"{TRULOS_API_URL}?page={page}&limit=100&filterRate=true&originStates={target_states}"
            r = session.get(url, headers=api_headers, timeout=10)
            if r.status_code != 200:
                break
            loads = r.json().get("loads", [])
            for l in loads:
                lid = str(l.get("LoadID") or "")
                if not lid or lid in seen_ids:
                    continue
                w_raw = float(re.sub(r"[^\d.]", "", str(l.get("Weight") or "0")) or 0)
                w_lbs = w_raw * 1000.0 if (0 < w_raw < 100) else w_raw
                rate = float(re.sub(r"[^\d.]", "", str(l.get("Rate") or "0")) or 0)
                eq = str(l.get("Equipment") or "").strip()
                comment = str(l.get("comment") or "").strip()
                if "53" in comment or "53'" in eq:
                    continue
                if rate < 50 or w_lbs <= 0 or w_lbs > max_weight_lbs:
                    continue
                seen_ids.add(lid)
                raw_candidates.append((w_lbs, rate, l))
        except Exception:
            break

    logger.info(f"Discovered {len(raw_candidates)} real qualifying public loads (<= {max_weight_lbs:,.0f} lbs). Enriching with broker phones & highway miles...")

    enriched_loads = []
    for w_lbs, rate, l in raw_candidates[:max_results]:
        lid = str(l["LoadID"])
        orig_city = str(l.get("OriginCity") or "").strip().title()
        orig_state = str(l.get("OriginState") or "").strip().upper()
        dest_city = str(l.get("DestinationCity") or "").strip().title()
        dest_state = str(l.get("DestinationState") or "").strip().upper()
        origin_str = f"{orig_city}, {orig_state}"
        dest_str = f"{dest_city}, {dest_state}"

        # Fetch real broker phone and detail from /load-detail.php
        broker_name = str(l.get("CompanyName") or "Verified Broker").strip()
        contact_name = str(l.get("ContactName") or "").strip()
        broker_phone = ""
        pickup_date = str(l.get("PickupDate") or "").strip()
        comment = str(l.get("comment") or "").strip()
        load_size = str(l.get("loadSize") or "Full").strip()
        eq_raw = str(l.get("Equipment") or "Van").strip()

        try:
            r_det = session.get(
                f"{TRULOS_DETAIL_URL}?id={lid}&format=json",
                headers={"X-Requested-With": "XMLHttpRequest"},
                timeout=6.0,
            )
            if r_det.status_code == 200:
                det_json = r_det.json().get("load", {})
                broker_phone = format_phone(det_json.get("contactPhone") or det_json.get("ContactPhone") or "")
                if det_json.get("companyName"):
                    broker_name = det_json["companyName"]
                if det_json.get("contactName"):
                    contact_name = det_json["contactName"]
        except Exception:
            pass

        # Calculate real highway loaded miles & deadhead miles from Home Base
        loaded_miles = get_highway_miles(session, origin_str, dest_str)
        deadhead_miles = get_highway_miles(session, home_base, origin_str)

        if loaded_miles is None or deadhead_miles is None or loaded_miles <= 0:
            logger.warning("Skipping load %s: highway mileage unavailable", lid)
            continue
        evaluation = FilterScoringEngine.evaluate({
            "equipment_type": str(l.get("Equipment") or "") + " " + comment,
            "weight_lbs": w_lbs, "total_miles": loaded_miles,
            "deadhead_miles": deadhead_miles, "flat_rate_pay": rate,
        })
        rpm, true_rpm = evaluation["rpm"], evaluation["true_rpm"]
        score, tier = evaluation["score"], evaluation["priority_tier"]

        broker_display = f"{broker_name}"
        if contact_name:
            broker_display += f" ({contact_name})"
        if broker_phone:
            broker_display += f" • {broker_phone}"

        eq_display = f"{eq_raw} ({load_size})"
        if pickup_date:
            eq_display += f" [{pickup_date}]"

        enriched_loads.append({
            "load_id": f"TR-{lid}",
            "source": "Trulos Public Board (Live)",
            "origin_city_state": origin_str,
            "dest_city_state": dest_str,
            "equipment_type": eq_display,
            "weight_lbs": w_lbs,
            "total_miles": loaded_miles,
            "deadhead_miles": deadhead_miles,
            "flat_rate_pay": rate,
            "rpm": rpm,
            "true_rpm": true_rpm,
            "broker_name": broker_display,
            "broker_phone": broker_phone,
            "broker_email": comment[:120],
            "score": score,
            "priority_tier": tier,
            "status": "LIVE",
            "posted_at": datetime.now().strftime("%Y-%m-%d %I:%M:%S %p"),
        })

    # Sort Greenlight first, then highest Loaded RPM
    enriched_loads.sort(key=lambda x: (x["priority_tier"], -x["true_rpm"]))
    return enriched_loads


def sync_live_loads_to_db(home_base: str = "Grand Rapids, MI") -> List[Dict[str, Any]]:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    loads = fetch_real_public_loads(home_base=home_base, max_weight_lbs=10000.0, max_results=30)

    conn = sqlite3.connect(str(DB_PATH), timeout=30.0)
    c = conn.cursor()
    c.execute("PRAGMA journal_mode=WAL")

    # Refresh never removes saved/manual rows. Cleanup requires a separate review.

    for item in loads:
        c.execute(
            """
            INSERT OR REPLACE INTO fe_express_loads (
                load_id, source, origin_city_state, dest_city_state, equipment_type,
                weight_lbs, total_miles, deadhead_miles, flat_rate_pay, rpm, true_rpm,
                broker_name, broker_phone, broker_email, score, priority_tier, status, posted_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                item["load_id"],
                item["source"],
                item["origin_city_state"],
                item["dest_city_state"],
                item["equipment_type"],
                item["weight_lbs"],
                item["total_miles"],
                item["deadhead_miles"],
                item["flat_rate_pay"],
                item["rpm"],
                item["true_rpm"],
                item["broker_name"],
                item["broker_phone"],
                item["broker_email"],
                item["score"],
                item["priority_tier"],
                item["status"],
                item.get("posted_at", datetime.now().strftime("%Y-%m-%d %I:%M:%S %p")),
            ),
        )
    conn.commit()
    conn.close()
    return loads


if __name__ == "__main__":
    live_loads = sync_live_loads_to_db("Grand Rapids, MI")
    print(f"\n==================================================")
    print(f"SYNCED {len(live_loads)} REAL LIVE PUBLIC LOADS INTO fe_express.db")
    print(f"==================================================")
    for l in live_loads[:15]:
        print(
            f"[{l['score']}] {l['load_id']} | {l['origin_city_state']} -> {l['dest_city_state']} "
            f"| {l['total_miles']} mi (+{l['deadhead_miles']} DH) | Pay: ${l['flat_rate_pay']:,.0f} "
            f"| RPM: ${l['rpm']}/mi (True: ${l['true_rpm']}/mi) | Wt: {l['weight_lbs']:,.0f} lbs | {l['broker_name']}"
        )
