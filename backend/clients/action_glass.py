from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import httpx
import sqlite3
import os
import time

router = APIRouter()

MASTER_DB = os.path.join(os.path.dirname(__file__), "..", "aibs_master.db")
DB_PATH = MASTER_DB if os.path.exists(MASTER_DB) else os.path.join(os.path.dirname(__file__), "..", "clients.db")


def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    try:
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA synchronous=NORMAL;")
    except Exception:
        pass
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db_connection()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS ag_quotes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            vehicle TEXT,
            glass_type TEXT,
            estimated_cost REAL,
            created_at INTEGER
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS ag_competitors (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            price_index TEXT,
            wait_time TEXT
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS ag_outreach (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            target_audience TEXT,
            offer TEXT,
            campaign_text TEXT,
            created_at INTEGER
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS ag_fleet (
            id TEXT PRIMARY KEY,
            location TEXT,
            status TEXT,
            driver TEXT
        )
    """)

    # Seed competitors if empty
    if conn.execute("SELECT COUNT(*) FROM ag_competitors").fetchone()[0] == 0:
        conn.executemany(
            "INSERT INTO ag_competitors (name, price_index, wait_time) VALUES (?, ?, ?)",
            [
                ("Safelite AutoGlass (Grandville)", "$$$", "3-5 Days"),
                ("West Michigan Glass Coatings", "$$", "1-2 Days"),
                ("Auto Glass Fitters", "$$", "2 Days"),
            ],
        )

    # Seed fleet if empty
    if conn.execute("SELECT COUNT(*) FROM ag_fleet").fetchone()[0] == 0:
        conn.executemany(
            "INSERT INTO ag_fleet (id, location, status, driver) VALUES (?, ?, ?, ?)",
            [
                ("Van-01", "Hudsonville", "On Job", "Mark S."),
                ("Van-02", "Grand Rapids", "In Transit", "Dave R."),
                ("Van-03", "Jenison HQ", "Available", "Sarah J."),
            ],
        )

    conn.commit()
    conn.close()


init_db()


# --- Models ---
class QuoterRequest(BaseModel):
    make: str
    model: str
    year: int
    glass_type: str


class OutreachRequest(BaseModel):
    target_audience: str
    offer: str


class SeoRequest(BaseModel):
    service: str
    location: str


# --- Endpoints ---


@router.post("/quoter")
async def action_glass_quoter(req: QuoterRequest):
    """
    Generates a quote and saves it to the database.
    """
    base_price = 250
    if req.glass_type.lower() == "windshield":
        base_price += 150
    elif req.glass_type.lower() == "sunroof":
        base_price += 300

    # Luxury tax
    if req.make.lower() in ["bmw", "mercedes", "audi", "porsche", "tesla"]:
        base_price *= 1.5

    vehicle_str = f"{req.year} {req.make} {req.model}"
    cost = round(base_price, 2)

    conn = get_db_connection()
    conn.execute(
        "INSERT INTO ag_quotes (vehicle, glass_type, estimated_cost, created_at) VALUES (?, ?, ?, ?)",
        (vehicle_str, req.glass_type, cost, int(time.time())),
    )
    conn.commit()
    conn.close()

    return {
        "success": True,
        "quote": {
            "vehicle": vehicle_str,
            "glass_type": req.glass_type,
            "estimated_cost": cost,
            "availability": "In Stock - Next Day Installation Available",
            "warranty": "Lifetime Warranty Included",
        },
    }


@router.get("/competitor-radar")
async def competitor_radar():
    """
    Retrieves competitor pricing from the database.
    """
    conn = get_db_connection()
    rows = conn.execute(
        "SELECT name, price_index, wait_time FROM ag_competitors"
    ).fetchall()
    conn.close()

    return {
        "success": True,
        "competitors": [dict(r) for r in rows],
        "action_glass_advantage": "Cheapest local option, next-day mobile service.",
    }


@router.post("/driver-outreach")
async def driver_outreach(req: OutreachRequest):
    """
    Generates a personalized SMS/Email outreach campaign and saves it to DB.
    """
    campaign_text = f"Hey {req.target_audience}! Did you catch a rock on 196? Action Glass in Jenison is offering {req.offer}. We come to you! Reply YES to book."

    conn = get_db_connection()
    conn.execute(
        "INSERT INTO ag_outreach (target_audience, offer, campaign_text, created_at) VALUES (?, ?, ?, ?)",
        (req.target_audience, req.offer, campaign_text, int(time.time())),
    )
    conn.commit()
    conn.close()

    return {
        "success": True,
        "campaign": campaign_text,
        "estimated_conversion_rate": "12.4%",
    }


@router.get("/fleet-tracker")
async def fleet_tracker():
    """
    Tracks branded fleet vehicles from the database.
    """
    conn = get_db_connection()
    rows = conn.execute("SELECT id, location, status, driver FROM ag_fleet").fetchall()
    conn.close()

    return {"success": True, "fleets": [dict(r) for r in rows]}


@router.post("/seo-optimizer")
async def seo_optimizer(req: SeoRequest):
    """
    Calls the local Genkit Node.js Microservice to generate highly optimized Google Ad copy and SEO tags.
    """
    try:
        async with httpx.AsyncClient() as client:
            # Call the Genkit server we built
            response = await client.post(
                "http://localhost:3001/api/actionGlassSeoFlow",
                json={"service": req.service, "location": req.location},
                timeout=30.0,
            )
            response.raise_for_status()
            genkit_data = response.json()

            return {"success": True, "ai_optimization": genkit_data.get("result", {})}
    except Exception as e:
        print(f"Error calling Genkit server: {e}")
        raise HTTPException(status_code=500, detail=f"AI Generation failed: {str(e)}")
