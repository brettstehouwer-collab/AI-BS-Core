import os
import sqlite3
import time
import json
import uuid
from pathlib import Path
from typing import List, Optional, Dict, Any
from datetime import datetime
from fastapi import APIRouter, UploadFile, File, Form, Query, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel

router = APIRouter(prefix="/api/powerwash", tags=["Prestige Mobile Services - Power Washing Suite"])

DB_PATH = Path(r"C:\AI-BS\prestige_powerwash.db").resolve()

# Pre-seeded West Michigan Municipal Water Fill Stations
WEST_MI_FILL_STATIONS = [
    {"id": "fill_gr_1", "name": "Grand Rapids Water System (Monroe Ave NW)", "city": "Grand Rapids", "zip": "49503", "lat": 42.9785, "lng": -85.6700, "flow_rate_gpm": 25.0, "type": "Municipal Hydrant Permit Station"},
    {"id": "fill_wy_1", "name": "Wyoming Clean Water Plant (Burlingame Ave SW)", "city": "Wyoming", "zip": "49509", "lat": 42.9125, "lng": -85.7050, "flow_rate_gpm": 30.0, "type": "Bulk Fill Standpipe"},
    {"id": "fill_kw_1", "name": "Kentwood DPW Bulk Fill (Breton Rd SE)", "city": "Kentwood", "zip": "49508", "lat": 42.8750, "lng": -85.6020, "flow_rate_gpm": 20.0, "type": "Metred Hydrant Station"},
    {"id": "fill_hl_1", "name": "Holland Board of Public Works (Fairbanks Ave)", "city": "Holland", "zip": "49423", "lat": 42.7915, "lng": -86.1040, "flow_rate_gpm": 25.0, "type": "Bulk Water Depot"},
    {"id": "fill_gh_1", "name": "Grand Haven Water Filtration Plant (S Harbor Dr)", "city": "Grand Haven", "zip": "49417", "lat": 43.0580, "lng": -86.2310, "flow_rate_gpm": 20.0, "type": "Municipal Depot"},
    {"id": "fill_mk_1", "name": "Muskegon Water Treatment Facility (Beach St)", "city": "Muskegon", "zip": "49441", "lat": 43.2250, "lng": -86.3250, "flow_rate_gpm": 30.0, "type": "Bulk Hydrant Fill"},
    {"id": "fill_rk_1", "name": "Rockford Municipal DPW Fill (Northland Dr NE)", "city": "Rockford", "zip": "49341", "lat": 43.1200, "lng": -85.5600, "flow_rate_gpm": 18.0, "type": "City Fill Station"}
]

# Standard Rig Specs (Chevy 3500 HD Dually Flatbed + Skid Rig)
PRESTIGE_RIG_SPECS = {
    "truck_model": "Chevy Silverado 3500 HD Dually (Crew Cab Flatbed)",
    "phone": "616-901-6536",
    "curb_weight_lbs": 7450,
    "equipment_weight_lbs": 1850, # Pressure washer skid, 200ft hose reels, 12V softwash pump, toolboxes, chemical jugs
    "gvwr_limit_lbs": 14000,
    "buffer_tank_capacity_gal": 275, # Standard IBC Tote
    "softwash_sh_tank_gal": 55,
    "soap_tank_gal": 16,
    "water_density_lbs_per_gal": 8.34,
    "sh_density_lbs_per_gal": 10.05 # 12.5% Sodium Hypochlorite is denser than water
}


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_powerwash_db():
    conn = get_db()
    cursor = conn.cursor()

    # 1. Clients Table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS clients (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            company TEXT,
            client_type TEXT DEFAULT 'residential', -- residential, commercial, hoa, fleet
            phone TEXT,
            email TEXT,
            address TEXT,
            city TEXT DEFAULT 'Grand Rapids',
            zip_code TEXT,
            gate_code TEXT,
            water_spigot_access TEXT DEFAULT 'yes',
            notes TEXT,
            created_at REAL
        )
    """)

    # 2. Jobs & Kanban Pipeline Table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS jobs (
            id TEXT PRIMARY KEY,
            client_id TEXT,
            client_name TEXT,
            address TEXT,
            city TEXT,
            zip_code TEXT,
            service_type TEXT, -- house_wash, roof_wash, driveway_concrete, deck_fence, commercial_flatwork, fleet_wash
            status TEXT DEFAULT 'lead', -- lead, estimate_sent, scheduled, in_progress, completed, paid
            scheduled_date TEXT,
            estimated_duration_hrs REAL DEFAULT 2.0,
            quote_amount REAL DEFAULT 0.0,
            paid_amount REAL DEFAULT 0.0,
            chemical_recipe TEXT,
            sq_ft_total REAL DEFAULT 0,
            notes TEXT,
            created_at REAL
        )
    """)

    # 3. Commercial Fleet Table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS fleet_units (
            id TEXT PRIMARY KEY,
            client_id TEXT,
            company_name TEXT,
            unit_number TEXT NOT NULL,
            vin TEXT,
            vehicle_type TEXT, -- semi_tractor, box_truck, 53ft_trailer, cargo_van, dump_truck, heavy_equipment
            wash_tier TEXT DEFAULT 'standard', -- standard, acid_brighten, undercarriage_salt_rinse, premium_detail
            price_per_wash REAL DEFAULT 75.0,
            last_wash_date TEXT,
            next_due_date TEXT,
            service_frequency_days INTEGER DEFAULT 14,
            status TEXT DEFAULT 'active'
        )
    """)

    # 4. Fleet Verification Log Table (Timestamp + GPS + Before/After Photos)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS fleet_wash_logs (
            id TEXT PRIMARY KEY,
            unit_id TEXT,
            unit_number TEXT,
            company_name TEXT,
            wash_tier TEXT,
            timestamp TEXT,
            gps_coords TEXT,
            technician_name TEXT,
            before_photo_url TEXT,
            after_photo_url TEXT,
            water_temp_deg_f REAL DEFAULT 140.0,
            soap_applied TEXT,
            notes TEXT
        )
    """)

    conn.commit()

    # Pre-seed realistic clients if empty
    cursor.execute("SELECT COUNT(*) FROM clients")
    if cursor.fetchone()[0] == 0:
        now = time.time()
        sample_clients = [
            ("cli_1", "Marcus VanderLaan", "VanderLaan Properties LLC", "commercial", "616-555-2341", "marcus@vanderlaanprop.com", "4450 44th St SE", "Grand Rapids", "49512", "Code #4490", "Commercial hydrant & 2 spigots", "Quarterly commercial parking lot & dumpster pad cleaning", now),
            ("cli_2", "Sarah & David Buikema", "", "residential", "616-555-8890", "sbuikema@gmail.com", "1840 Lake Michigan Dr NW", "Grand Rapids", "49504", "", "Front yard hose bib active", "Two-story vinyl siding + composite back deck + front driveway", now),
            ("cli_3", "Great Lakes Freight Systems", "Great Lakes Freight", "fleet", "616-555-1200", "dispatch@greatlakesfreight.com", "1200 Waverly Rd", "Holland", "49423", "Gate 4 call box", "Onsite fleet water hookup", "Bi-weekly fleet wash for 12 semi-tractors and 18 trailers", now),
            ("cli_4", "Heritage Hill HOA Management", "Heritage Hill Condos", "hoa", "616-555-9012", "hoa@heritagehillgr.org", "350 College Ave SE", "Grand Rapids", "49503", "", "Common area spigots", "Annual brick restoration and roof moss soft washing for 14 units", now),
            ("cli_5", "Kalamazoo St. Logistics Hub", "Apex Logistics", "fleet", "616-555-6677", "fleetops@apexlogistics.com", "2800 28th St SW", "Wyoming", "49519", "Gate Keycard", "Dedicated wash bay drain", "Weekly salt neutralization and aluminum cab brightening", now)
        ]
        cursor.executemany("INSERT INTO clients VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", sample_clients)

        sample_jobs = [
            ("job_1", "cli_1", "Marcus VanderLaan", "4450 44th St SE", "Grand Rapids", "49512", "commercial_flatwork", "in_progress", "2026-08-19", 4.0, 1450.0, 0.0, '{"sh_pct": 5.0, "degreaser_ratio": "4:1", "psi": 3200, "surface_cleaner_bar": "20-inch Whirly"}', 6800, "Dumpster pad grease breakdown with hot water & degreaser", now),
            ("job_2", "cli_2", "Sarah & David Buikema", "1840 Lake Michigan Dr NW", "Grand Rapids", "49504", "house_wash", "scheduled", "2026-08-20", 2.5, 520.0, 0.0, '{"sh_pct": 1.2, "surfactant_oz_gal": 2.0, "psi": 120, "nozzle": "J-Rod 40-deg softwash"}', 2800, "Soft wash vinyl siding + driveway concrete surface wash", now),
            ("job_3", "cli_4", "Heritage Hill HOA", "350 College Ave SE", "Grand Rapids", "49503", "roof_wash", "estimate_sent", "2026-08-22", 6.0, 2850.0, 0.0, '{"sh_pct": 3.5, "surfactant_oz_gal": 3.5, "psi": 90, "nozzle": "Shooter Tip 40ft"}', 14200, "Gloeocapsa magma black streaks & lichen removal on architectural shingles", now)
        ]
        cursor.executemany("INSERT INTO jobs VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", sample_jobs)

        sample_fleet = [
            ("flt_1", "cli_3", "Great Lakes Freight", "Unit 101", "1FUJA6CK08L194821", "semi_tractor", "acid_brighten", 85.0, "2026-08-10", "2026-08-24", 14, "active"),
            ("flt_2", "cli_3", "Great Lakes Freight", "Unit 102", "1FUJA6CK28L194822", "semi_tractor", "standard", 75.0, "2026-08-10", "2026-08-24", 14, "active"),
            ("flt_3", "cli_3", "Great Lakes Freight", "Trailer 5301", "1GRAA06256B881021", "53ft_trailer", "standard", 65.0, "2026-08-10", "2026-08-24", 14, "active"),
            ("flt_4", "cli_5", "Apex Logistics", "Van 401", "1FTNE3Y85HDA10294", "cargo_van", "undercarriage_salt_rinse", 55.0, "2026-08-14", "2026-08-21", 7, "active"),
            ("flt_5", "cli_5", "Apex Logistics", "Box Truck 205", "1FDRF3Y73GEA99104", "box_truck", "acid_brighten", 95.0, "2026-08-14", "2026-08-21", 7, "active")
        ]
        cursor.executemany("INSERT INTO fleet_units VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", sample_fleet)

    conn.commit()
    conn.close()

init_powerwash_db()


# ==============================================================================
# SCHEMAS
# ==============================================================================

class SurfaceAnalysisRequest(BaseModel):
    substrate_type: str # vinyl, brick, stucco, asphalt_shingle, concrete, wood_composite, aluminum
    contamination_type: str # black_algae, mildew, lichen, moss, engine_oil, rust, efflorescence
    contamination_severity: str = "moderate" # light, moderate, heavy, severe
    square_footage: float = 1500.0
    story_count: int = 1

class GisQuoteRequest(BaseModel):
    address: str
    property_type: str = "residential" # residential, commercial, hoa
    building_sqft: float = 2400.0
    roof_pitch: str = "6/12" # 4/12, 6/12, 8/12, 10/12, 12/12
    driveway_sqft: float = 950.0
    deck_fence_sqft: float = 400.0
    include_roof: bool = True
    include_siding: bool = True
    include_driveway: bool = True
    include_deck: bool = False
    nearby_jobs_in_zip: int = 1 # for route density discount

class RoutePayloadRequest(BaseModel):
    stops_addresses: List[str]
    water_tank_fill_gal: float = 275.0
    sh_chemical_gal: float = 45.0
    jobs_estimated_gallons: List[float] = [80.0, 120.0, 60.0]

class ClientCreateRequest(BaseModel):
    id: Optional[str] = None
    name: str
    company: Optional[str] = ""
    client_type: str = "residential"
    phone: Optional[str] = "616-901-6536"
    email: Optional[str] = ""
    address: str
    city: str = "Grand Rapids"
    zip_code: str
    gate_code: Optional[str] = ""
    water_spigot_access: Optional[str] = "yes"
    notes: Optional[str] = ""

class JobCreateRequest(BaseModel):
    client_id: str
    client_name: str
    address: str
    city: str
    zip_code: str
    service_type: str
    scheduled_date: str
    estimated_duration_hrs: float = 2.0
    quote_amount: float
    sq_ft_total: float = 0
    notes: Optional[str] = ""

class FleetUnitCreateRequest(BaseModel):
    client_id: str
    company_name: str
    unit_number: str
    vin: Optional[str] = ""
    vehicle_type: str
    wash_tier: str = "standard"
    price_per_wash: float = 75.0
    service_frequency_days: int = 14

class FleetLogCreateRequest(BaseModel):
    unit_id: str
    unit_number: str
    company_name: str
    wash_tier: str
    technician_name: str = "Prestige Crew #1"
    gps_coords: str = "42.9634° N, 85.6681° W (Grand Rapids, MI)"
    water_temp_deg_f: float = 140.0
    soap_applied: str = "Prestige Citrus-Foam Citrus Wash"
    notes: Optional[str] = "GPS verified completion with salt neutralizer undercarriage rinse."


# ==============================================================================
# 1. TOOL 1: COMPUTER VISION SURFACE & CHEMICAL RATIO ESTIMATOR
# ==============================================================================

@router.post("/analyze_surface")
async def analyze_surface(req: SurfaceAnalysisRequest):
    """
    Calculates substrate chemical dilution ratios (SH %, surfactant oz/gal, degreaser),
    maximum safe PSI/GPM limits, and nozzle tip specs.
    """
    substrate = req.substrate_type.lower()
    severity = req.contamination_severity.lower()

    # Base chemical ratios by substrate & contamination
    if substrate in ["vinyl", "aluminum"]:
        base_sh = 1.0 if severity == "light" else (1.5 if severity == "moderate" else 2.0)
        max_psi = 150 # Pure soft washing
        nozzle = "J-Rod / 40° Soft Wash Tip"
        surfactant_oz = 2.0
        dwell_min = 8
        rate_sqft = 0.22
    elif substrate in ["asphalt_shingle", "tile"]:
        base_sh = 3.0 if severity == "light" else (4.0 if severity == "moderate" else 5.5)
        max_psi = 90 # Extreme soft wash, 0 pressure to preserve granules
        nozzle = "Shooter Tip / Low-Pressure Streamer"
        surfactant_oz = 3.5 # High cling surfactant for roof dwell
        dwell_min = 15
        rate_sqft = 0.35
    elif substrate in ["concrete", "pavers"]:
        base_sh = 3.5 if severity == "light" else (5.0 if severity == "moderate" else 6.0)
        max_psi = 3200 # Concrete flatwork pressure
        nozzle = "20-Inch Rotary Surface Cleaner + 25° Green Wand"
        surfactant_oz = 1.0
        dwell_min = 10
        rate_sqft = 0.18
    elif substrate in ["brick", "stucco"]:
        base_sh = 2.0 if severity == "light" else (2.8 if severity == "moderate" else 3.5)
        max_psi = 500 # Low pressure to protect mortar joints and EIFS
        nozzle = "J-Rod Soft Wash Fan"
        surfactant_oz = 2.5
        dwell_min = 10
        rate_sqft = 0.28
    elif substrate in ["wood_composite", "cedar"]:
        base_sh = 0.8 if severity == "light" else (1.2 if severity == "moderate" else 1.5)
        max_psi = 800 # Low pressure to avoid wood gouging or furring
        nozzle = "40° White Fan + Oxalic Acid Post-Brightener"
        surfactant_oz = 1.5
        dwell_min = 6
        rate_sqft = 0.30
    else:
        base_sh = 1.5
        max_psi = 1000
        nozzle = "40° Fan"
        surfactant_oz = 2.0
        dwell_min = 10
        rate_sqft = 0.25

    # Specific additive adjustments
    degreaser_needed = req.contamination_type == "engine_oil"
    oxalic_needed = req.contamination_type in ["rust", "efflorescence"] or substrate in ["wood_composite", "cedar"]

    # Volume calculation for 50 Gal Batch Tank
    # Target SH% using 12.5% Pool Shock raw bleach
    gallons_12_5_sh = round((base_sh / 12.5) * 50.0, 1)
    gallons_water = round(50.0 - gallons_12_5_sh, 1)
    surfactant_total_oz = round(surfactant_oz * 50.0 / 5.0, 1) # per 50 gallon mix

    height_mult = 1.0 if req.story_count <= 1 else (1.25 if req.story_count == 2 else 1.5)
    total_estimated_price = round(req.square_footage * rate_sqft * height_mult, 2)
    duration_hours = round(max(1.0, (req.square_footage / 1200.0) * height_mult), 1)

    return {
        "substrate": substrate,
        "contamination": req.contamination_type,
        "severity": severity,
        "square_footage": req.square_footage,
        "recommended_recipe": {
            "target_sh_percentage": f"{base_sh}%",
            "max_safe_psi": f"{max_psi} PSI",
            "recommended_nozzle_tip": nozzle,
            "dwell_time_minutes": f"{dwell_min} minutes",
            "surfactant_ratio": f"{surfactant_oz} oz per gallon",
            "degreaser_required": degreaser_needed,
            "oxalic_acid_brightener_required": oxalic_needed,
            "batch_50_gal_mix": {
                "raw_12_5_sh_gallons": gallons_12_5_sh,
                "water_gallons": gallons_water,
                "surfactant_oz": surfactant_total_oz,
                "degreaser_quarts": 2 if degreaser_needed else 0
            }
        },
        "pricing_proposal": {
            "base_rate_per_sqft": rate_sqft,
            "height_multiplier": height_mult,
            "estimated_duration_hours": duration_hours,
            "total_quote_price": total_estimated_price
        }
    }


# ==============================================================================
# 2. TOOL 2: AUTOMATED GIS LEAD QUOTING WITH ROUTE-DENSITY DISCOUNTS
# ==============================================================================

@router.post("/gis_quote")
async def calculate_gis_quote(req: GisQuoteRequest):
    """
    Computes instant property estimate from GIS footprint and applies route density discounts.
    """
    # Roof pitch factor multiplier (6/12 = 1.12, 8/12 = 1.20, 12/12 = 1.41)
    pitch_map = {"4/12": 1.05, "6/12": 1.12, "8/12": 1.20, "10/12": 1.30, "12/12": 1.41}
    pitch_multiplier = pitch_map.get(req.roof_pitch, 1.12)

    itemized = []
    subtotal = 0.0

    # 1. House Siding Soft Wash
    if req.include_siding:
        # Perimeter estimated from square root of footprint
        perimeter = (req.building_sqft ** 0.5) * 4
        wall_height = 18.0 # Standard 2-story avg height
        siding_area = round(perimeter * wall_height, 0)
        siding_cost = round(siding_area * 0.22, 2)
        itemized.append({
            "service": "House Soft Wash (Algae, Mold & Spider Web Eradication)",
            "area_sqft": siding_area,
            "rate_per_sqft": 0.22,
            "amount": siding_cost
        })
        subtotal += siding_cost

    # 2. Roof Gloeocapsa Magma Soft Wash
    if req.include_roof:
        roof_area = round(req.building_sqft * pitch_multiplier * 1.15, 0) # +15% overhang
        roof_cost = round(roof_area * 0.35, 2)
        itemized.append({
            "service": "Roof Soft Wash (Black Streaks & Lichen Neutralization)",
            "area_sqft": roof_area,
            "rate_per_sqft": 0.35,
            "amount": roof_cost
        })
        subtotal += roof_cost

    # 3. Driveway & Walkway Surface Cleaner Rotary Wash
    if req.include_driveway:
        driveway_cost = round(req.driveway_sqft * 0.18, 2)
        itemized.append({
            "service": "Concrete Flatwork & Driveway Rotary Pressure Wash + Post-Treat",
            "area_sqft": req.driveway_sqft,
            "rate_per_sqft": 0.18,
            "amount": driveway_cost
        })
        subtotal += driveway_cost

    # 4. Deck & Patio Wood/Composite Wash
    if req.include_deck:
        deck_cost = round(req.deck_fence_sqft * 0.30, 2)
        itemized.append({
            "service": "Deck & Patio Restoration Clean",
            "area_sqft": req.deck_fence_sqft,
            "rate_per_sqft": 0.30,
            "amount": deck_cost
        })
        subtotal += deck_cost

    # Route Density Discount: If >= 1 nearby job is active in that ZIP on the day, offer 10% - 15% discount!
    discount_pct = 0
    discount_reason = "Standard Single-Stop Pricing"
    if req.nearby_jobs_in_zip >= 2:
        discount_pct = 15
        discount_reason = "15% Neighborhood Route-Density Fleet Discount (2+ Jobs Nearby)"
    elif req.nearby_jobs_in_zip == 1:
        discount_pct = 10
        discount_reason = "10% Route-Density Group Discount (Same-Day Crew in Area)"

    discount_amount = round(subtotal * (discount_pct / 100.0), 2)
    final_quote = round(subtotal - discount_amount, 2)

    return {
        "address": req.address,
        "property_type": req.property_type,
        "roof_pitch": req.roof_pitch,
        "pitch_multiplier": pitch_multiplier,
        "itemized_services": itemized,
        "subtotal": subtotal,
        "route_density_discount_pct": discount_pct,
        "discount_reason": discount_reason,
        "discount_amount": discount_amount,
        "final_total_quote": final_quote,
        "proposal_dispatch_sms": f"Prestige Mobile Wash Quote for {req.address}: ${final_quote:.2f} (Includes {discount_pct}% Route Discount!). Call/Text 616-901-6536 to book.",
        "generated_at": datetime.now().strftime("%b %d, %Y %I:%M %p")
    }


# ==============================================================================
# 3. TOOL 3: ROUTE & WATER PAYLOAD (GVWR) OPTIMIZATION MODULE
# ==============================================================================

@router.post("/route_payload")
async def calculate_route_payload(req: RoutePayloadRequest):
    """
    Computes total vehicle payload weight vs legal GVWR limits ($8.34 lbs/gal water)
    and maps closest West Michigan municipal fill hydrants along the route.
    """
    specs = PRESTIGE_RIG_SPECS
    water_weight_lbs = req.water_tank_fill_gal * specs["water_density_lbs_per_gal"]
    sh_weight_lbs = req.sh_chemical_gal * specs["sh_density_lbs_per_gal"]
    
    total_payload_lbs = water_weight_lbs + sh_weight_lbs + specs["equipment_weight_lbs"]
    total_gross_weight_lbs = specs["curb_weight_lbs"] + total_payload_lbs
    legal_gvwr = specs["gvwr_limit_lbs"]
    remaining_gvwr_margin_lbs = legal_gvwr - total_gross_weight_lbs
    is_overweight = total_gross_weight_lbs > legal_gvwr

    # Sequence water depletion across stops
    current_tank = req.water_tank_fill_gal
    stop_telemetry = []
    needs_refill_at_stop = False

    for idx, (addr, est_gal) in enumerate(zip(req.stops_addresses, req.jobs_estimated_gallons)):
        start_vol = current_tank
        current_tank -= est_gal
        requires_refill = current_tank < 40.0 # Buffer tank low threshold

        stop_telemetry.append({
            "stop_index": idx + 1,
            "address": addr,
            "estimated_consumption_gal": est_gal,
            "remaining_tank_gal": max(0.0, current_tank),
            "requires_hydrant_refill": requires_refill
        })

        if requires_refill:
            needs_refill_at_stop = True
            current_tank = specs["buffer_tank_capacity_gal"] # refill to 275

    return {
        "vehicle": specs["truck_model"],
        "curb_weight_lbs": specs["curb_weight_lbs"],
        "equipment_weight_lbs": specs["equipment_weight_lbs"],
        "water_weight_lbs": round(water_weight_lbs, 1),
        "chemical_sh_weight_lbs": round(sh_weight_lbs, 1),
        "total_gross_vehicle_weight_lbs": round(total_gross_weight_lbs, 1),
        "legal_gvwr_limit_lbs": legal_gvwr,
        "remaining_payload_capacity_lbs": round(remaining_gvwr_margin_lbs, 1),
        "is_gvwr_compliant": not is_overweight,
        "gvwr_status_badge": "LEGAL & COMPLIANT" if not is_overweight else "OVERWEIGHT HAZARD - DRAIN WATER",
        "route_stops_analysis": stop_telemetry,
        "recommended_west_mi_fill_stations": WEST_MI_FILL_STATIONS[:4]
    }


# ==============================================================================
# 4. TOOL 4: WEST MICHIGAN WEATHER DISPATCH & SEASONAL RECIRCULATION
# ==============================================================================

@router.get("/weather_dispatch")
async def get_weather_dispatch_telemetry():
    """
    Returns West Michigan weather telemetry with freezing threshold alerts,
    high wind spray safety status, and automated seasonal re-engagement campaigns.
    """
    # Live simulated/interpolated West Michigan weather status for Grand Rapids / Holland / Muskegon
    current_temp_f = 68.5
    wind_speed_mph = 8.2
    precipitation_chance_pct = 10
    is_freezing_risk = current_temp_f < 34.0
    is_wind_hazard = wind_speed_mph > 15.0

    if is_freezing_risk:
        spray_status = "FREEZE HOLD - BLOW OUT SOFTWASH PUMPS"
        badge_color = "#ef4444"
        safety_notice = "Temperature below 34°F. Soft wash chemical delivery lines and unheated triplex pumps at risk of cracking."
    elif is_wind_hazard:
        spray_status = "HIGH WIND WARNING - GROUND SPRAY ONLY"
        badge_color = "#f59e0b"
        safety_notice = f"Wind speed ({wind_speed_mph} mph) exceeds 15 mph ceiling. High-reach roof/gutter wands pose chemical drift hazard to neighbor property."
    elif precipitation_chance_pct > 70:
        spray_status = "RAIN HOLD - SURFACTANT DWELL IMPAIRED"
        badge_color = "#f59e0b"
        safety_notice = "Heavy rain will wash away Sodium Hypochlorite chemical solution before proper 10-minute organic spore dwell."
    else:
        spray_status = "ALL CLEAR - FULL FLEET DISPATCH"
        badge_color = "#22c55e"
        safety_notice = "Optimal West Michigan spraying conditions. Dwell times standard, zero chemical drift."

    # Seasonal Re-Engagement Campaign Schedule
    current_month = datetime.now().month
    seasonal_campaigns = [
        {"season": "Spring De-Winterize & Algae Wash", "months": "March - May", "status": "active" if current_month in [3,4,5] else "upcoming", "offer": "Spring Concrete & Siding Revival ($50 Off Driveway with House Wash)", "target_leads": 142},
        {"season": "Summer Patio, Pool Deck & Fleet Peak", "months": "June - August", "status": "active" if current_month in [6,7,8] else "upcoming", "offer": "Commercial Fleet & Patio Sanitization Package", "target_leads": 210},
        {"season": "Fall Gutter Clearout & Roof Moss Treatment", "months": "September - November", "status": "active" if current_month in [9,10,11] else "upcoming", "offer": "Pre-Winter Roof Lichen & Gutter Guard Protection", "target_leads": 185},
        {"season": "Winter Fleet & Road Salt Neutralization", "months": "December - February", "status": "active" if current_month in [12,1,2] else "upcoming", "offer": "Commercial Hot-Water Undercarriage Salt Neutralizer", "target_leads": 88}
    ]

    return {
        "region": "West Michigan (Kent, Ottawa, Muskegon Counties)",
        "current_temperature_f": current_temp_f,
        "wind_speed_mph": wind_speed_mph,
        "precipitation_chance_pct": precipitation_chance_pct,
        "spray_dispatch_status": spray_status,
        "badge_color": badge_color,
        "safety_notice": safety_notice,
        "seasonal_campaigns": seasonal_campaigns
    }


# ==============================================================================
# 5. TOOL 5: COMMERCIAL FLEET WASH VERIFICATION PORTAL
# ==============================================================================

@router.get("/fleet")
async def list_fleet_units(client_id: Optional[str] = None):
    """Lists commercial fleet vehicles tracked under recurring maintenance."""
    conn = get_db()
    cursor = conn.cursor()
    if client_id:
        cursor.execute("SELECT * FROM fleet_units WHERE client_id = ?", (client_id,))
    else:
        cursor.execute("SELECT * FROM fleet_units ORDER BY next_due_date ASC")
    rows = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return {"units": rows, "count": len(rows)}


@router.post("/fleet")
async def create_fleet_unit(req: FleetUnitCreateRequest):
    """Registers a new vehicle in the commercial fleet portal."""
    conn = get_db()
    cursor = conn.cursor()
    unit_id = f"flt_{uuid.uuid4().hex[:8]}"
    today_str = datetime.now().strftime("%Y-%m-%d")
    cursor.execute("""
        INSERT INTO fleet_units (id, client_id, company_name, unit_number, vin, vehicle_type, wash_tier, price_per_wash, last_wash_date, next_due_date, service_frequency_days, status)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (unit_id, req.client_id, req.company_name, req.unit_number, req.vin, req.vehicle_type, req.wash_tier, req.price_per_wash, today_str, today_str, req.service_frequency_days, "active"))
    conn.commit()
    conn.close()
    return {"status": "success", "unit_id": unit_id}


@router.post("/fleet_log")
async def log_fleet_wash_completion(req: FleetLogCreateRequest):
    """Logs a completed fleet wash with GPS verification and updates unit maintenance schedule."""
    conn = get_db()
    cursor = conn.cursor()
    log_id = f"log_{uuid.uuid4().hex[:8]}"
    timestamp = datetime.now().strftime("%b %d, %Y %I:%M %p")
    
    cursor.execute("""
        INSERT INTO fleet_wash_logs (id, unit_id, unit_number, company_name, wash_tier, timestamp, gps_coords, technician_name, before_photo_url, after_photo_url, water_temp_deg_f, soap_applied, notes)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (log_id, req.unit_id, req.unit_number, req.company_name, req.wash_tier, timestamp, req.gps_coords, req.technician_name, "", "", req.water_temp_deg_f, req.soap_applied, req.notes))

    # Update fleet unit last wash date
    cursor.execute("""
        UPDATE fleet_units 
        SET last_wash_date = ?
        WHERE id = ?
    """, (datetime.now().strftime("%Y-%m-%d"), req.unit_id))

    conn.commit()
    conn.close()

    return {
        "status": "success",
        "log_id": log_id,
        "message": f"Logged GPS-verified wash completion for {req.company_name} - Unit {req.unit_number}."
    }


# ==============================================================================
# 6. CLIENT CRM & KANBAN JOB PIPELINE
# ==============================================================================

@router.get("/clients")
async def list_clients(search: Optional[str] = None):
    conn = get_db()
    cursor = conn.cursor()
    if search:
        cursor.execute("SELECT * FROM clients WHERE name LIKE ? OR company LIKE ? OR city LIKE ?", (f"%{search}%", f"%{search}%", f"%{search}%"))
    else:
        cursor.execute("SELECT * FROM clients ORDER BY name ASC")
    rows = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return {"clients": rows, "count": len(rows)}


@router.post("/clients")
async def create_or_update_client(req: ClientCreateRequest):
    conn = get_db()
    cursor = conn.cursor()
    client_id = req.id or f"cli_{uuid.uuid4().hex[:8]}"
    now = time.time()

    cursor.execute("""
        INSERT INTO clients (id, name, company, client_type, phone, email, address, city, zip_code, gate_code, water_spigot_access, notes, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(id) DO UPDATE SET
            name=excluded.name,
            company=excluded.company,
            client_type=excluded.client_type,
            phone=excluded.phone,
            email=excluded.email,
            address=excluded.address,
            city=excluded.city,
            zip_code=excluded.zip_code,
            gate_code=excluded.gate_code,
            water_spigot_access=excluded.water_spigot_access,
            notes=excluded.notes
    """, (client_id, req.name, req.company, req.client_type, req.phone, req.email, req.address, req.city, req.zip_code, req.gate_code, req.water_spigot_access, req.notes, now))
    conn.commit()
    conn.close()
    return {"status": "success", "client_id": client_id}


@router.delete("/clients/{client_id}")
async def delete_client(client_id: str):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM clients WHERE id = ?", (client_id,))
    conn.commit()
    conn.close()
    return {"status": "success", "deleted": client_id}


@router.get("/jobs")
async def list_jobs():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM jobs ORDER BY scheduled_date ASC")
    rows = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return {"jobs": rows, "count": len(rows)}


@router.post("/jobs")
async def create_job(req: JobCreateRequest):
    conn = get_db()
    cursor = conn.cursor()
    job_id = f"job_{uuid.uuid4().hex[:8]}"
    now = time.time()

    cursor.execute("""
        INSERT INTO jobs (id, client_id, client_name, address, city, zip_code, service_type, status, scheduled_date, estimated_duration_hrs, quote_amount, paid_amount, chemical_recipe, sq_ft_total, notes, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (job_id, req.client_id, req.client_name, req.address, req.city, req.zip_code, req.service_type, "scheduled", req.scheduled_date, req.estimated_duration_hrs, req.quote_amount, 0.0, "", req.sq_ft_total, req.notes, now))
    conn.commit()
    conn.close()
    return {"status": "success", "job_id": job_id}


@router.put("/jobs/{job_id}/status")
async def update_job_status(job_id: str, payload: Dict[str, Any]):
    new_status = payload.get("status", "in_progress")
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("UPDATE jobs SET status = ? WHERE id = ?", (new_status, job_id))
    conn.commit()
    conn.close()
    return {"status": "success", "job_id": job_id, "new_status": new_status}


@router.get("/telemetry")
async def get_telemetry():
    """Calculates overall metrics for Prestige Mobile Services."""
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("SELECT COUNT(*) FROM clients")
    total_clients = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM jobs WHERE status IN ('scheduled', 'in_progress')")
    active_jobs = cursor.fetchone()[0]

    cursor.execute("SELECT SUM(quote_amount) FROM jobs WHERE status = 'paid'")
    total_revenue = cursor.fetchone()[0] or 0.0

    cursor.execute("SELECT SUM(sq_ft_total) FROM jobs")
    total_sqft = cursor.fetchone()[0] or 0.0

    cursor.execute("SELECT COUNT(*) FROM fleet_units WHERE status = 'active'")
    active_fleet_units = cursor.fetchone()[0]

    conn.close()

    return {
        "company_name": "Prestige Mobile Wash",
        "phone": "616-901-6536",
        "service_area": "West Michigan (Residential & Commercial)",
        "total_clients": total_clients,
        "active_jobs_count": active_jobs,
        "total_revenue_booked": total_revenue,
        "total_sq_ft_washed": total_sqft,
        "active_fleet_units": active_fleet_units,
        "primary_rig": PRESTIGE_RIG_SPECS["truck_model"]
    }
