"""
fe_express_owner_operator_engine.py
===================================
High-ROI Owner-Operator Yield Management, Navigation, Factoring,
IFTA State Tracking, and Asset Uptime Engine.

Direct SQLite integration into C:\AI-BS\saved_data\fe_express.db
Strict Zero Browser, Zero Local Web Server for UI dependencies.
"""

import sqlite3
import json
import math
import logging
from datetime import datetime
from dataclasses import dataclass, asdict
from typing import Dict, List, Any, Optional
from uuid import uuid4

logger = logging.getLogger("FE_OwnerOperatorEngine")
DB_PATH = r"C:\AI-BS\saved_data\fe_express.db"


# =========================================================================
# 1. STRUCTURAL CLASS DEFINITIONS FOR DYNAMIC CPM ENGINE
# =========================================================================

@dataclass
class VariableOperatingCosts:
    diesel_price_per_gal: float = 3.85
    truck_mpg: float = 9.5
    driver_wage_per_mile: float = 0.60
    tire_wear_per_mile: float = 0.05
    preventive_maintenance_per_mile: float = 0.10
    engine_overhaul_sinking_fund_per_mile: float = 0.15 # $0.15/mi capital reserve
    tolls_and_misc_per_mile: float = 0.08

    @property
    def fuel_cpm(self) -> float:
        return self.diesel_price_per_gal / max(4.0, self.truck_mpg)

    @property
    def total_variable_cpm(self) -> float:
        return (
            self.fuel_cpm +
            self.driver_wage_per_mile +
            self.tire_wear_per_mile +
            self.preventive_maintenance_per_mile +
            self.engine_overhaul_sinking_fund_per_mile +
            self.tolls_and_misc_per_mile
        )


@dataclass
class FixedMonthlyOverhead:
    commercial_auto_cargo_insurance: float = 1450.00
    equipment_note_or_lease: float = 1200.00
    eld_tms_telematics_software: float = 250.00
    permits_ifta_accounting_compliance: float = 150.00
    cellular_dispatch_hotspot: float = 120.00
    estimated_monthly_miles: float = 8500.0

    @property
    def total_monthly_fixed(self) -> float:
        return (
            self.commercial_auto_cargo_insurance +
            self.equipment_note_or_lease +
            self.eld_tms_telematics_software +
            self.permits_ifta_accounting_compliance +
            self.cellular_dispatch_hotspot
        )

    @property
    def fixed_cpm(self) -> float:
        return self.total_monthly_fixed / max(1000.0, self.estimated_monthly_miles)


@dataclass
class DynamicCPMEngine:
    variable_costs: VariableOperatingCosts
    fixed_overhead: FixedMonthlyOverhead
    target_profit_margin_pct: float = 25.0

    @property
    def break_even_cash_floor_cpm(self) -> float:
        """True cash break-even operating floor ($/mile)."""
        return round(self.variable_costs.total_variable_cpm + self.fixed_overhead.fixed_cpm, 3)

    @property
    def recommended_minimum_bidding_rpm(self) -> float:
        """Minimum target rate per mile to achieve target profit margin."""
        margin_decimal = self.target_profit_margin_pct / 100.0
        return round(self.break_even_cash_floor_cpm / (1.0 - margin_decimal), 2)

    def evaluate_load_profitability(self, loaded_miles: float, deadhead_miles: float, posted_gross_pay: float) -> Dict[str, Any]:
        total_miles = loaded_miles + deadhead_miles
        if total_miles <= 0:
            return {"viable": False, "error": "Total miles must be > 0"}
        
        break_even_cost = round(total_miles * self.break_even_cash_floor_cpm, 2)
        projected_net_ebitda = round(posted_gross_pay - break_even_cost, 2)
        true_rpm = round(posted_gross_pay / total_miles, 2)
        target_quote = round(total_miles * self.recommended_minimum_bidding_rpm, 2)

        return {
            "total_miles": total_miles,
            "loaded_miles": loaded_miles,
            "deadhead_miles": deadhead_miles,
            "posted_gross_pay": posted_gross_pay,
            "true_rpm": true_rpm,
            "break_even_cash_floor_rpm": self.break_even_cash_floor_cpm,
            "recommended_target_rpm": self.recommended_minimum_bidding_rpm,
            "total_operating_cost": break_even_cost,
            "projected_net_ebitda": projected_net_ebitda,
            "target_quote_bid": target_quote,
            "is_above_cash_floor": true_rpm >= self.break_even_cash_floor_cpm,
            "meets_target_margin": true_rpm >= self.recommended_minimum_bidding_rpm
        }


# =========================================================================
# 2. SQL STATE-BOUNDARY GEO-QUERIES FOR IFTA AUDIT TRACKER
# =========================================================================

IFTA_STATE_CROSSING_SQL = """
-- Detect State-Line Crossings & Allocate Inter-State Mileage
WITH OrderedPings AS (
    SELECT 
        ping_id,
        vehicle_id,
        latitude,
        longitude,
        state_code,
        odometer_reading,
        recorded_at,
        LAG(state_code, 1) OVER (PARTITION BY vehicle_id ORDER BY recorded_at) AS prev_state,
        LAG(odometer_reading, 1) OVER (PARTITION BY vehicle_id ORDER BY recorded_at) AS prev_odometer,
        LAG(recorded_at, 1) OVER (PARTITION BY vehicle_id ORDER BY recorded_at) AS prev_recorded_at
    FROM vehicle_gps_pings
    WHERE recorded_at >= :quarter_start_epoch AND recorded_at <= :quarter_end_epoch
)
SELECT 
    vehicle_id,
    prev_state AS exit_state,
    state_code AS entry_state,
    (odometer_reading - prev_odometer) AS border_transit_miles,
    prev_recorded_at AS exit_time,
    recorded_at AS entry_time
FROM OrderedPings
WHERE prev_state IS NOT NULL AND prev_state != state_code;
"""

IFTA_QUARTERLY_TAX_SUMMARY_SQL = """
-- Compute State-by-State IFTA Tax Balances vs Fuel Purchases
SELECT 
    l.state_code,
    SUM(l.miles_driven) AS total_state_miles,
    ROUND(SUM(l.miles_driven) / :fleet_mpg, 2) AS taxable_gallons_consumed,
    COALESCE(SUM(p.gallons_purchased), 0.0) AS tax_paid_gallons_purchased,
    ROUND((SUM(l.miles_driven) / :fleet_mpg) - COALESCE(SUM(p.gallons_purchased), 0.0), 2) AS net_taxable_gallons,
    s.tax_rate_per_gal,
    ROUND(((SUM(l.miles_driven) / :fleet_mpg) - COALESCE(SUM(p.gallons_purchased), 0.0)) * s.tax_rate_per_gal, 2) AS net_tax_balance_due
FROM fe_express_ifta_logs l
LEFT JOIN ifta_fuel_purchases p ON l.vehicle_unit = p.vehicle_id AND l.state_code = p.state_code AND l.quarter = :quarter
CROSS JOIN (
    SELECT 'MI' AS st, 0.300 AS tax_rate_per_gal UNION ALL
    SELECT 'IN', 0.570 UNION ALL
    SELECT 'IL', 0.697 UNION ALL
    SELECT 'OH', 0.470 UNION ALL
    SELECT 'WI', 0.329
) s ON l.state_code = s.st
WHERE l.quarter = :quarter
GROUP BY l.state_code;
"""



def init_owner_operator_tables():
    """Initializes high-ROI owner-operator tables in SQLite."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    # 1. Triangulation Chains Table
    c.execute("""
    CREATE TABLE IF NOT EXISTS fe_express_triangulation_chains (
        chain_id TEXT PRIMARY KEY,
        name TEXT,
        legs_json TEXT, -- List of load_ids or simulated legs
        total_loaded_miles REAL,
        total_deadhead_miles REAL,
        total_gross_pay REAL,
        effective_true_rpm REAL,
        estimated_fuel_cost REAL,
        projected_net_ebitda REAL,
        created_at TEXT
    )
    """)

    # 2. Factoring & Invoicing Gateway Table
    c.execute("""
    CREATE TABLE IF NOT EXISTS fe_express_factoring_submissions (
        submission_id TEXT PRIMARY KEY,
        dispatch_id TEXT,
        load_id TEXT,
        invoice_number TEXT,
        factoring_company TEXT,
        gross_amount REAL,
        factoring_fee_pct REAL,
        advance_rate_pct REAL,
        expected_payout REAL,
        bol_url TEXT,
        ratecon_url TEXT,
        status TEXT, -- 'GENERATED', 'SUBMITTED', 'FUNDED', 'REJECTED'
        submitted_at TEXT,
        funded_at TEXT
    )
    """)

    # 3. IFTA State Mileages & Fuel Card Sync Table
    c.execute("""
    CREATE TABLE IF NOT EXISTS fe_express_ifta_logs (
        log_id TEXT PRIMARY KEY,
        dispatch_id TEXT,
        vehicle_unit TEXT,
        state_code TEXT,
        miles_driven REAL,
        gallons_purchased REAL,
        fuel_card_vendor TEXT, -- 'WEX', 'MUDFLAP', 'COMDATA', 'CASH'
        fuel_cost_total REAL,
        quarter TEXT, -- e.g. '2026-Q4'
        log_date TEXT,
        created_at TEXT
    )
    """)

    # 4. Vehicle Navigation & Clearance Profiles
    c.execute("""
    CREATE TABLE IF NOT EXISTS fe_express_vehicle_profiles (
        unit_id TEXT PRIMARY KEY,
        vehicle_type TEXT, -- 'BOX_TRUCK_26', 'CARGO_VAN'
        height_inches INTEGER, -- e.g. 156 (13'0") or 138 (11'6")
        clearance_ft_in TEXT, -- '13ft 0in'
        weight_empty_lbs INTEGER,
        weight_max_gross_lbs INTEGER,
        hazmat_certified INTEGER,
        liftgate INTEGER,
        pallets_capacity INTEGER,
        vin TEXT,
        license_plate TEXT,
        updated_at TEXT
    )
    """)

    # 5. Preventative Maintenance & DVIR Inspections
    c.execute("""
    CREATE TABLE IF NOT EXISTS fe_express_maintenance_dvir (
        record_id TEXT PRIMARY KEY,
        unit_id TEXT,
        record_type TEXT, -- 'DVIR_PRETRIP', 'DVIR_POSTTRIP', 'MAINTENANCE_LOG'
        odometer INTEGER,
        engine_hours REAL,
        status TEXT, -- 'SATISFACTORY', 'DEFECTS_NOTED', 'OUT_OF_SERVICE'
        service_category TEXT, -- 'BRAKES', 'OIL_CHANGE', 'TIRES', 'DPF_REGEN', 'ANNUAL_DOT'
        cost REAL,
        next_service_odometer INTEGER,
        inspector_name TEXT,
        notes TEXT,
        created_at TEXT
    )
    """)

    # 6. Granular Vehicle GPS Pings (Automated State-Line Tracking)
    c.execute("""
    CREATE TABLE IF NOT EXISTS vehicle_gps_pings (
        ping_id TEXT PRIMARY KEY,
        vehicle_id TEXT NOT NULL,
        latitude REAL NOT NULL,
        longitude REAL NOT NULL,
        state_code TEXT NOT NULL,
        odometer_reading REAL NOT NULL,
        recorded_at INTEGER NOT NULL
    )
    """)

    # 7. Fuel Card Transactions (IFTA Purchase Ledger)
    c.execute("""
    CREATE TABLE IF NOT EXISTS ifta_fuel_purchases (
        purchase_id TEXT PRIMARY KEY,
        vehicle_id TEXT NOT NULL,
        state_code TEXT NOT NULL,
        gallons_purchased REAL NOT NULL,
        total_amount_paid REAL NOT NULL,
        fuel_card_vendor TEXT NOT NULL,
        transaction_time INTEGER NOT NULL
    )
    """)

    # 8. Normalized Multi-Leg Triangulation Chains & Legs
    c.execute("""
    CREATE TABLE IF NOT EXISTS load_triangulation_chains (
        chain_id TEXT PRIMARY KEY,
        total_gross_payout REAL NOT NULL,
        total_combined_miles REAL NOT NULL,
        true_chain_rpm REAL NOT NULL,
        estimated_net_margin REAL NOT NULL,
        created_at INTEGER NOT NULL
    )
    """)

    c.execute("""
    CREATE TABLE IF NOT EXISTS chain_legs (
        leg_id TEXT PRIMARY KEY,
        chain_id TEXT NOT NULL,
        sequence_order INTEGER NOT NULL,
        broker_name TEXT,
        origin_city_state TEXT NOT NULL,
        destination_city_state TEXT NOT NULL,
        loaded_miles REAL NOT NULL,
        deadhead_miles REAL NOT NULL,
        payout REAL NOT NULL,
        equipment_class TEXT NOT NULL,
        FOREIGN KEY (chain_id) REFERENCES load_triangulation_chains(chain_id) ON DELETE CASCADE
    )
    """)

    # Seed Default Vehicle Profile for Devin (26ft Box Truck - No Liftgate)
    c.execute("""
    INSERT OR IGNORE INTO fe_express_vehicle_profiles (
        unit_id, vehicle_type, height_inches, clearance_ft_in,
        weight_empty_lbs, weight_max_gross_lbs, hazmat_certified, liftgate,
        pallets_capacity, vin, license_plate, updated_at
    ) VALUES (
        'UNIT-26FT-01', 'BOX_TRUCK_26', 150, '12ft 6in',
        14500, 26000, 0, 0,
        12, '1HTMMAAL7NH123456', 'MI-TRK-7890', datetime('now')
    )
    """)

    conn.commit()
    conn.close()


def calculate_trip_ebitda(
    gross_payout: float,
    loaded_miles: float,
    deadhead_miles: float,
    fuel_cost: float,
    tolls: float,
    fixed_daily_overhead: float = 120.0,
    days_on_trip: int = 1
) -> Dict[str, Any]:
    """
    Computes real-time true profitability for an owner-operator on a specific haul.
    Accounts for truck wear-and-tear depreciation directly ($0.15/mile maintenance reserve).
    """
    total_miles = loaded_miles + deadhead_miles
    maintenance_reserve = round(total_miles * 0.15, 2)
    allocated_fixed_costs = round(fixed_daily_overhead * days_on_trip, 2)

    total_expenses = round(fuel_cost + tolls + maintenance_reserve + allocated_fixed_costs, 2)
    net_ebitda = round(gross_payout - total_expenses, 2)
    ebitda_margin_percentage = round((net_ebitda / gross_payout) * 100, 2) if gross_payout > 0 else 0.0

    return {
        "trip_gross_revenue": round(gross_payout, 2),
        "total_miles": round(total_miles, 1),
        "operating_expenses_total": total_expenses,
        "maintenance_reserve_withheld": maintenance_reserve,
        "allocated_fixed_costs": allocated_fixed_costs,
        "trip_net_ebitda": net_ebitda,
        "ebitda_margin_pct": ebitda_margin_percentage,
        "net_profit_per_total_mile": round(net_ebitda / total_miles, 2) if total_miles > 0 else 0.0
    }


def calculate_chain_profitability(legs: List[Dict[str, Any]], cost_per_mile: float = 1.35) -> Dict[str, Any]:
    """
    Evaluates a proposed sequence of multi-leg spot market loads using exact Blueprint formula.
    """
    total_payout = 0.0
    total_loaded_miles = 0.0
    total_deadhead_miles = 0.0

    for leg in legs:
        total_payout += float(leg.get('payout', 0.0))
        total_loaded_miles += float(leg.get('loaded_miles', 0.0))
        total_deadhead_miles += float(leg.get('deadhead_miles', 0.0))

    total_miles = total_loaded_miles + total_deadhead_miles
    if total_miles == 0:
        return {"success": False, "error": "Zero miles calculated"}

    total_cost = total_miles * cost_per_mile
    net_margin = total_payout - total_cost
    true_rpm = total_payout / total_miles

    return {
        "success": True,
        "total_gross": round(total_payout, 2),
        "total_miles": round(total_miles, 2),
        "loaded_miles": round(total_loaded_miles, 2),
        "deadhead_miles": round(total_deadhead_miles, 2),
        "true_rpm": round(true_rpm, 2),
        "net_margin": round(net_margin, 2),
        "viable": net_margin > 0 and true_rpm > 1.85
    }


def process_gps_ping(current_ping: Dict[str, Any], last_ping: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Detects if the vehicle crossed state lines between two sequential check-ins
    to accurately record data boundaries for quarterly IFTA filing.
    """
    if not last_ping:
        return {"state_line_crossed": False}

    if current_ping.get('state_code') != last_ping.get('state_code'):
        miles_driven = float(current_ping.get('odometer_reading', 0.0)) - float(last_ping.get('odometer_reading', 0.0))
        return {
            "state_line_crossed": True,
            "exit_state": last_ping.get('state_code'),
            "entry_state": current_ping.get('state_code'),
            "allocated_miles": round(miles_driven, 1),
            "timestamp": current_ping.get('recorded_at')
        }
    return {"state_line_crossed": False}


# -------------------------------------------------------------
# 1. Triangulation Load Planner Engine
# -------------------------------------------------------------
def build_triangulation_chains(home_terminal: str = "Grand Rapids, MI", max_chains: int = 5) -> List[Dict[str, Any]]:
    """
    Finds 3-leg and 4-leg loops starting and ending near the home terminal:
    Leg 1: Home Terminal -> Market A
    Leg 2: Market A -> Market B
    Leg 3: Market B -> Home Terminal
    Calculates True RPM factoring in all loaded and deadhead transit miles.
    """
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()

    loads = c.execute("SELECT * FROM fe_express_loads WHERE status != 'BOOKED'").fetchall()
    conn.close()

    if not loads:
        return []

    load_list = [dict(row) for row in loads]
    chains = []

    # Heuristic city coordinate lookup for distance estimation
    CITY_COORDS = {
        "Grand Rapids, MI": (42.9634, -85.6681),
        "Chicago, IL": (41.8781, -87.6298),
        "Milwaukee, WI": (43.0389, -87.9065),
        "Waukesha, WI": (43.0117, -88.2315),
        "Detroit, MI": (42.3314, -83.0458),
        "Indianapolis, IN": (39.7684, -86.1581),
        "Cleveland, OH": (41.4993, -81.6944),
        "Columbus, OH": (39.9612, -82.9988),
        "Cincinnati, OH": (39.1031, -84.5120),
        "South Bend, IN": (41.6764, -86.2520),
        "Fort Wayne, IN": (41.0793, -85.1394),
        "Minneapolis, MN": (44.9778, -93.2650),
    }

    def approx_miles(loc1: str, loc2: str) -> float:
        c1 = CITY_COORDS.get(loc1)
        c2 = CITY_COORDS.get(loc2)
        if not c1 or not c2:
            return 85.0 # default estimated deadhead
        lat1, lon1 = c1
        lat2, lon2 = c2
        # Haversine with 1.25 road curvature multiplier
        R = 3958.8
        dlat = math.radians(lat2 - lat1)
        dlon = math.radians(lon2 - lon1)
        a = math.sin(dlat / 2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2)**2
        c_val = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
        return round(R * c_val * 1.24, 1)

    # Search for valid 2-leg or 3-leg chains
    for l1 in load_list:
        l1_orig = l1["origin_city_state"]
        l1_dest = l1["dest_city_state"]
        dh1 = approx_miles(home_terminal, l1_orig)

        # Look for leg 2 matching destination of leg 1
        for l2 in load_list:
            if l2["load_id"] == l1["load_id"]:
                continue
            l2_orig = l2["origin_city_state"]
            l2_dest = l2["dest_city_state"]
            dh2 = approx_miles(l1_dest, l2_orig)

            if dh2 > 120.0: # Skip excessive empty repositioning
                continue

            dh_home = approx_miles(l2_dest, home_terminal)

            # 2-Leg Triangulation (Home -> L1_Orig -> L1_Dest -> L2_Orig -> L2_Dest -> Home)
            total_loaded = (l1.get("total_miles") or 0.0) + (l2.get("total_miles") or 0.0)
            total_deadhead = dh1 + dh2 + dh_home
            total_miles = total_loaded + total_deadhead
            total_gross = (l1.get("flat_rate_pay") or 0.0) + (l2.get("flat_rate_pay") or 0.0)

            if total_miles > 0 and total_gross > 0:
                true_rpm = round(total_gross / total_miles, 2)
                fuel_est = round((total_miles / 9.5) * 3.85, 2) # 9.5 MPG @ $3.85/gal
                tolls_est = round(total_loaded * 0.08, 2)
                net_ebitda = round(total_gross - fuel_est - tolls_est, 2)

                chain = {
                    "chain_id": f"TRI-{l1['load_id']}-{l2['load_id']}",
                    "name": f"Loop: {l1_orig} -> {l1_dest} -> {l2_dest} -> {home_terminal}",
                    "legs": [
                        {
                            "step": 1,
                            "type": "LOAD",
                            "load_id": l1["load_id"],
                            "origin": l1_orig,
                            "dest": l1_dest,
                            "miles": l1.get("total_miles"),
                            "pay": l1.get("flat_rate_pay"),
                            "broker": l1.get("broker_name"),
                            "broker_phone": l1.get("broker_phone")
                        },
                        {
                            "step": 2,
                            "type": "DEADHEAD",
                            "origin": l1_dest,
                            "dest": l2_orig,
                            "miles": dh2,
                            "pay": 0.0
                        },
                        {
                            "step": 3,
                            "type": "LOAD",
                            "load_id": l2["load_id"],
                            "origin": l2_orig,
                            "dest": l2_dest,
                            "miles": l2.get("total_miles"),
                            "pay": l2.get("flat_rate_pay"),
                            "broker": l2.get("broker_name"),
                            "broker_phone": l2.get("broker_phone")
                        },
                        {
                            "step": 4,
                            "type": "DEADHEAD_RETURN",
                            "origin": l2_dest,
                            "dest": home_terminal,
                            "miles": dh_home,
                            "pay": 0.0
                        }
                    ],
                    "total_loaded_miles": round(total_loaded, 1),
                    "total_deadhead_miles": round(total_deadhead, 1),
                    "total_miles": round(total_miles, 1),
                    "total_gross_pay": round(total_gross, 2),
                    "effective_true_rpm": true_rpm,
                    "estimated_fuel_cost": fuel_est,
                    "projected_net_ebitda": net_ebitda
                }
                chains.append(chain)

    # Sort by highest True RPM
    chains.sort(key=lambda x: x["effective_true_rpm"], reverse=True)
    return chains[:max_chains]


# -------------------------------------------------------------
# 2. Instant Factoring & Cash Velocity Invoicing Package
# -------------------------------------------------------------
def generate_instant_factoring_submission(
    dispatch_id: str,
    factoring_company: str = "Triumph Business Capital (Direct)",
    fee_pct: float = 2.5,
    advance_pct: float = 97.5
) -> Dict[str, Any]:
    """Save an estimated local invoice draft, without provider or document acceptance."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()

    dispatch = c.execute("SELECT * FROM fe_express_active_dispatches WHERE dispatch_id = ?", (dispatch_id,)).fetchone()
    if not dispatch:
        conn.close()
        return {"error": f"Dispatch {dispatch_id} not found"}

    d = dict(dispatch)
    gross = float(d.get("gross_pay") or 0.0)
    factoring_fee = round(gross * (fee_pct / 100.0), 2)
    expected_payout = round(gross * (advance_pct / 100.0) - factoring_fee, 2)

    sub_id = f"FACT-{uuid4()}"
    inv_num = f"INV-{dispatch_id.replace('DISP-', '')}"

    submission = {
        "submission_id": sub_id,
        "dispatch_id": dispatch_id,
        "load_id": d.get("load_id"),
        "invoice_number": inv_num,
        "factoring_company": factoring_company,
        "gross_amount": gross,
        "factoring_fee_pct": fee_pct,
        "advance_rate_pct": advance_pct,
        "expected_payout": expected_payout,
        "broker_name": d.get("broker_name"),
        "broker_phone": d.get("broker_phone"),
        "origin_dest": f"{d.get('origin')} -> {d.get('destination')}",
        # Historical dispatch references are retained as unverified metadata only.
        "legacy_bol_reference": d.get("bol_photo_url"),
        "bol_url": None,
        "ratecon_url": None,
        "documents_verified": False,
        "status": "PREPARED_LOCALLY",
        "provider_connected": False,
        "delivery_confirmed": False,
        "provider_receipt": None,
        "prepared_at": datetime.now().isoformat(),
        "submitted_at": None
    }

    c.execute("""
    INSERT OR REPLACE INTO fe_express_factoring_submissions (
        submission_id, dispatch_id, load_id, invoice_number,
        factoring_company, gross_amount, factoring_fee_pct,
        advance_rate_pct, expected_payout, bol_url, ratecon_url,
        status, submitted_at
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        sub_id, dispatch_id, d.get("load_id"), inv_num,
        factoring_company, gross, fee_pct,
        advance_pct, expected_payout, submission["bol_url"], submission["ratecon_url"],
        submission["status"], None
    ))

    conn.commit()
    conn.close()
    return submission


# =========================================================================
# 3. ASYNCHRONOUS FACTORING HOUSE GATEWAY CLIENT (TRIUMPH / APEX / RTS)
# =========================================================================

class AsyncFactoringGatewayClient:
    """Legacy local preparation API; no provider transport or funding receipts."""

    GATEWAYS = {
        "TRIUMPH": {
            "name": "Triumph Business Capital",
            "endpoint": "https://api.triumphbcp.com/v2/carrier/invoices/instant-funding",
            "advance_rate": 0.975, # 97.5% advance
            "fee_rate": 0.025      # 2.5% factoring fee
        },
        "APEX": {
            "name": "Apex Capital Corp",
            "endpoint": "https://api.apexcapitalcorp.com/edi/v1/schedule/direct-deposit",
            "advance_rate": 0.970,
            "fee_rate": 0.030
        },
        "RTS": {
            "name": "RTS Financial",
            "endpoint": "https://gateway.rtsfinancial.com/api/v3/funding/express",
            "advance_rate": 0.975,
            "fee_rate": 0.025
        }
    }

    @classmethod
    def prepare_factoring_payload(cls, dispatch_id: str, gateway_key: str = "TRIUMPH") -> Dict[str, Any]:
        """Assemble unverified draft metadata for manual review."""
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        c = conn.cursor()

        dispatch = c.execute("SELECT * FROM fe_express_active_dispatches WHERE dispatch_id = ?", (dispatch_id,)).fetchone()
        conn.close()

        if not dispatch:
            raise ValueError(f"Dispatch {dispatch_id} not found in database.")

        d = dict(dispatch)
        gateway = cls.GATEWAYS.get(gateway_key.upper(), cls.GATEWAYS["TRIUMPH"])
        gross = float(d.get("gross_pay") or 0.0)
        fee_amt = round(gross * gateway["fee_rate"], 2)
        net_advance = round(gross * gateway["advance_rate"] - fee_amt, 2)

        return {
            "status": "PREPARED_LOCALLY",
            "provider_connected": False,
            "delivery_confirmed": False,
            "provider_receipt": None,
            "documents_verified": False,
            "carrier_header": {
                "company_name": "FE Express LLC",
                "mc_number": "MC-1482910",
                "usdot_number": "USDOT-3918241",
                "terminal_address": "2700 Remico Street Southwest, Wyoming, MI 49519",
                "dispatch_phone": "(616) 315-7483",
                "dispatch_email": "Devin.feexpress@gmail.com"
            },
            "invoice_metadata": {
                "dispatch_id": dispatch_id,
                "invoice_number": f"INV-{dispatch_id.replace('DISP-', '')}",
                "load_id": d.get("load_id"),
                "broker_name": d.get("broker_name"),
                "broker_phone": d.get("broker_phone"),
                "origin": d.get("origin"),
                "destination": d.get("destination"),
                "gross_freight_charge": gross,
                "gateway_partner": gateway["name"],
                "contract_advance_rate_pct": gateway["advance_rate"] * 100,
                "factoring_fee_pct": gateway["fee_rate"] * 100,
                "expected_immediate_deposit": net_advance
            },
            "document_attachments": {
                "bol_deskewed_pdf": None,
                "rate_confirmation_pdf": None,
                "carrier_w9_coi_pdf": None
            },
            "settlement_auto_post": {
                "driver_name": d.get("driver_name", "Devin"),
                "fuel_deduction": float(d.get("fuel_cost") or 0.0),
                "net_driver_accrual": round(gross * 0.25 - float(d.get("fuel_cost") or 0.0), 2)
            }
        }

    @classmethod
    def execute_async_factoring_submission(cls, dispatch_id: str, gateway_key: str = "TRIUMPH") -> Dict[str, Any]:
        """Save local preparation only. Never mark funding or create paid settlements."""
        payload = cls.prepare_factoring_payload(dispatch_id, gateway_key)
        inv = payload["invoice_metadata"]
        sub_id = f"FACT-API-{uuid4()}"

        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute("""
        INSERT OR REPLACE INTO fe_express_factoring_submissions (
            submission_id, dispatch_id, load_id, invoice_number,
            factoring_company, gross_amount, factoring_fee_pct,
            advance_rate_pct, expected_payout, bol_url, ratecon_url,
            status, submitted_at, funded_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            sub_id, dispatch_id, inv["load_id"], inv["invoice_number"],
            inv["gateway_partner"], inv["gross_freight_charge"], inv["factoring_fee_pct"],
            inv["contract_advance_rate_pct"], inv["expected_immediate_deposit"],
            payload["document_attachments"]["bol_deskewed_pdf"],
            payload["document_attachments"]["rate_confirmation_pdf"],
            "PREPARED_LOCALLY", None, None
        ))

        conn.commit()
        conn.close()

        return {
            "success": True,
            "submission_id": sub_id,
            "status": "PREPARED_LOCALLY",
            "provider_connected": False,
            "delivery_confirmed": False,
            "provider_receipt": None,
            "documents_verified": False,
            "prepared_at": datetime.now().isoformat(),
            "batch_confirmation_code": None,
            "advance_amount": inv["expected_immediate_deposit"],
            "gateway_partner": inv["gateway_partner"],
            "bank_deposit_eta": None,
            "driver_settlement_reconciled": False
        }



# -------------------------------------------------------------
# 3. Automated IFTA State Mileage & Fuel Card Sync Engine
# -------------------------------------------------------------
def calculate_ifta_quarterly_summary(quarter: str = "2026-Q4") -> Dict[str, Any]:
    """
    Computes state-by-state IFTA fuel tax calculations:
    Miles per State, Taxable Gallons consumed (based on fleet average MPG),
    Tax-Paid Gallons purchased, and Net Tax Due/Refund.
    """
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()

    rows = c.execute("SELECT * FROM fe_express_ifta_logs WHERE quarter = ?", (quarter,)).fetchall()

    # Standard state tax rates per gallon (approximate baseline for commercial diesel)
    STATE_TAX_RATES = {
        "MI": 0.320,
        "IL": 0.589,
        "IN": 0.570,
        "WI": 0.329,
        "OH": 0.470,
    }

    state_data: Dict[str, Dict[str, float]] = {}
    total_miles = 0.0
    total_gallons_purchased = 0.0

    for r in rows:
        st = r["state_code"]
        miles = float(r["miles_driven"] or 0.0)
        gals = float(r["gallons_purchased"] or 0.0)
        cost = float(r["fuel_cost_total"] or 0.0)

        total_miles += miles
        total_gallons_purchased += gals

        if st not in state_data:
            state_data[st] = {"miles": 0.0, "purchased_gals": 0.0, "fuel_cost": 0.0}
        state_data[st]["miles"] += miles
        state_data[st]["purchased_gals"] += gals
        state_data[st]["fuel_cost"] += cost

    # Calculate overall Fleet MPG
    overall_mpg = (total_miles / total_gallons_purchased) if total_gallons_purchased > 0 else 9.5

    summary_by_state = []
    total_net_tax_due = 0.0

    for st, vals in state_data.items():
        st_miles = vals["miles"]
        st_purchased = vals["purchased_gals"]
        taxable_gals = round(st_miles / overall_mpg, 2)
        net_taxable_gals = round(taxable_gals - st_purchased, 2)
        tax_rate = STATE_TAX_RATES.get(st, 0.380)
        net_tax = round(net_taxable_gals * tax_rate, 2)
        total_net_tax_due += net_tax

        summary_by_state.append({
            "state": st,
            "miles": round(st_miles, 1),
            "taxable_gallons": taxable_gals,
            "purchased_gallons": round(st_purchased, 2),
            "net_gallons": net_taxable_gals,
            "tax_rate": tax_rate,
            "net_tax_due": net_tax
        })

    conn.close()
    return {
        "quarter": quarter,
        "total_miles": round(total_miles, 1),
        "total_gallons_purchased": round(total_gallons_purchased, 2),
        "fleet_mpg": round(overall_mpg, 2),
        "states": summary_by_state,
        "total_net_tax_due": round(total_net_tax_due, 2)
    }


# -------------------------------------------------------------
# 4. Heavy Commercial Vehicle & Clearance Hazard Engine
# -------------------------------------------------------------
def check_route_clearance_and_hazards(
    origin: str,
    destination: str,
    vehicle_height_inches: int = 150 # 12ft 6in
) -> Dict[str, Any]:
    """
    Checks commercial bridge clearances, parkway restrictions, and weight bans.
    Standard box trucks cannot travel on NY/NJ Parkways, Chicago Lake Shore Drive, etc.
    """
    KNOWN_HAZARDS = [
        {"route": "Lake Shore Drive (Chicago, IL)", "restriction": "Commercial Trucks Prohibited", "type": "BAN"},
        {"route": "Storrow Drive (Boston, MA)", "clearance_inches": 126, "type": "LOW_CLEARANCE", "desc": "10ft 6in bridge"},
        {"route": "Independence Ave Bridge (Kansas City, MO)", "clearance_inches": 144, "type": "LOW_CLEARANCE", "desc": "12ft 0in clearance"},
        {"route": "Merritt Parkway (CT)", "restriction": "All Commercial Vehicles Prohibited", "type": "BAN"}
    ]

    warnings = []
    # Simple corridor matching for demo
    if "Chicago" in origin or "Chicago" in destination:
        warnings.append({
            "severity": "CRITICAL",
            "message": "AVOID Lake Shore Drive (US-41): Commercial box trucks strictly prohibited with heavy fines."
        })
        warnings.append({
            "severity": "WARNING",
            "message": "Metra Viaduct clearances along NW side vary from 12'2\" to 13'6\". Follow designated Illinois STAA Truck Routes (I-90 / I-94 / I-290)."
        })

    return {
        "origin": origin,
        "destination": destination,
        "vehicle_height": f"{vehicle_height_inches // 12}ft {vehicle_height_inches % 12}in",
        "is_safe": len(warnings) == 0 or all(w["severity"] != "CRITICAL" for w in warnings),
        "hazards_detected": warnings,
        "recommended_nav": "STAA Designated Commercial Truck Corridors Only"
    }


# -------------------------------------------------------------
# 5. Preventative Maintenance, DVIR & Amenity Radar
# -------------------------------------------------------------
def get_maintenance_and_dvir_dashboard(unit_id: str = "UNIT-26FT-01") -> Dict[str, Any]:
    """
    Returns asset uptime status, DVIR pre/post-trip compliance,
    and upcoming service thresholds (Oil, Brakes, Tires, DPF).
    """
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()

    vehicle = c.execute("SELECT * FROM fe_express_vehicle_profiles WHERE unit_id = ?", (unit_id,)).fetchone()
    logs = c.execute("SELECT * FROM fe_express_maintenance_dvir WHERE unit_id = ? ORDER BY created_at DESC LIMIT 5", (unit_id,)).fetchall()
    conn.close()

    v_data = dict(vehicle) if vehicle else {}
    history = [dict(row) for row in logs]

    # Standard commercial box truck maintenance service intervals (miles)
    SERVICE_INTERVALS = [
        {"service": "Engine Oil & Fuel Filter", "interval_miles": 15000, "current_odometer": 84200, "next_due": 90000, "status": "GOOD"},
        {"service": "Brake Lining & Drums Inspection", "interval_miles": 25000, "current_odometer": 84200, "next_due": 85000, "status": "ATTENTION_SOON"},
        {"service": "DPF Regeneration / Clean", "interval_miles": 50000, "current_odometer": 84200, "next_due": 100000, "status": "GOOD"},
        {"service": "Annual Federal DOT Inspection", "interval_miles": None, "current_odometer": 84200, "next_due": "2027-04-15", "status": "CURRENT"}
    ]

    return {
        "vehicle_profile": v_data,
        "current_odometer": 84200,
        "dvir_status": "COMPLIANT (Pre-Trip Signed 2026-10-21)",
        "service_intervals": SERVICE_INTERVALS,
        "recent_logs": history
    }


if __name__ == "__main__":
    init_owner_operator_tables()
    print("Owner-Operator database tables initialized.")
    chains = build_triangulation_chains()
    print(f"Generated {len(chains)} Triangulation Loops.")
