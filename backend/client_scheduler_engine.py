import os
import json
import sqlite3
import time
import uuid
import logging
from datetime import datetime, timedelta

logger = logging.getLogger("ClientSchedulerEngine")
logger.setLevel(logging.INFO)

DB_PATH = os.path.join(os.path.dirname(__file__), "state.db")


def init_scheduler_db():
    """Initializes SQLite tables for Client Profiles, Email Ingestion, and Scheduled Weekly Posts."""
    conn = sqlite3.connect(DB_PATH, timeout=15.0)
    try:
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA synchronous=NORMAL;")
    except Exception:
        pass
    cursor = conn.cursor()

    # 1. Clients Table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS client_profiles (
                    client_id TEXT DEFAULT 'stehouwer_publishing',
            id TEXT PRIMARY KEY,
            name TEXT UNIQUE,
            industry TEXT,
            website TEXT,
            target_audience TEXT,
            brand_voice TEXT,
            preferred_channels TEXT,
            contact_email TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # 2. Ingested Client Requests & Emails Table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS client_email_requests (
                    client_id TEXT DEFAULT 'stehouwer_publishing',
            id TEXT PRIMARY KEY,
            client_name TEXT,
            sender_email TEXT,
            subject TEXT,
            raw_request_text TEXT,
            target_week TEXT,
            status TEXT DEFAULT 'UNPROCESSED',
            received_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # 3. Scheduled Social & Promotional Posts Queue
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS scheduled_posts_queue (
                    client_id TEXT DEFAULT 'stehouwer_publishing',
            id TEXT PRIMARY KEY,
            client_name TEXT,
            platform TEXT,
            scheduled_day TEXT,
            scheduled_time TEXT,
            post_topic TEXT,
            post_copy TEXT,
            hashtags TEXT,
            media_type TEXT,
            media_url TEXT,
            status TEXT DEFAULT 'QUEUED',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    conn.commit()
    conn.close()

    # Seed Default Clients if empty (Stehouwer Publishing, Grand Rapids Creative Studio, AI-BS Sovereign Cloud)
    seed_default_clients()


def seed_default_clients():
    conn = sqlite3.connect(DB_PATH, timeout=15.0)
    try:
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA synchronous=NORMAL;")
    except Exception:
        pass
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM client_profiles")
    count = cursor.fetchone()[0]
    if count == 0:
        defaults = [
            (
                "client_sp",
                "Stehouwer Publishing",
                "Book Publishing & Literary Media",
                "https://stehouwer-publishing.com",
                "Authors, Readers & Book Buyers",
                "Professional, Inspiring, Authoritative",
                "Twitter, LinkedIn, Facebook, Email Newsletter",
                "contact@stehouwer-publishing.com",
            ),
            (
                "client_grcs",
                "Grand Rapids Creative Studio",
                "Media & Audio Production",
                "https://grcreativestudio.com",
                "Local Businesses & Content Creators",
                "Energetic, Modern, Tech-Savvy",
                "Twitter, LinkedIn, Instagram",
                "info@grcreativestudio.com",
            ),
            (
                "client_aibs",
                "AI-BS Sovereign Cloud",
                "Generative AI & GPU Computing",
                "https://ai-bs-dashboard.web.app/playground",
                "Developers, Engineers & Tech Creators",
                "Bold, High-Performance, Innovative",
                "Twitter, LinkedIn, Discord, Telegram",
                "support@stehouwer-publishing.com",
            ),
        ]
        cursor.executemany(
            """
            INSERT OR IGNORE INTO client_profiles (id, name, industry, website, target_audience, brand_voice, preferred_channels, contact_email)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
            defaults,
        )
        conn.commit()
    conn.close()


init_scheduler_db()


def get_all_clients():
    """Returns list of active client profiles."""
    conn = sqlite3.connect(DB_PATH, timeout=15.0)
    try:
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA synchronous=NORMAL;")
    except Exception:
        pass
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM client_profiles ORDER BY name ASC")
    rows = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return rows


def save_client_profile(
    name,
    industry,
    website,
    target_audience,
    brand_voice,
    preferred_channels,
    contact_email,
):
    """Creates or updates a client profile."""
    client_id = f"client_{uuid.uuid4().hex[:8]}"
    conn = sqlite3.connect(DB_PATH, timeout=15.0)
    try:
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA synchronous=NORMAL;")
    except Exception:
        pass
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO client_profiles (id, name, industry, website, target_audience, brand_voice, preferred_channels, contact_email)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(name) DO UPDATE SET
            industry=excluded.industry,
            website=excluded.website,
            target_audience=excluded.target_audience,
            brand_voice=excluded.brand_voice,
            preferred_channels=excluded.preferred_channels,
            contact_email=excluded.contact_email
    """,
        (
            client_id,
            name,
            industry,
            website,
            target_audience,
            brand_voice,
            preferred_channels,
            contact_email,
        ),
    )
    conn.commit()
    conn.close()
    return get_all_clients()


def ingest_client_email_request(
    client_name, sender_email, subject, raw_request_text, target_week=None
):
    """Simulates or records an incoming client email post request."""
    request_id = f"email_{uuid.uuid4().hex[:8]}"
    if not target_week:
        target_week = datetime.now().strftime("Week of %B %d, %Y")

    conn = sqlite3.connect(DB_PATH, timeout=15.0)
    try:
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA synchronous=NORMAL;")
    except Exception:
        pass
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO client_email_requests (id, client_name, sender_email, subject, raw_request_text, target_week, status)
        VALUES (?, ?, ?, ?, ?, ?, 'QUEUED')
    """,
        (request_id, client_name, sender_email, subject, raw_request_text, target_week),
    )
    conn.commit()
    conn.close()
    return {
        "id": request_id,
        "status": "QUEUED",
        "message": f"Client request '{subject}' logged successfully.",
    }


def generate_weekly_content_schedule(client_name, custom_instructions=None):
    """
    Generates 7 daily tailored social media posts for the specified client.
    Converts client profile details & raw email notes into daily posts.
    """
    conn = sqlite3.connect(DB_PATH, timeout=15.0)
    try:
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA synchronous=NORMAL;")
    except Exception:
        pass
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM client_profiles WHERE name = ?", (client_name,))
    client = cursor.fetchone()
    conn.close()

    if not client:
        # Fallback default client
        client = {
            "name": client_name,
            "industry": "Publishing & Media",
            "website": "https://stehouwer-publishing.com",
            "target_audience": "Local Businesses & Readers",
            "brand_voice": "Professional, Inspiring",
            "preferred_channels": "Twitter, LinkedIn, Facebook, Instagram",
        }
    else:
        client = dict(client)

    days = [
        "Monday",
        "Tuesday",
        "Wednesday",
        "Thursday",
        "Friday",
        "Saturday",
        "Sunday",
    ]
    post_types = [
        (
            "Product / Service Spotlight",
            "Highlighting core offerings and competitive edge.",
        ),
        (
            "Customer Testimonial / Story",
            "Sharing success stories, author highlights, and feedback.",
        ),
        (
            "Educational / Industry Insight",
            "Providing actionable advice and industry expertise.",
        ),
        (
            "Behind-The-Scenes / Process",
            "Showcasing studio workflow, RTX 4090 rendering, or writing process.",
        ),
        (
            "Promotional Offer / Call-To-Action",
            "Special discount, free consultation, or manuscript submission CTA.",
        ),
        (
            "Community & Weekend Highlight",
            "Local West Michigan community news and weekend thoughts.",
        ),
        (
            "Weekly Recap & Upcoming Preview",
            "Summarizing key milestones and previewing next week's releases.",
        ),
    ]

    generated_schedule = []
    conn = sqlite3.connect(DB_PATH, timeout=15.0)
    try:
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA synchronous=NORMAL;")
    except Exception:
        pass
    cursor = conn.cursor()

    for idx, day in enumerate(days):
        topic_title, topic_desc = post_types[idx]
        post_id = f"post_{uuid.uuid4().hex[:8]}"

        if "stehouwer publishing" in client_name.lower():
            copy = (
                f"📚 Stehouwer Publishing {day} Highlight: {topic_title}!\n\n"
                f"Whether you are an aspiring author preparing a manuscript or a reader looking for your next captivating book, "
                f"Stehouwer Publishing brings world-class formatting, cover design, and distribution.\n\n"
                f"👉 Discover our catalog & submission portal: {client['website']}\n\n"
                f"#StehouwerPublishing #Authors #BookPublishing #IndieAuthors #WestMichigan #Books"
            )
            hashtags = "#StehouwerPublishing #Authors #BookPublishing #IndieAuthors"
        else:
            copy = (
                f"🚀 {client['name']} — {day} Showcase: {topic_title}\n\n"
                f"{topic_desc} We help {client['target_audience']} achieve outstanding results with tailored {client['industry']} solutions.\n\n"
                f"🔗 Visit our portal: {client['website']}\n\n"
                f"#{client['name'].replace(' ', '')} #{client['industry'].split()[0]} #Innovation #Growth"
            )
            hashtags = f"#{client['name'].replace(' ', '')} #Growth"

        channels = [
            c.strip()
            for c in client.get("preferred_channels", "Twitter, LinkedIn").split(",")
        ]
        platform = channels[idx % len(channels)]

        cursor.execute(
            """
            INSERT INTO scheduled_posts_queue (id, client_name, platform, scheduled_day, scheduled_time, post_topic, post_copy, hashtags, status)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'SCHEDULED')
        """,
            (
                post_id,
                client["name"],
                platform,
                day,
                "09:00 AM",
                topic_title,
                copy,
                hashtags,
            ),
        )

        generated_schedule.append(
            {
                "id": post_id,
                "client_name": client["name"],
                "platform": platform,
                "scheduled_day": day,
                "scheduled_time": "09:00 AM",
                "post_topic": topic_title,
                "post_copy": copy,
                "hashtags": hashtags,
                "status": "SCHEDULED",
            }
        )

    conn.commit()
    conn.close()
    return generated_schedule


def get_scheduled_posts_queue(client_name=None):
    """Retrieves all scheduled posts in queue."""
    conn = sqlite3.connect(DB_PATH, timeout=15.0)
    try:
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA synchronous=NORMAL;")
    except Exception:
        pass
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    if client_name:
        cursor.execute(
            "SELECT * FROM scheduled_posts_queue WHERE client_name = ? ORDER BY created_at DESC",
            (client_name,),
        )
    else:
        cursor.execute(
            "SELECT * FROM scheduled_posts_queue ORDER BY created_at DESC LIMIT 50"
        )
    rows = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return rows


if __name__ == "__main__":
    clients = get_all_clients()
    print(f"Loaded {len(clients)} client profiles.")
    schedule = generate_weekly_content_schedule("Stehouwer Publishing")
    print(f"Generated 7 weekly posts for Stehouwer Publishing.")
