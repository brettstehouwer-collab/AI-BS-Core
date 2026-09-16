import os
import sqlite3
import time
import json
from typing import List, Optional
from pydantic import BaseModel
from fastapi import APIRouter
from dotenv import load_dotenv

router = APIRouter(prefix="/api/vault", tags=["Secure Data Vault"])

MASTER_DB = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "aibs_master.db"
)
DB_PATH = MASTER_DB if os.path.exists(MASTER_DB) else os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "stehouwer_vault.db"
)


def get_db():
    conn = sqlite3.connect(DB_PATH, timeout=20.0)
    try:
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA synchronous=NORMAL;")
    except Exception:
        pass
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.row_factory = sqlite3.Row
    return conn


def init_vault_db():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS vault_keys (
            id TEXT PRIMARY KEY,
            clientName TEXT,
            apiName TEXT,
            apiKey TEXT,
            baseUrl TEXT,
            category TEXT,
            created_at REAL
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS vault_data (
            id TEXT PRIMARY KEY,
            timestamp REAL,
            source TEXT,
            data TEXT
        )
    """)
    conn.commit()

    # Load from .env and inject standard keys if missing
    env_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env"
    )
    load_dotenv(dotenv_path=env_path)

    system_keys = [
        (
            "system-paypal",
            "System Default",
            "PayPal Client ID",
            os.getenv("PAYPAL_CLIENT_ID", ""),
            "Finance",
        ),
        (
            "system-stripe",
            "System Default",
            "Stripe API Key",
            os.getenv("STRIPE_API_KEY", ""),
            "Finance",
        ),
        (
            "system-rapidapi",
            "System Default",
            "RapidAPI Master Key",
            "715331f921msh08fd118bc6cfcdbp1fd3bfjsn995142bec639",
            "All-Purpose",
        ),
        (
            "system-gemini",
            "System Default",
            "Gemini API Key",
            "AQ.Ab8RN6Lpq_Z1D7Dd68Nv2xPgdz8iF7RqaTDMg57IQAYnXwm07Q",
            "AI Models",
        ),
        (
            "system-crypto",
            "System Default",
            "Crypto.com API Key",
            "qUS4PaX3zNcGycmVJhoeM4",
            "Finance",
        ),
        (
            "system-discord",
            "System Default",
            "Discord Bot Token",
            "MTUyMzk2MzE4MjMzMzQyNzgzMw.G8_30A.GZ5G_7X9ppFbhrIRQbOawIYrlvNaHwkfqno2rg",
            "Social/Bots",
        ),
    ]

    now = time.time()
    for key_id, client, name, val, cat in system_keys:
        if val:  # Only insert if value exists
            cursor.execute(
                "INSERT OR IGNORE INTO vault_keys (id, clientName, apiName, apiKey, baseUrl, category, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (key_id, client, name, val, "", cat, now),
            )

    conn.commit()
    conn.close()


init_vault_db()


class ApiKeySchema(BaseModel):
    id: str
    clientName: str
    apiName: str
    apiKey: str
    baseUrl: str
    category: str


class VaultDataSchema(BaseModel):
    id: str
    timestamp: float
    source: str
    data: dict


@router.get("/keys")
def get_keys():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM vault_keys ORDER BY created_at DESC")
    rows = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return {"status": "success", "keys": rows}


@router.post("/keys")
def save_key(payload: ApiKeySchema):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT OR REPLACE INTO vault_keys (id, clientName, apiName, apiKey, baseUrl, category, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """,
        (
            payload.id,
            payload.clientName,
            payload.apiName,
            payload.apiKey,
            payload.baseUrl,
            payload.category,
            time.time(),
        ),
    )
    conn.commit()
    conn.close()
    return {"status": "success"}


@router.delete("/keys/{key_id}")
def delete_key(key_id: str):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM vault_keys WHERE id = ?", (key_id,))
    conn.commit()
    conn.close()
    return {"status": "success"}


@router.get("/data")
def get_data():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM vault_data ORDER BY timestamp DESC")
    rows = []
    for r in cursor.fetchall():
        item = dict(r)
        item["data"] = json.loads(item["data"])
        rows.append(item)
    conn.close()
    return {"status": "success", "vault": rows}


@router.post("/data")
def save_data(payload: VaultDataSchema):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT OR REPLACE INTO vault_data (id, timestamp, source, data)
        VALUES (?, ?, ?, ?)
    """,
        (payload.id, payload.timestamp, payload.source, json.dumps(payload.data)),
    )
    conn.commit()
    conn.close()
    return {"status": "success"}


@router.delete("/data/{data_id}")
def delete_data(data_id: str):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM vault_data WHERE id = ?", (data_id,))
    conn.commit()
    conn.close()
    return {"status": "success"}


@router.get("/saved_data")
def get_saved_data():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM vault_data ORDER BY timestamp DESC")
    rows = []
    for r in cursor.fetchall():
        item = dict(r)
        try:
            item["data"] = json.loads(item["data"])
        except Exception:
            pass
        rows.append(item)
    conn.close()
    return {"status": "success", "results": rows, "count": len(rows)}

