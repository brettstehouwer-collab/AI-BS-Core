import os
import sys
import time
import json
import sqlite3
import requests
import logging
from typing import List, Dict, Any, Optional

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("FE_Express_Poller")

sys.path.insert(0, r"C:\AI-BS\backend")
from routers.fe_express_router import DB_PATH, FilterScoringEngine

POLL_INTERVAL_SECONDS = 45

# Mock incoming board feed simulation for continuous real-time load detection
SIMULATED_LOAD_BATCHES = [
    [
        {"load_id": "FE-901", "origin": "Grand Rapids, MI", "destination": "Chicago, IL", "equipment": "26' Box Truck w/ Liftgate", "weight_lbs": 6200, "total_miles": 180, "deadhead_miles": 15, "flat_rate_pay": 580, "broker": "Echo Logistics", "broker_phone": "800-555-0199"},
        {"load_id": "FE-902", "origin": "Holland, MI", "destination": "Indianapolis, IN", "equipment": "24' Box Truck", "weight_lbs": 4800, "total_miles": 240, "deadhead_miles": 25, "flat_rate_pay": 720, "broker": "CH Robinson", "broker_phone": "800-555-0144"},
        {"load_id": "FE-903", "origin": "Kalamazoo, MI", "destination": "Cleveland, OH", "equipment": "53' Dry Van", "weight_lbs": 38000, "total_miles": 260, "deadhead_miles": 0, "flat_rate_pay": 600, "broker": "TQL", "broker_phone": "800-555-0122"}
    ],
    [
        {"load_id": "FE-904", "origin": "Detroit, MI", "destination": "Columbus, OH", "equipment": "26' Straight Truck", "weight_lbs": 5100, "total_miles": 205, "deadhead_miles": 10, "flat_rate_pay": 650, "broker": "Coyote Logistics", "broker_phone": "800-555-0188"},
        {"load_id": "FE-905", "origin": "Lansing, MI", "destination": "Milwaukee, WI", "equipment": "26' Box Truck", "weight_lbs": 7900, "total_miles": 310, "deadhead_miles": 20, "flat_rate_pay": 500, "broker": "ArcBest", "broker_phone": "800-555-0177"}
    ]
]


def poll_and_ingest():
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    c = conn.cursor()

    c.execute("SELECT key, value FROM fe_express_config")
    cfg = dict(c.fetchall())
    min_green = float(cfg.get("min_greenlight_rpm", 2.50))
    min_caut = float(cfg.get("min_caution_rpm", 2.00))
    max_wt = float(cfg.get("max_weight_lbs", 10000.0))

    batch_idx = 0
    logger.info("FE Express Autonomous Poller Daemon Started.")

    while True:
        try:
            batch = SIMULATED_LOAD_BATCHES[batch_idx % len(SIMULATED_LOAD_BATCHES)]
            batch_idx += 1

            for load in batch:
                load_id = load["load_id"]
                c.execute("SELECT load_id FROM fe_express_loads WHERE load_id = ?", (load_id,))
                if c.fetchone():
                    continue

                eval_data = FilterScoringEngine.evaluate(
                    load,
                    min_greenlight_rpm=min_green,
                    min_caution_rpm=min_caut,
                    max_weight=max_wt
                )

                c.execute("""
                    INSERT INTO fe_express_loads (
                        load_id, source, origin_city_state, dest_city_state, equipment_type,
                        weight_lbs, total_miles, deadhead_miles, flat_rate_pay, rpm, true_rpm,
                        broker_name, broker_phone, broker_email, score, priority_tier, status
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    load_id,
                    "Live Board Feed",
                    eval_data.get("origin", ""),
                    eval_data.get("destination", ""),
                    eval_data.get("equipment", ""),
                    float(eval_data.get("weight_lbs", 0.0)),
                    float(eval_data.get("total_miles", 1.0)),
                    float(eval_data.get("deadhead_miles", 0.0)),
                    float(eval_data.get("flat_rate_pay", 0.0)),
                    eval_data.get("rpm", 0.0),
                    eval_data.get("true_rpm", 0.0),
                    eval_data.get("broker", "Unknown Broker"),
                    eval_data.get("broker_phone", ""),
                    "",
                    eval_data.get("score", "Reject"),
                    eval_data.get("priority_tier", 3),
                    "NEW"
                ))
                conn.commit()

                if eval_data.get("score") == "Greenlight":
                    logger.info(f"🚨 [GREENLIGHT LOAD DETECTED] {load_id} | {eval_data.get('origin')} -> {eval_data.get('destination')} | True RPM: ${eval_data.get('true_rpm')}/mi")

        except Exception as e:
            logger.error(f"Poller error: {e}")

        time.sleep(POLL_INTERVAL_SECONDS)


if __name__ == "__main__":
    poll_and_ingest()
