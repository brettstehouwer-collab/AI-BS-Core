import os
import sqlite3
import logging
from datetime import datetime
from typing import Dict, Any, Optional
from pathlib import Path

logger = logging.getLogger("FE_Express_AlertSentinel")
DB_PATH = Path(r"C:\AI-BS\saved_data\fe_express.db")


class AlertSentinel:
    @staticmethod
    def init_db():
        conn = sqlite3.connect(str(DB_PATH))
        c = conn.cursor()
        c.execute("""
            CREATE TABLE IF NOT EXISTS fe_express_alert_rules (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                driver_phone TEXT DEFAULT '616-402-3628',
                min_rpm REAL DEFAULT 2.50,
                min_pay REAL DEFAULT 800.0,
                max_deadhead REAL DEFAULT 75.0,
                home_base TEXT DEFAULT 'Grand Rapids, MI',
                active INTEGER DEFAULT 1,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.commit()
        conn.close()

    @classmethod
    def evaluate_load_for_alert(cls, load: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Determines whether a freshly parsed load qualifies for an urgent SMS alert
        to Devin's dispatch phone based on Greenlight criteria.
        """
        score = load.get("score")
        true_rpm = float(load.get("true_rpm") or load.get("rpm") or 0.0)
        pay = float(load.get("flat_rate_pay") or 0.0)
        deadhead = float(load.get("deadhead_miles") or 0.0)

        # High-priority trigger: Greenlight OR True RPM >= $2.50 OR Pay >= $1,000
        if score == "Greenlight" or true_rpm >= 2.50 or (pay >= 1000.0 and true_rpm >= 2.20):
            message = (
                f"🚨 FE EXPRESS HOT LOAD: {load.get('load_id')}!\n"
                f"📍 {load.get('origin_city_state')} ➡️ {load.get('dest_city_state')}\n"
                f"💰 Pay: ${pay:,.0f} | RPM: ${true_rpm:.2f}/mi ({load.get('total_miles')} mi + {deadhead} DH)\n"
                f"📦 Eq: {load.get('equipment_type')}\n"
                f"📞 Broker: {load.get('broker_name')}"
            )
            return {
                "qualified": True,
                "load_id": load.get("load_id"),
                "sms_body": message,
                "timestamp": datetime.now().strftime("%Y-%m-%d %I:%M:%S %p")
            }
        return None
