from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from pydantic import BaseModel
import time
import uuid
import sqlite3
import os
from typing import List, Optional

# Re-use the existing memory service for ChromaDB Client Vaults
from core.memory_service import get_memory_service, MemoryService

from modules import marketing_engine
from modules import lead_enrichment_engine
from modules.telecom_engine import telecom
from modules import reactivation_engine
from modules import virtual_staging_engine

# --- Database Initialization ---
MASTER_DB = os.path.join(os.path.dirname(__file__), "..", "aibs_master.db")
DB_PATH = MASTER_DB if os.path.exists(MASTER_DB) else os.path.join(os.path.dirname(__file__), "..", "west_michigan.db")


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
        CREATE TABLE IF NOT EXISTS properties (
            zpid TEXT PRIMARY KEY,
            address TEXT,
            price INTEGER,
            bedrooms INTEGER,
            bathrooms INTEGER,
            livingArea INTEGER,
            propertyType TEXT,
            listingStatus TEXT,
            daysOnZillow INTEGER,
            agentName TEXT,
            zillowUrl TEXT,
            scrapedAt INTEGER
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS marketing_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            property_address TEXT,
            zillow_url TEXT,
            created_at INTEGER,
            results TEXT
        )
    """)
    conn.commit()
    conn.close()


init_db()

router = APIRouter()


# --- Pydantic Models ---
class MarketingRequest(BaseModel):
    zillow_url: str
    rapid_api_key: str


class BulkMarketingRequest(BaseModel):
    location: str
    rapid_api_key: str


class BulkScrapeRequest(BaseModel):
    locations: list[str]
    rapid_api_key: str


class ListingsRequest(BaseModel):
    location: str
    rapid_api_key: str


class VaultNoteRequest(BaseModel):
    note: str
    tags: str = ""


class LeadEntry(BaseModel):
    domain: str
    linkedin_url: str


class BulkEnrichRequest(BaseModel):
    leads: list[LeadEntry]
    rapid_api_key: str


class LeadCaptureRequest(BaseModel):
    lead_name: str
    lead_phone: str
    property_interest: str


class ReactivationUploadRequest(BaseModel):
    csv_content: str


class VirtualStagingRequest(BaseModel):
    image_base64: str
    style: str
    room_type: str
    custom_prompt: str = ""


class VideoTourRequest(BaseModel):
    image_base64: str
    custom_prompt: str = ""


# --- History now persisted in west_michigan.db marketing_history table ---

# =====================================================================
# 1. Omni-Channel Marketing Endpoints
# =====================================================================


@router.get("/marketing")
async def get_marketing_history():
    """Retrieve Joey Hamilton's past generated marketing campaigns."""
    conn = get_db_connection()
    rows = conn.execute(
        "SELECT * FROM marketing_history ORDER BY created_at DESC"
    ).fetchall()
    conn.close()

    history = []
    for row in rows:
        import json

        history.append(
            {
                "property_address": row["property_address"],
                "zillow_url": row["zillow_url"],
                "created_at": row["created_at"],
                "results": json.loads(row["results"]),
            }
        )
    return {"success": True, "history": history}


@router.post("/marketing")
async def generate_marketing(req: MarketingRequest):
    """
    Generate AI Marketing Collateral from a Zillow URL using RapidAPI and Ollama.
    """
    try:
        # Call the actual marketing engine
        results = await marketing_engine.generate_marketing_copy(
            zillow_url=req.zillow_url,
            rapid_api_key=req.rapid_api_key,
            brand_style="Joey Hamilton (Five Star Real Estate)",
        )

        import json

        conn = get_db_connection()
        conn.execute(
            "INSERT INTO marketing_history (property_address, zillow_url, created_at, results) VALUES (?, ?, ?, ?)",
            (
                "Generated via Zillow API",
                req.zillow_url,
                int(time.time()),
                json.dumps(results),
            ),
        )
        conn.commit()
        conn.close()

        return {"success": True, "data": results}
    except Exception as e:
        print(f"Error generating marketing: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/marketing/bulk")
async def generate_bulk_marketing(req: BulkMarketingRequest):
    """
    Automatically find the newest properties in a location and mass-generate marketing.
    """
    import asyncio

    try:
        # 1. Discover properties using Vault
        properties = await marketing_engine.search_properties(
            location=req.location, rapid_api_key=req.rapid_api_key
        )

        # We cap at 3 to prevent extreme LLM execution times in a single request
        top_properties = properties[:3]
        bulk_results = []

        for prop in top_properties:
            zillow_url = prop.get("zillowUrl") or prop.get("zillow_url")
            if not zillow_url:
                continue

            # 2. Generate marketing copy
            results = await marketing_engine.generate_marketing_copy(
                zillow_url=zillow_url,
                rapid_api_key=req.rapid_api_key,
                brand_style="Joey Hamilton (Five Star Real Estate)",
            )

            address = prop.get("address", "Bulk Generated AI Listing")

            import json

            conn = get_db_connection()
            conn.execute(
                "INSERT INTO marketing_history (property_address, zillow_url, created_at, results) VALUES (?, ?, ?, ?)",
                (address, zillow_url, int(time.time()), json.dumps(results)),
            )
            conn.commit()
            conn.close()

            record = {
                "property_address": address,
                "zillow_url": zillow_url,
                "created_at": int(time.time()),
                "results": results,
            }
            bulk_results.append(record)

            if prop != top_properties[-1]:
                await asyncio.sleep(2)

        return {"success": True, "bulk_data": bulk_results}
    except Exception as e:
        print(f"Error in bulk marketing: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# =====================================================================
# 2. Property Discovery Endpoints
# =====================================================================


@router.post("/listings")
async def find_listings(req: ListingsRequest):
    """
    Fetch MLS listings via RapidAPI for Joey's search area.
    """
    try:
        properties = await marketing_engine.search_properties(
            location=req.location, rapid_api_key=req.rapid_api_key
        )
        return {"success": True, "properties": properties}
    except Exception as e:
        print(f"Error fetching listings: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# =====================================================================
# 3. West Michigan Database Endpoints
# =====================================================================


@router.post("/database/scrape")
async def scrape_to_database(req: BulkScrapeRequest):
    """
    Scrape multiple cities/zip codes and save all properties permanently to SQLite.
    """
    import asyncio

    try:
        conn = get_db_connection()
        total_saved = 0

        for loc in req.locations:
            loc = loc.strip()
            if not loc:
                continue

            # 1. Fetch properties for this location
            properties = await marketing_engine.search_properties(
                location=loc, rapid_api_key=req.rapid_api_key
            )

            # 2. Insert into SQLite
            for prop in properties:
                zpid = str(prop.get("zpid"))
                if not zpid:
                    continue

                conn.execute(
                    """
                    INSERT OR REPLACE INTO properties 
                    (zpid, address, price, bedrooms, bathrooms, livingArea, propertyType, listingStatus, daysOnZillow, agentName, zillowUrl, scrapedAt)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                    (
                        zpid,
                        prop.get("address", ""),
                        prop.get("price", 0),
                        prop.get("bedrooms", 0),
                        prop.get("bathrooms", 0),
                        prop.get("livingArea", 0),
                        prop.get("propertyType", ""),
                        prop.get("listingStatus", ""),
                        prop.get("daysOnZillow", 0),
                        prop.get("agentName", ""),
                        prop.get("zillowUrl", ""),
                        int(time.time()),
                    ),
                )
                total_saved += 1

            conn.commit()

            # Rate limit safety
            if loc != req.locations[-1]:
                await asyncio.sleep(2)

        conn.close()
        return {"success": True, "saved_count": total_saved}
    except Exception as e:
        print(f"Error scraping to database: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/database/properties")
async def get_database_properties():
    """Retrieve all saved properties from the West Michigan database."""
    try:
        conn = get_db_connection()
        rows = conn.execute(
            "SELECT * FROM properties ORDER BY scrapedAt DESC"
        ).fetchall()
        conn.close()

        properties = [dict(row) for row in rows]
        return {"success": True, "properties": properties}
    except Exception as e:
        print(f"Error fetching database properties: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# =====================================================================
# 4. Secure Client Vault (ChromaDB) Endpoints
# =====================================================================


@router.get("/secure-memory")
async def get_secure_notes(memory: MemoryService = Depends(get_memory_service)):
    """Fetch all notes stored in Joey's isolated ChromaDB collection."""
    if not memory.is_online:
        raise HTTPException(status_code=503, detail="ChromaDB is offline")

    try:
        # Retrieve all notes for Joey Hamilton
        results = await memory.retrieve_client_notes(
            client_id="joey_hamilton", limit=100
        )

        # Format the response to match the frontend expectations
        notes_list = []
        if results and results.get("documents"):
            for i, doc in enumerate(results["documents"]):
                meta = results["metadatas"][i] if results.get("metadatas") else {}
                notes_list.append({"note": doc, "metadata": meta})

        # Sort by timestamp descending
        notes_list.sort(key=lambda x: x["metadata"].get("timestamp", 0), reverse=True)

        return {"success": True, "notes": notes_list}
    except Exception as e:
        print(f"Error fetching Joey's secure memory: {e}")
        return {"success": False, "detail": str(e)}


@router.post("/secure-memory")
async def save_secure_note(
    req: VaultNoteRequest, memory: MemoryService = Depends(get_memory_service)
):
    """Encrypt and save a note to Joey's isolated ChromaDB vector vault."""
    if not memory.is_online:
        raise HTTPException(status_code=503, detail="ChromaDB is offline")

    try:
        doc_id = f"joey_note_{uuid.uuid4()}"
        metadata = {
            "tags": req.tags,
            "timestamp": time.time(),
            "source": "manual_entry",
        }

        success = await memory.add_client_note(
            client_id="joey_hamilton",
            document=req.note,
            metadata=metadata,
            doc_id=doc_id,
        )

        if success:
            return {"success": True}
        return {"success": False, "detail": "Failed to persist to ChromaDB"}
    except Exception as e:
        print(f"Error saving to Joey's secure memory: {e}")
        return {"success": False, "detail": str(e)}


# =====================================================================
# 4. Lead Enrichment Endpoints
# =====================================================================


@router.get("/enrich")
async def get_enriched_leads():
    """Fetch all permanently saved enriched leads from SQLite."""
    try:
        leads = lead_enrichment_engine.get_all_enriched_leads()
        return {"success": True, "leads": leads}
    except Exception as e:
        print(f"Error fetching enriched leads: {e}")
        return {"success": False, "detail": str(e)}


@router.post("/enrich")
async def enrich_new_lead(req: BulkEnrichRequest):
    """Enrich a massive list of leads with LinkedIn activity and Google Favicon, then save permanently."""
    import asyncio

    try:
        enriched_leads = []
        for lead_entry in req.leads:
            # Skip empty entries
            if not lead_entry.domain.strip() and not lead_entry.linkedin_url.strip():
                continue

            enriched = await lead_enrichment_engine.enrich_and_save_lead(
                domain=lead_entry.domain.strip(),
                linkedin_url=lead_entry.linkedin_url.strip(),
                rapid_api_key=req.rapid_api_key,
            )
            enriched_leads.append(enriched)

            # 2-second rate limit safety delay (except for the last one)
            if lead_entry != req.leads[-1]:
                await asyncio.sleep(2)

        return {"success": True, "leads": enriched_leads}
    except Exception as e:
        print(f"Error enriching lead: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# =====================================================================
# 5. Telecom Endpoints (Call Whisper)
# =====================================================================


@router.post("/telecom/lead-capture")
async def capture_lead_and_whisper(req: LeadCaptureRequest):
    """
    Capture a lead from a landing page and instantly trigger the Call Whisper to Joe.
    """
    try:
        # In a real app, you would save this lead to the database here.
        # For now, we trigger the call whisper directly to Joe's mock phone number.
        joe_phone = "+1234567890"  # Joe's cell phone

        result = telecom.trigger_call_whisper(
            agent_phone=joe_phone,
            lead_name=req.lead_name,
            lead_phone=req.lead_phone,
            property_interest=req.property_interest,
        )
        return result
    except Exception as e:
        print(f"Error triggering call whisper: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# =====================================================================
# 6. Past Client Reactivation Endpoints
# =====================================================================


@router.post("/reactivation/upload")
async def upload_reactivation_csv(req: ReactivationUploadRequest):
    """
    Accepts a CSV string of past clients, parses it, and generates personalized SMS campaigns.
    """
    try:
        results = await reactivation_engine.parse_and_generate_campaign(req.csv_content)
        return {"success": True, "campaigns": results}
    except Exception as e:
        print(f"Error in reactivation upload: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# =====================================================================
# 7. AI Virtual Staging Endpoints
# =====================================================================


@router.post("/virtual-staging/generate")
async def generate_virtual_staging(req: VirtualStagingRequest):
    """
    Accepts an empty room image and generates a beautifully staged version.
    """
    try:
        result = await virtual_staging_engine.generate_virtual_staging(
            req.image_base64, req.style, req.room_type, req.custom_prompt
        )
        return result
    except Exception as e:
        print(f"Error in virtual staging generation: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/virtual-staging/video-tour")
async def generate_video_tour_endpoint(req: VideoTourRequest):
    """
    Accepts a room image and generates a photorealistic camera pan video tour.
    """
    try:
        result = await virtual_staging_engine.generate_video_tour(
            req.image_base64, req.custom_prompt
        )
        return result
    except Exception as e:
        print(f"Error in video tour generation: {e}")
        raise HTTPException(status_code=500, detail=str(e))
