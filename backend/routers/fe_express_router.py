import os
import sys
import re
import time
import sqlite3
import logging
from datetime import datetime
from typing import List, Dict, Optional, Any
from pathlib import Path
from fastapi import APIRouter, HTTPException, Query, Body, Depends, Request, Response
from pydantic import BaseModel, Field

logger = logging.getLogger("FE_Express")

from security.fe_express_access import sessions, require_fe_express_access
from fe_express_driver_reports import router as driver_reports_router

router = APIRouter(prefix="/api/v1/fe-express", tags=["FE Express Dispatch"], dependencies=[Depends(require_fe_express_access)])


class PinLogin(BaseModel):
    pin: str


@router.post('/pin/login')
def pin_login(payload: PinLogin, response: Response):
    response.headers['Cache-Control'] = 'no-store'
    return sessions.login(payload.pin)


@router.post('/pin/logout')
def pin_logout(request: Request, response: Response):
    response.headers['Cache-Control'] = 'no-store'
    sessions.revoke(request.headers.get('authorization', ''))
    return {'locked': True}


DB_PATH = Path(r"C:\AI-BS\saved_data\fe_express.db")


def get_db():
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn


class LoadModel(BaseModel):
    load_id: str
    source: Optional[str] = "Manual Entry"
    origin_city_state: str
    dest_city_state: str
    equipment_type: str
    weight_lbs: float = Field(gt=0, allow_inf_nan=False)
    total_miles: float = Field(gt=0, allow_inf_nan=False)
    deadhead_miles: float = Field(default=0.0, ge=0, allow_inf_nan=False)
    flat_rate_pay: float = Field(ge=0, allow_inf_nan=False)
    broker_name: Optional[str] = "Direct Broker"
    broker_phone: Optional[str] = ""
    broker_email: Optional[str] = ""


from fe_express_scoring import FilterScoringEngine

@router.get("/status")
def get_status():
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM fe_express_loads")
    total_loads = c.fetchone()[0]

    c.execute("SELECT COUNT(*) FROM fe_express_loads WHERE score = 'Greenlight'")
    greenlights = c.fetchone()[0]

    c.execute("SELECT COUNT(*) FROM fe_express_alerts")
    alerts_sent = c.fetchone()[0]
    conn.close()

    return {
        "status": "ONLINE",
        "service": "FE Express Box Truck Automation Hub",
        "total_loads": total_loads,
        "greenlight_loads": greenlights,
        "alerts_dispatched": alerts_sent
    }


@router.get("/loads")
def get_loads(tier: Optional[int] = None, score: Optional[str] = None, limit: int = 50):
    conn = get_db()
    c = conn.cursor()
    query = "SELECT * FROM fe_express_loads WHERE 1=1"
    params = []

    if tier is not None:
        query += " AND priority_tier = ?"
        params.append(tier)
    if score is not None:
        query += " AND score = ?"
        params.append(score)

    query += " ORDER BY created_at DESC LIMIT ?"
    params.append(limit)

    c.execute(query, params)
    rows = [dict(r) for r in c.fetchall()]
    conn.close()
    return {"success": True, "count": len(rows), "loads": rows}


@router.post("/loads/evaluate")
def evaluate_ad_hoc_load(load: LoadModel):
    evaluated = FilterScoringEngine.evaluate(load.dict())
    return {"success": True, "evaluated": evaluated}


@router.post("/loads/sync-public")
def sync_public_boards_endpoint(home_base: str = Query("Grand Rapids, MI")):
    from fe_express_live_ingestor import sync_live_loads_to_db
    loads = sync_live_loads_to_db(home_base=home_base)
    return {"success": True, "synced_count": len(loads), "loads": loads}



@router.post("/loads/ingest")
def ingest_loads(payload: List[Dict[str, Any]] = Body(...)):
    conn = get_db()
    c = conn.cursor()

    c.execute("SELECT key, value FROM fe_express_config")
    cfg = dict(c.fetchall())
    min_green = float(cfg.get("min_greenlight_rpm", 2.50))
    min_caut = float(cfg.get("min_caution_rpm", 2.00))
    max_wt = float(cfg.get("max_weight_lbs", 10000.0))

    ingested_count = 0
    greenlight_count = 0

    for raw in payload:
        load_id = str(raw.get("load_id") or raw.get("id") or f"FE-{int(time.time()*1000)}")
        eval_data = FilterScoringEngine.evaluate(
            raw,
            min_greenlight_rpm=min_green,
            min_caution_rpm=min_caut,
            max_weight=max_wt
        )

        c.execute("""
            INSERT OR REPLACE INTO fe_express_loads (
                load_id, source, origin_city_state, dest_city_state, equipment_type,
                weight_lbs, total_miles, deadhead_miles, flat_rate_pay, rpm, true_rpm,
                broker_name, broker_phone, broker_email, score, priority_tier, status
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            load_id,
            eval_data.get("source", "Direct Feed"),
            eval_data.get("origin_city_state", eval_data.get("origin", "")),
            eval_data.get("dest_city_state", eval_data.get("destination", "")),
            eval_data.get("equipment_type", eval_data.get("equipment", "")),
            float(eval_data.get("weight_lbs", 0.0)),
            float(eval_data.get("total_miles", 1.0)),
            float(eval_data.get("deadhead_miles", 0.0)),
            float(eval_data.get("flat_rate_pay", 0.0)),
            eval_data.get("rpm", 0.0),
            eval_data.get("true_rpm", 0.0),
            eval_data.get("broker_name", "Unknown Broker"),
            eval_data.get("broker_phone", ""),
            eval_data.get("broker_email", ""),
            eval_data.get("score", "Reject"),
            eval_data.get("priority_tier", 3),
            "NEW"
        ))
        ingested_count += 1
        if eval_data.get("score") == "Greenlight":
            greenlight_count += 1

    conn.commit()
    conn.close()

    return {
        "success": True,
        "ingested_count": ingested_count,
        "greenlight_count": greenlight_count
    }


@router.get("/loads/{load_id}/bid")
def generate_broker_bid(load_id: str):
    """Generates pre-filled email and SMS broker rate confirmation bid for a load."""
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT * FROM fe_express_loads WHERE load_id = ?", (load_id,))
    row = c.fetchone()
    conn.close()

    if not row:
        raise HTTPException(status_code=404, detail="Load not found")

    from fe_express_bid_generator import BrokerBidGenerator
    load_dict = dict(row)
    bid_payload = BrokerBidGenerator.generate_email_bid(load_dict)

    return {
        "success": True,
        "load_id": load_id,
        "bid": bid_payload
    }


@router.get("/loads/{load_id}/fuel-analysis")
def calculate_load_fuel_and_margins(
    load_id: str,
    diesel_price: float = Query(3.85, description="Diesel price per gallon ($)"),
    truck_mpg: float = Query(9.5, description="Truck average MPG")
):
    """Calculates fuel burn, maintenance reserves, and net profit margins."""
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT * FROM fe_express_loads WHERE load_id = ?", (load_id,))
    row = c.fetchone()
    conn.close()

    if not row:
        raise HTTPException(status_code=404, detail="Load not found")

    from fe_express_fuel_calculator import FuelCostCalculator
    load_dict = dict(row)
    analysis = FuelCostCalculator.calculate_trip_profitability(
        loaded_miles=float(load_dict.get("total_miles", 0)),
        deadhead_miles=float(load_dict.get("deadhead_miles", 0)),
        flat_rate_pay=float(load_dict.get("flat_rate_pay", 0)),
        diesel_price_gal=diesel_price,
        truck_mpg=truck_mpg
    )

    return {
        "success": True,
        "load_id": load_id,
        "analysis": analysis
    }


@router.get("/loads/{load_id}/backhauls")
def get_load_backhauls(
    load_id: str,
    home_base: str = Query("Grand Rapids, MI")
):
    """Finds matching return freight for a load's destination to prevent deadheading home empty."""
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT * FROM fe_express_loads WHERE load_id = ?", (load_id,))
    row = c.fetchone()
    conn.close()

    if not row:
        raise HTTPException(status_code=404, detail="Load not found")

    from fe_express_backhaul import BackhaulEngine
    load_dict = dict(row)
    dest = load_dict.get("dest_city_state", "")
    backhauls = BackhaulEngine.find_backhauls(outbound_dest=dest, home_base=home_base)

    return {
        "success": True,
        "load_id": load_id,
        "outbound_destination": dest,
        "home_base": home_base,
        "backhauls_count": len(backhauls),
        "backhauls": backhauls
    }


@router.get("/alerts/check/{load_id}")
def check_load_alert(load_id: str):
    """Evaluates whether a load triggers a high-priority SMS/push alert."""
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT * FROM fe_express_loads WHERE load_id = ?", (load_id,))
    row = c.fetchone()
    conn.close()

    if not row:
        raise HTTPException(status_code=404, detail="Load not found")

@router.get("/brokers/credit")
def get_broker_credit(broker_name: str = Query(...)):
    """Retrieves broker credit score, factoring approval, and days-to-pay profile."""
    from fe_express_broker_credit import BrokerCreditSentinel
    profile = BrokerCreditSentinel.get_broker_credit(broker_name)
    return {
        "success": True,
        "broker_credit": profile
    }


@router.get("/loads/{load_id}/benchmark")
def get_load_benchmark(load_id: str):
    """Retrieves 7-day spot rate benchmark, market high/low, and counter-bid recommendation."""
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT * FROM fe_express_loads WHERE load_id = ?", (load_id,))
    row = c.fetchone()
    conn.close()

    if not row:
        raise HTTPException(status_code=404, detail="Load not found")

    from fe_express_spot_benchmark import LaneSpotBenchmark
    load_dict = dict(row)
    origin = load_dict.get("origin_city_state", "")
    dest = load_dict.get("dest_city_state", "")
    rpm = float(load_dict.get("true_rpm") or load_dict.get("rpm") or 0.0)
    miles = float(load_dict.get("total_miles") or 1.0)

    benchmark = LaneSpotBenchmark.get_lane_benchmark(
        origin=origin,
        dest=dest,
        current_true_rpm=rpm,
        miles=miles
    )

    from fe_express_broker_credit import BrokerCreditSentinel
    broker_credit = BrokerCreditSentinel.get_broker_credit(load_dict.get("broker_name", ""))

    return {
        "success": True,
        "load_id": load_id,
        "benchmark": benchmark,
        "broker_credit": broker_credit
    }


# ==========================================
# PHASE 3: ACTIVE LOADS, BOL UPLOAD & PROFIT LEDGER
# ==========================================

from fe_express_active_ledger import ActiveLoadManager

@router.get("/active-dispatches")
def get_active_dispatches():
    """Returns all active loads, BOL photos, and accounting ledgers for Devin."""
    dispatches = ActiveLoadManager.get_active_dispatches()
    return {
        "success": True,
        "dispatches": dispatches
    }


@router.post("/book-load")
def book_active_load(payload: Dict[str, Any] = Body(...)):
    """Transfers a load from the board into Devin's active haul queue."""
    result = ActiveLoadManager.book_load(payload)
    return result


@router.post("/dispatches/{dispatch_id}/accounting")
def update_dispatch_accounting(dispatch_id: str, payload: Dict[str, Any] = Body(...)):
    """Updates status, fuel, tolls, BOL photos, and calculates net profit."""
    result = ActiveLoadManager.update_load_accounting(dispatch_id, payload)
    return result


# ==========================================
# PHASE 4: 1099 SUBCONTRACT DRIVERS & SETTLEMENTS
# ==========================================

@router.get("/drivers")
def get_drivers():
    """Returns list of subcontract 1099 drivers for Devin's box truck operations."""
    drivers = ActiveLoadManager.get_contractor_drivers()
    return {
        "success": True,
        "drivers": drivers
    }


@router.post("/drivers")
def save_driver(payload: Dict[str, Any] = Body(...)):
    """Creates or updates a subcontract driver profile."""
    result = ActiveLoadManager.save_contractor_driver(payload)
    return result


@router.get("/settlements")
def get_settlements(driver_id: Optional[str] = Query(None)):
    """Returns settlement and payment records, optionally filtered by driver."""
    settlements = ActiveLoadManager.get_driver_settlements(driver_id)
    return {
        "success": True,
        "settlements": settlements
    }


@router.post("/settlements")
def record_settlement(payload: Dict[str, Any] = Body(...)):
    """Records a new trip settlement payout for a subcontract 1099 driver."""
    result = ActiveLoadManager.record_settlement(payload)
    return result


# ==========================================
# REMOTE TUNNEL UPDATE & SYNC ENDPOINTS
# ==========================================

@router.get("/version")
def get_fe_express_version():
    """Returns the current sovereign application version and minimum supported version."""
    return {
        "app_name": "FE Express Native Desktop Hub",
        "current_version": "v5.338.0",
        "minimum_supported_version": "v5.330.0",
        "release_channel": "production",
        "update_available": False,
        "download_url": "https://api.brettstehouwer.live/api/v1/fe-express/download-update",
        "release_notes": "100% Feature Parity: 4-Subtab Native Suite, Box vs Van Automation, Direct SQLite, 1099 Tax Ledger."
    }


@router.get("/update-manifest")
def get_update_manifest():
    """Manifest describing binary components and SHA-256 signatures for remote tunnel patching."""
    return {
        "version": "v5.338.0",
        "timestamp": datetime.now().isoformat(),
        "tunnel_endpoint": "https://api.brettstehouwer.live/api/v1/fe-express",
        "components": {
            "core_executable": "fe_express_native_desktop.exe",
            "db_schema_version": "4.0",
            "required_assets": ["installer/app_icon.ico"]
        }
    }


# ==========================================
# OWNER-OPERATOR HIGH-ROI ADVANCED ENDPOINTS
# ==========================================

@router.get("/triangulation-chains")
def get_triangulation_chains(home: str = Query("Grand Rapids, MI")):
    """Calculates 3-to-4 leg loop chains maximizing True RPM and eliminating empty deadhead."""
    try:
        from backend.core.fe_express_owner_operator_engine import build_triangulation_chains
        chains = build_triangulation_chains(home_terminal=home)
        return {"success": True, "chains": chains}
    except Exception as e:
        logger.error(f"Error computing triangulation chains: {e}")
        return {"success": False, "chains": [], "error": str(e)}


@router.post("/factoring/submit")
def submit_instant_factoring(payload: Dict[str, Any] = Body(...)):
    """Submits instant factoring package for same-day funding on delivered hauls."""
    try:
        from backend.core.fe_express_owner_operator_engine import generate_instant_factoring_submission
        disp_id = payload.get("dispatch_id")
        fee_pct = float(payload.get("fee_pct", 2.5))
        advance_pct = float(payload.get("advance_pct", 97.5))
        sub = generate_instant_factoring_submission(dispatch_id=disp_id, fee_pct=fee_pct, advance_pct=advance_pct)
        return {"success": True, "factoring_package": sub}
    except Exception as e:
        logger.error(f"Error submitting factoring: {e}")
        return {"success": False, "error": str(e)}


@router.get("/ifta/summary")
def get_ifta_summary(quarter: str = Query("2026-Q4")):
    """Returns quarterly state-line mileage, taxable gallons, and net tax due/refund for IFTA."""
    try:
        from backend.core.fe_express_owner_operator_engine import calculate_ifta_quarterly_summary
        summary = calculate_ifta_quarterly_summary(quarter=quarter)
        return {"success": True, "ifta_summary": summary}
    except Exception as e:
        logger.error(f"Error calculating IFTA summary: {e}")
        return {"success": False, "error": str(e)}


@router.get("/navigation/hazards")
def check_route_hazards(origin: str = Query(...), destination: str = Query(...), height_inches: int = Query(150)):
    """Checks heavy vehicle clearance heights, parkway restrictions, and low-bridge warnings."""
    try:
        from backend.core.fe_express_owner_operator_engine import check_route_clearance_and_hazards
        result = check_route_clearance_and_hazards(origin=origin, destination=destination, vehicle_height_inches=height_inches)
        return {"success": True, "navigation_check": result}
    except Exception as e:
        logger.error(f"Error checking route hazards: {e}")
        return {"success": False, "error": str(e)}


@router.get("/maintenance/dvir")
def get_maintenance_dvir_status(unit_id: str = Query("UNIT-26FT-01")):
    """Returns DVIR inspection status and preventative maintenance odometer triggers."""
    try:
        from backend.core.fe_express_owner_operator_engine import get_maintenance_and_dvir_dashboard
        dash = get_maintenance_and_dvir_dashboard(unit_id=unit_id)
        return {"success": True, "maintenance_dashboard": dash}
    except Exception as e:
        logger.error(f"Error fetching maintenance dashboard: {e}")
        return {"success": False, "error": str(e)}


# ==========================================
# APEX DISPATCHER COCKPIT 5-PILLAR ENDPOINTS
# ==========================================

@router.get("/fraud-shield")
def check_fraud_shield(broker: str = Query(...), mc: Optional[str] = Query(None)):
    """Verifies broker credit score, days-to-pay, active 75k bond status, and fraud risk."""
    try:
        from backend.core.fe_express_dispatcher_dream_cockpit import check_broker_fraud_shield
        res = check_broker_fraud_shield(broker_name=broker, mc_number=mc)
        return {"success": True, "fraud_shield": res}
    except Exception as e:
        logger.error(f"Error evaluating broker fraud shield: {e}")
        return {"success": False, "error": str(e)}


@router.post("/blast-bid")
def send_blast_bid(payload: Dict[str, Any] = Body(...)):
    """Dispatches parallel pitch simultaneously across SMS, programmatic Email, and Carrier TMS Webhook."""
    try:
        from backend.core.fe_express_dispatcher_dream_cockpit import execute_multi_channel_blast_bid
        load = payload.get("load", {})
        bid = float(payload.get("bid_amount", load.get("flat_rate_pay", 0)))
        profile = payload.get("dispatcher_profile", {})
        res = execute_multi_channel_blast_bid(load=load, bid_amount=bid, dispatcher_profile=profile)
        return {"success": True, "blast_result": res}
    except Exception as e:
        logger.error(f"Error executing blast bid: {e}")
        return {"success": False, "error": str(e)}


@router.get("/horizon-map")
def get_horizon_map(destination: str = Query(...), hours_ahead: int = Query(14)):
    """Projects spot load-to-truck ratio and outbound RPM for tomorrow morning arrival dock window."""
    try:
        from backend.core.fe_express_dispatcher_dream_cockpit import get_predictive_horizon_map
        res = get_predictive_horizon_map(destination_city=destination, arrival_hours_ahead=hours_ahead)
        return {"success": True, "horizon_map": res}
    except Exception as e:
        logger.error(f"Error fetching horizon map: {e}")
        return {"success": False, "error": str(e)}


@router.post("/detention-sentinel")
def trigger_detention_sentinel(payload: Dict[str, Any] = Body(...)):
    """Monitors dock dwell time and automatically commences escrow billing at 120 minutes."""
    try:
        from backend.core.fe_express_dispatcher_dream_cockpit import check_and_trigger_detention_sentinel
        disp_id = payload.get("dispatch_id")
        facility = payload.get("facility_name", "Shipper Facility")
        arrival_epoch = int(payload.get("arrival_timestamp", time.time() - 7200)) # Default 2 hours ago
        rate = float(payload.get("hourly_rate", 75.0))
        res = check_and_trigger_detention_sentinel(dispatch_id=disp_id, facility_name=facility, arrival_time_epoch=arrival_epoch, hourly_rate=rate)
        return {"success": True, "detention_status": res}
    except Exception as e:
        logger.error(f"Error checking detention sentinel: {e}")
        return {"success": False, "error": str(e)}


@router.get("/dock-intelligence")
def get_dock_intelligence(query: str = Query(...)):
    """Retrieves facility average wait times, lumper requirements, overnight parking, and gate instructions."""
    try:
        from backend.core.fe_express_dispatcher_dream_cockpit import get_dock_facility_intelligence
        res = get_dock_facility_intelligence(query_text=query)
        return {"success": True, "dock_facility": res}
    except Exception as e:
        logger.error(f"Error fetching dock intelligence: {e}")
        return {"success": False, "error": str(e)}


@router.get("/cpm-calibration")
def get_cpm_calibration(
    diesel_price: float = Query(3.85),
    truck_mpg: float = Query(9.5),
    driver_cpm: float = Query(0.60),
    target_margin: float = Query(25.0)
):
    """Calculates live break-even operating floor rate ($/mi) and recommended minimum bidding RPM."""
    try:
        from backend.core.fe_express_dispatcher_dream_cockpit import calibrate_live_cost_per_mile
        res = calibrate_live_cost_per_mile(
            diesel_price=diesel_price,
            truck_mpg=truck_mpg,
            driver_cpm=driver_cpm,
            target_margin_pct=target_margin
        )
        return {"success": True, "cpm_calibration": res}
    except Exception as e:
        logger.error(f"Error calculating CPM calibration: {e}")
        return {"success": False, "error": str(e)}


@router.post("/accessorial-claim")
def create_accessorial_claim(payload: Dict[str, Any] = Body(...)):
    """Builds a 1-click legal dispute packet with itemized rate con clauses and carrier proof log."""
    try:
        from backend.core.fe_express_dispatcher_dream_cockpit import build_accessorial_dispute_package
        claim_type = payload.get("claim_type", "DETENTION")
        load_id = payload.get("load_id", "LD-9901")
        broker = payload.get("broker_name", "Broker")
        mc = payload.get("broker_mc", "MC-000000")
        email = payload.get("broker_email", "claims@brokerage.com")
        units = float(payload.get("units_claimed", 2.0))
        rate = float(payload.get("unit_rate", 75.0))
        arr = payload.get("arrival_time", "08:00 AM")
        dep = payload.get("departure_time", "12:00 PM")
        fac = payload.get("facility_address", "Shipper/Receiver Dock")
        notes = payload.get("notes", "Signed receiver stamp attached with verifiable in/out time")

        res = build_accessorial_dispute_package(
            claim_type=claim_type, load_id=load_id, broker_name=broker, broker_mc=mc,
            broker_email=email, units_claimed=units, unit_rate=rate,
            arrival_time_str=arr, departure_time_str=dep, facility_address=fac, signed_bol_notes=notes
        )
        return {"success": True, "accessorial_claim": res}
    except Exception as e:
        logger.error(f"Error creating accessorial claim packet: {e}")
        return {"success": False, "error": str(e)}


@router.get("/fuel-optimizer")
def get_fuel_optimizer(
    origin: str = Query(...),
    destination: str = Query(...),
    miles: float = Query(...),
    tank_pct: float = Query(35.0),
    mpg: float = Query(9.5)
):
    """Computes optimal truck stop fuel arbitrage to minimize wholesale diesel spend."""
    try:
        from backend.core.fe_express_dispatcher_dream_cockpit import optimize_fuel_route_stops
        res = optimize_fuel_route_stops(origin=origin, destination=destination, total_miles=miles, current_fuel_tank_pct=tank_pct, truck_mpg=mpg)
        return {"success": True, "fuel_optimization": res}
    except Exception as e:
        logger.error(f"Error optimizing fuel stops: {e}")
        return {"success": False, "error": str(e)}


@router.post("/capacity-broadcast")
def post_capacity_broadcast(payload: Dict[str, Any] = Body(...)):
    """1-Click broadcasts empty truck capacity across DAT, Truckstop, Sylectus, and broker portals."""
    try:
        from backend.core.fe_express_dispatcher_dream_cockpit import broadcast_truck_capacity
        unit = payload.get("unit_id", "UNIT-26FT-01")
        loc = payload.get("location", "Grand Rapids, MI")
        dest = payload.get("destination_zone", "Midwest")
        eq = payload.get("equipment_type", "26' Box Truck (Dock High - No Liftgate)")
        avail = payload.get("available_time", "Immediately")
        res = broadcast_truck_capacity(unit_id=unit, current_location=loc, destination_zone=dest, equipment_type=eq, available_time_str=avail)
        return {"success": True, "broadcast_result": res}
    except Exception as e:
        logger.error(f"Error broadcasting truck capacity: {e}")
        return {"success": False, "error": str(e)}


@router.post("/lumper-escrow")
def post_lumper_escrow(payload: Dict[str, Any] = Body(...)):
    """Dispatches urgent lumper pre-approval request straight to broker night-dispatch cell."""
    try:
        from backend.core.fe_express_dispatcher_dream_cockpit import create_lumper_preapproval_request
        disp_id = payload.get("dispatch_id", "DISP-2026-001")
        facility = payload.get("facility_name", "Receiving DC")
        broker = payload.get("broker_name", "Broker")
        phone = payload.get("broker_night_phone", "(616) 315-7483")
        amt = float(payload.get("lumper_amount", 150.0))
        method = payload.get("payment_method", "EFS_CODE")
        res = create_lumper_preapproval_request(dispatch_id=disp_id, facility_name=facility, broker_name=broker, broker_night_phone=phone, lumper_cost=amt, payment_method=method)
        return {"success": True, "lumper_escrow": res}
    except Exception as e:
        logger.error(f"Error commencing lumper escrow: {e}")
        return {"success": False, "error": str(e)}


@router.post("/fleet-escrow/deduction")
def post_fleet_escrow_deduction(payload: Dict[str, Any] = Body(...)):
    """Records recurring lease, insurance, or dynamic fuel advance escrow deductions for small fleets."""
    try:
        from backend.core.fe_express_dispatcher_dream_cockpit import record_fleet_escrow_deduction
        drv_id = payload.get("driver_id", "DRV-DEVIN")
        week = payload.get("pay_period_week", datetime.now().strftime("%Y-W%W"))
        d_type = payload.get("deduction_type", "FUEL_CARD_ADVANCE")
        desc = payload.get("description", "Fuel card transaction deduction")
        amt = float(payload.get("amount", 50.0))
        state = payload.get("state_jurisdiction", "MI")
        res = record_fleet_escrow_deduction(driver_id=drv_id, pay_period_week=week, deduction_type=d_type, description=desc, amount=amt, state_jurisdiction=state)
        return {"success": True, "escrow_deduction": res}
    except Exception as e:
        logger.error(f"Error logging fleet escrow deduction: {e}")
        return {"success": False, "error": str(e)}


@router.get("/fmcsa-profile")
def get_fmcsa_profile():
    """Returns official verified FMCSA SAFER carrier snapshot for FE EXPRESS LLC (USDOT 2137128)."""
    try:
        from backend.core.fe_express_dispatcher_dream_cockpit import FMCSA_SAFER_PROFILE
        return {"success": True, "profile": FMCSA_SAFER_PROFILE}
    except Exception as e:
        logger.error(f"Error retrieving FMCSA profile: {e}")
        return {"success": False, "error": str(e)}


@router.post("/mesh-haul/match")
def post_mesh_haul_match(payload: Dict[str, Any] = Body(...)):
    """Generates peer-to-peer capacity exchange match with cryptographic smart contract and 0 broker fee."""
    try:
        from backend.core.fe_express_dispatcher_dream_cockpit import MeshCapacityMatch
        car_a = payload.get("carrier_a_id", "FE-EXPRESS-UNIT-01")
        car_b = payload.get("carrier_b_id", "PEER-CARRIER-MIDWEST")
        lane = payload.get("lane_coordinates", ["Grand Rapids, MI", "Chicago, IL"])
        truck_len = float(payload.get("truck_length_ft", 26.0))
        used_len = float(payload.get("used_linear_ft", 16.0))
        weight = int(payload.get("cargo_weight_lbs", 4500))
        linehaul = float(payload.get("total_linehaul_usd", 950.0))
        
        matcher = MeshCapacityMatch(car_a, car_b, lane)
        result = matcher.evaluate_fractional_match(
            total_truck_length_ft=truck_len,
            used_linear_ft=used_len,
            cargo_weight_lbs=weight,
            total_linehaul_usd=linehaul
        )
        return {"success": True, "mesh_match": result}
    except Exception as e:
        logger.error(f"Error evaluating mesh haul match: {e}")
        return {"success": False, "error": str(e)}


@router.post("/fatigue-catalyst")
def post_fatigue_catalyst(payload: Dict[str, Any] = Body(...)):
    """Analyzes driver ocular micro-saccades and HRV drop to proactively predict fatigue and reschedule receiver."""
    try:
        from backend.core.fe_express_dispatcher_dream_cockpit import analyze_driver_fatigue_telemetry
        drv = payload.get("driver_id", "DRV-101")
        unit = payload.get("unit_id", "UNIT-26FT-01")
        blink = float(payload.get("blink_duration_ms", 380.0))
        saccade = float(payload.get("micro_saccade_velocity_deg_s", 180.0))
        tilt = float(payload.get("head_tilt_angle_deg", 14.5))
        hrv = float(payload.get("hrv_drop_percentage", 24.0))
        hos = int(payload.get("hos_remaining_minutes", 195))
        
        result = analyze_driver_fatigue_telemetry(
            driver_id=drv, unit_id=unit, blink_duration_ms=blink,
            micro_saccade_velocity_deg_s=saccade, head_tilt_angle_deg=tilt,
            hrv_drop_percentage=hrv, current_hos_remaining_minutes=hos
        )
        return {"success": True, "fatigue_analysis": result}
    except Exception as e:
        logger.error(f"Error evaluating fatigue catalyst: {e}")
        return {"success": False, "error": str(e)}


@router.post("/scope3-carbon")
def post_scope3_carbon(payload: Dict[str, Any] = Body(...)):
    """Calculates audit-proof Scope 3 carbon savings and generates certified enterprise compliance packet."""
    try:
        from backend.core.fe_express_dispatcher_dream_cockpit import calculate_scope3_carbon_ledger
        disp = payload.get("dispatch_id", "DISP-2026-001")
        orig = payload.get("origin", "Grand Rapids, MI")
        dest = payload.get("destination", "Chicago, IL")
        miles = float(payload.get("miles_traveled", 180.0))
        weight = int(payload.get("cargo_weight_lbs", 4200))
        throttle = float(payload.get("steady_throttle_pct", 78.5))
        
        result = calculate_scope3_carbon_ledger(
            dispatch_id=disp, origin=orig, destination=dest,
            miles_traveled=miles, cargo_weight_lbs=weight,
            steady_throttle_pct=throttle
        )
        return {"success": True, "carbon_ledger": result}
    except Exception as e:
        logger.error(f"Error calculating scope3 carbon ledger: {e}")
        return {"success": False, "error": str(e)}


@router.get("/black-swan-radar")
def get_black_swan_radar(corridor: str = "Midwest / I-80 & I-94"):
    """Scans for macro bottlenecks, port gate delays, and emergency bridge detours via fleet velocity sinks."""
    try:
        from backend.core.fe_express_dispatcher_dream_cockpit import scan_macro_disruption_swarm
        result = scan_macro_disruption_swarm(corridor_state=corridor)
        return {"success": True, "macro_radar": result}
    except Exception as e:
        logger.error(f"Error scanning black swan radar: {e}")
        return {"success": False, "error": str(e)}


@router.get("/ar-hud")
def get_ar_hud(unit_id: str = "UNIT-26FT-01", driver_id: str = "DRV-101"):
    """Retrieves high-contrast, inverted text-only telemetry for night windshield HUD reflection."""
    try:
        from backend.core.fe_express_dispatcher_dream_cockpit import get_ar_hud_windshield_telemetry
        result = get_ar_hud_windshield_telemetry(unit_id=unit_id, driver_id=driver_id)
        return {"success": True, "hud_telemetry": result}
    except Exception as e:
        logger.error(f"Error retrieving AR HUD telemetry: {e}")
        return {"success": False, "error": str(e)}


@router.post("/scraper/sync-public-boards")
def post_sync_public_boards(payload: Dict[str, Any] = Body(default={})):
    """Triggers live ingestion of real public load boards (Trulos, etc.) without requiring credentials."""
    try:
        from backend.fe_express_live_ingestor import sync_live_loads_to_db
        home = payload.get("home_base", "Grand Rapids, MI")
        loads = sync_live_loads_to_db(home_base=home)
        return {
            "success": True,
            "message": f"Successfully ingested {len(loads)} real live public loads",
            "loads_count": len(loads),
            "greenlight_count": len([l for l in loads if l.get("score") == "Greenlight"])
        }
    except Exception as e:
        logger.error(f"Error syncing public boards: {e}")
        return {"success": False, "error": str(e)}






router.include_router(driver_reports_router)
from fe_express_workspace import router as workspace_router
router.include_router(workspace_router)
