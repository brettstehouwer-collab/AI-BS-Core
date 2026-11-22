import os
import sqlite3
import logging
from uuid import uuid4
from datetime import datetime
from typing import Dict, Any, List, Optional
from pathlib import Path

logger = logging.getLogger("FE_Express_ActiveLedger")
DB_PATH = Path(r"C:\AI-BS\saved_data\fe_express.db")
UPLOAD_DIR = Path(r"C:\AI-BS\saved_data\fe_express_bols")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


def init_active_loads_db():
    conn = sqlite3.connect(str(DB_PATH))
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS fe_express_active_dispatches (
            dispatch_id TEXT PRIMARY KEY,
            load_id TEXT,
            origin TEXT,
            destination TEXT,
            loaded_miles REAL,
            deadhead_miles REAL,
            gross_pay REAL,
            driver_name TEXT DEFAULT 'Devin',
            driver_phone TEXT DEFAULT '(616) 315-7483',
            driver_email TEXT DEFAULT 'Devin.feexpress@gmail.com',
            broker_name TEXT,
            broker_phone TEXT,
            status TEXT DEFAULT 'ASSIGNED',
            bol_photo_url TEXT,
            bol_notes TEXT,
            fuel_cost REAL DEFAULT 0.0,
            tolls_cost REAL DEFAULT 0.0,
            driver_pay REAL DEFAULT 0.0,
            net_profit REAL DEFAULT 0.0,
            dispatched_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            completed_at TIMESTAMP
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS fe_express_contractor_drivers (
            driver_id TEXT PRIMARY KEY,
            full_name TEXT NOT NULL,
            phone TEXT,
            email TEXT,
            tax_id_or_ssn_last4 TEXT,
            driver_license_num TEXT,
            driver_license_state TEXT DEFAULT 'MI',
            pay_model TEXT DEFAULT 'PERCENT_GROSS', -- 'PERCENT_GROSS', 'PER_MILE', 'FLAT_PER_DAY'
            pay_rate REAL DEFAULT 25.0,            -- e.g. 25% of load gross, or $0.55/mile
            medical_card_exp DATE,
            mvr_check_status TEXT DEFAULT 'CLEARED',
            w9_on_file INTEGER DEFAULT 1,
            notes TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS fe_express_driver_settlements (
            settlement_id TEXT PRIMARY KEY,
            driver_id TEXT,
            dispatch_id TEXT,
            trip_date DATE,
            origin_dest TEXT,
            total_miles REAL,
            gross_load_pay REAL,
            contractor_pay REAL,
            fuel_deduction REAL DEFAULT 0.0,
            cash_advance REAL DEFAULT 0.0,
            net_1099_payout REAL,
            payment_status TEXT DEFAULT 'PENDING', -- 'PENDING', 'PAID'
            payment_method TEXT DEFAULT 'ZELLE',    -- 'ZELLE', 'DIRECT_DEPOSIT', 'CHECK'
            notes TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()


init_active_loads_db()


class ActiveLoadManager:
    @staticmethod
    def book_load(load_data: Dict[str, Any]) -> Dict[str, Any]:
        """Locks in a load from the board into Devin's active haul queue."""
        conn = sqlite3.connect(str(DB_PATH))
        c = conn.cursor()
        
        dispatch_id = f"DISPATCH-{uuid4().hex}"
        load_id = load_data.get("load_id", f"LD-{int(datetime.now().timestamp())}")
        origin = load_data.get("origin_city_state", "")
        dest = load_data.get("dest_city_state", "")
        loaded_miles = float(load_data.get("total_miles", 0.0))
        deadhead_miles = float(load_data.get("deadhead_miles", 0.0))
        gross_pay = float(load_data.get("flat_rate_pay", 0.0))
        broker_name = load_data.get("broker_name", "Direct Broker")
        broker_phone = load_data.get("broker_phone", "")

        # Default estimated fuel and operational overhead
        # Box truck average: 10 MPG @ $3.85/gal = ~$0.385/mi fuel cost
        total_trip_miles = loaded_miles + deadhead_miles
        est_fuel = round(total_trip_miles * 0.385, 2)
        est_tolls = 25.0
        est_net = round(gross_pay - est_fuel - est_tolls, 2)

        c.execute("""
            INSERT INTO fe_express_active_dispatches (
                dispatch_id, load_id, origin, destination,
                loaded_miles, deadhead_miles, gross_pay,
                driver_name, driver_phone, driver_email,
                broker_name, broker_phone, status,
                fuel_cost, tolls_cost, net_profit
            ) VALUES (?, ?, ?, ?, ?, ?, ?, 'Devin', '(616) 315-7483', 'Devin.feexpress@gmail.com', ?, ?, 'EN_ROUTE_PICKUP', ?, ?, ?)
        """, (
            dispatch_id, load_id, origin, dest,
            loaded_miles, deadhead_miles, gross_pay,
            broker_name, broker_phone,
            est_fuel, est_tolls, est_net
        ))
        conn.commit()
        conn.close()

        return {
            "success": True,
            "dispatch_id": dispatch_id,
            "status": "EN_ROUTE_PICKUP",
            "gross_pay": gross_pay,
            "est_net_profit": est_net
        }

    @staticmethod
    def get_active_dispatches() -> List[Dict[str, Any]]:
        conn = sqlite3.connect(str(DB_PATH))
        conn.row_factory = sqlite3.Row
        c = conn.cursor()
        c.execute("""
            SELECT * FROM fe_express_active_dispatches 
            ORDER BY dispatched_at DESC
        """)
        rows = c.fetchall()
        conn.close()
        return [dict(r) for r in rows]

    @staticmethod
    def update_load_accounting(dispatch_id: str, updates: Dict[str, Any]) -> Dict[str, Any]:
        conn = sqlite3.connect(str(DB_PATH))
        c = conn.cursor()
        
        status = updates.get("status")
        fuel = float(updates.get("fuel_cost", 0.0))
        tolls = float(updates.get("tolls_cost", 0.0))
        bol_notes = updates.get("bol_notes", "")
        bol_url = updates.get("bol_photo_url")

        # Recalculate net profit
        c.execute("SELECT gross_pay FROM fe_express_active_dispatches WHERE dispatch_id = ?", (dispatch_id,))
        row = c.fetchone()
        gross = row[0] if row else 0.0
        net = round(gross - fuel - tolls, 2)

        completed_at = datetime.now().isoformat() if status == "DELIVERED" else None

        c.execute("""
            UPDATE fe_express_active_dispatches 
            SET status = COALESCE(?, status),
                fuel_cost = ?,
                tolls_cost = ?,
                net_profit = ?,
                bol_notes = COALESCE(?, bol_notes),
                bol_photo_url = COALESCE(?, bol_photo_url),
                completed_at = COALESCE(?, completed_at)
            WHERE dispatch_id = ?
        """, (status, fuel, tolls, net, bol_notes, bol_url, completed_at, dispatch_id))
        
        conn.commit()
        conn.close()
        return {"success": True, "dispatch_id": dispatch_id, "net_profit": net}

    @staticmethod
    def get_contractor_drivers() -> List[Dict[str, Any]]:
        conn = sqlite3.connect(str(DB_PATH))
        conn.row_factory = sqlite3.Row
        c = conn.cursor()
        c.execute("SELECT * FROM fe_express_contractor_drivers ORDER BY full_name ASC")
        rows = c.fetchall()
        conn.close()
        return [dict(r) for r in rows]

    @staticmethod
    def save_contractor_driver(driver: Dict[str, Any]) -> Dict[str, Any]:
        conn = sqlite3.connect(str(DB_PATH))
        c = conn.cursor()
        driver_id = driver.get("driver_id") or f"DRV-{int(datetime.now().timestamp())}"
        c.execute("""
            INSERT OR REPLACE INTO fe_express_contractor_drivers (
                driver_id, full_name, phone, email,
                tax_id_or_ssn_last4, driver_license_num, driver_license_state,
                pay_model, pay_rate, medical_card_exp,
                mvr_check_status, w9_on_file, notes
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            driver_id,
            driver.get("full_name", "Subcontract Driver"),
            driver.get("phone", ""),
            driver.get("email", ""),
            driver.get("tax_id_or_ssn_last4", "XXXX"),
            driver.get("driver_license_num", ""),
            driver.get("driver_license_state", "MI"),
            driver.get("pay_model", "PERCENT_GROSS"),
            float(driver.get("pay_rate", 25.0)),
            driver.get("medical_card_exp", "2027-01-01"),
            driver.get("mvr_check_status", "CLEARED"),
            int(driver.get("w9_on_file", 1)),
            driver.get("notes", "")
        ))
        conn.commit()
        conn.close()
        return {"success": True, "driver_id": driver_id}

    @staticmethod
    def get_driver_settlements(driver_id: Optional[str] = None) -> List[Dict[str, Any]]:
        conn = sqlite3.connect(str(DB_PATH))
        conn.row_factory = sqlite3.Row
        c = conn.cursor()
        if driver_id:
            c.execute("SELECT * FROM fe_express_driver_settlements WHERE driver_id = ? ORDER BY trip_date DESC", (driver_id,))
        else:
            c.execute("SELECT * FROM fe_express_driver_settlements ORDER BY trip_date DESC")
        rows = c.fetchall()
        conn.close()
        return [dict(r) for r in rows]

    @staticmethod
    def record_settlement(settlement: Dict[str, Any]) -> Dict[str, Any]:
        conn = sqlite3.connect(str(DB_PATH))
        c = conn.cursor()
        sid = settlement.get("settlement_id") or f"SETTLE-{int(datetime.now().timestamp())}"
        c.execute("""
            INSERT OR REPLACE INTO fe_express_driver_settlements (
                settlement_id, driver_id, dispatch_id, trip_date,
                origin_dest, total_miles, gross_load_pay,
                contractor_pay, fuel_deduction, cash_advance,
                net_1099_payout, payment_status, payment_method, notes
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            sid,
            settlement.get("driver_id", ""),
            settlement.get("dispatch_id", ""),
            settlement.get("trip_date", datetime.now().strftime("%Y-%m-%d")),
            settlement.get("origin_dest", ""),
            float(settlement.get("total_miles", 0.0)),
            float(settlement.get("gross_load_pay", 0.0)),
            float(settlement.get("contractor_pay", 0.0)),
            float(settlement.get("fuel_deduction", 0.0)),
            float(settlement.get("cash_advance", 0.0)),
            float(settlement.get("net_1099_payout", 0.0)),
            settlement.get("payment_status", "PAID"),
            settlement.get("payment_method", "ZELLE"),
            settlement.get("notes", "")
        ))
        conn.commit()
        conn.close()
        return {"success": True, "settlement_id": sid}

