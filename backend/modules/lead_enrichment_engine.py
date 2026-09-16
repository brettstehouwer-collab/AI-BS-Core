import httpx
import json
import sqlite3
import os
import uuid
import time
from datetime import datetime

DB_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "leads_store.db"
)


def _ensure_joey_leads_table():
    conn = sqlite3.connect(DB_PATH)
    try:
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA synchronous=NORMAL;")
    except Exception:
        pass
    c = conn.cursor()
    c.execute("""CREATE TABLE IF NOT EXISTS joey_enriched_leads (
                    id TEXT PRIMARY KEY,
                    name TEXT,
                    domain TEXT,
                    linkedin_url TEXT,
                    logo_url TEXT,
                    comments_json TEXT,
                    created_at REAL
                 )""")
    conn.commit()
    conn.close()


_ensure_joey_leads_table()


async def fetch_linkedin_comments(profile_url: str, rapid_api_key: str):
    """Fetch recent comments from LinkedIn profile using linkedin-data-scraper."""
    if not profile_url:
        return []

    url = "https://linkedin-data-scraper.p.rapidapi.com/comments_from_recent_activity"
    querystring = {"profile_url": profile_url, "page": "1"}
    headers = {
        "x-rapidapi-key": rapid_api_key,
        "x-rapidapi-host": "linkedin-data-scraper.p.rapidapi.com",
    }

    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                url, headers=headers, params=querystring, timeout=15.0
            )
            if response.status_code == 200:
                data = response.json()
                raw_posts = data.get("posts_with_comments", [])

                parsed_comments = []
                extracted_name = "Unknown Lead"

                for p in raw_posts:
                    highlighted = p.get("highlightedComment", {})
                    commenter = highlighted.get("commenter", {})
                    if extracted_name == "Unknown Lead" and commenter.get("title"):
                        extracted_name = commenter.get("title")

                    commentary = highlighted.get("commentary", "")
                    if commentary:
                        parsed_comments.append(
                            {
                                "comment": commentary,
                                "post_url": p.get("postLink", ""),
                                "timestamp": p.get("postedAgo", ""),
                            }
                        )
                return parsed_comments, extracted_name
            return [], "Unknown Lead"
    except Exception as e:
        print(f"Error fetching LinkedIn comments: {e}")
        return [], "Unknown Lead"


def get_clearbit_logo(domain: str):
    """Return the free Google Favicon URL for a given domain."""
    if not domain:
        return ""
    # Strip https:// or http:// if present
    clean_domain = (
        domain.replace("https://", "")
        .replace("http://", "")
        .replace("www.", "")
        .split("/")[0]
    )
    if not clean_domain:
        return ""
    return f"https://www.google.com/s2/favicons?domain={clean_domain}&sz=128"


async def enrich_and_save_lead(domain: str, linkedin_url: str, rapid_api_key: str):
    """Orchestrate the enrichment and save to database."""

    # 1. Fetch Clearbit Logo (Instant)
    logo_url = get_clearbit_logo(domain)

    # 2. Fetch LinkedIn Comments and Auto-Extract Name
    comments = []
    name = "Unknown Lead"
    if linkedin_url and rapid_api_key:
        comments, name = await fetch_linkedin_comments(linkedin_url, rapid_api_key)

    # 3. Save to database
    lead_id = f"lead_{uuid.uuid4()}"
    created_at = time.time()

    conn = sqlite3.connect(DB_PATH)
    try:
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA synchronous=NORMAL;")
    except Exception:
        pass
    c = conn.cursor()
    c.execute(
        """INSERT INTO joey_enriched_leads 
                 (id, name, domain, linkedin_url, logo_url, comments_json, created_at)
                 VALUES (?, ?, ?, ?, ?, ?, ?)""",
        (
            lead_id,
            name,
            domain,
            linkedin_url,
            logo_url,
            json.dumps(comments),
            created_at,
        ),
    )
    conn.commit()
    conn.close()

    return {
        "id": lead_id,
        "name": name,
        "domain": domain,
        "linkedin_url": linkedin_url,
        "logo_url": logo_url,
        "comments": comments,
        "created_at": created_at,
    }


def get_all_enriched_leads():
    """Retrieve all saved leads from the database."""
    conn = sqlite3.connect(DB_PATH)
    try:
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA synchronous=NORMAL;")
    except Exception:
        pass
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute("SELECT * FROM joey_enriched_leads ORDER BY created_at DESC")
    rows = c.fetchall()
    conn.close()

    leads = []
    for r in rows:
        lead = dict(r)
        # Parse the JSON string back into a list
        try:
            lead["comments"] = json.loads(lead["comments_json"])
        except:
            lead["comments"] = []
        del lead["comments_json"]
        leads.append(lead)

    return leads
