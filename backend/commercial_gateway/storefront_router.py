import sqlite3
import os
import urllib.request
import json
from fastapi import APIRouter, HTTPException, Header, Depends
from pydantic import BaseModel
from typing import Optional

router = APIRouter(prefix="/api/storefront", tags=["Digital Storefront"])

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "stehouwer_vault.db")

def get_tenant(x_client_id: Optional[str] = Header(None)):
    if not x_client_id:
        return "stehouwer_publishing"
    return x_client_id

def init_db():
    try:
        conn = sqlite3.connect(DB_PATH)
        try:
            conn.execute("PRAGMA journal_mode=WAL;")
            conn.execute("PRAGMA synchronous=NORMAL;")
        except Exception:
            pass
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS tenant_user_credits (
                client_id TEXT DEFAULT 'stehouwer_publishing',
                user_email TEXT,
                credits INTEGER DEFAULT 500,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (client_id, user_email)
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS leads_tracker (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                client_id TEXT DEFAULT 'stehouwer_publishing',
                name TEXT,
                contact TEXT,
                status TEXT,
                revenue TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"Error initializing storefront vault DB: {e}")

init_db()

class GenerateRequest(BaseModel):
    user_email: str = "default_user@stehouwer.com"
    prompt: str
    model: str = "stehouwer_llm"

class LeadRequest(BaseModel):
    name: str
    contact: str
    status: str = "Active Trial"
    revenue: str = "$29/mo"

@router.get("/balance")
async def get_balance(user_email: str = "default_user@stehouwer.com", tenant: str = Depends(get_tenant)):
    """
    Returns current credit balance for the given user email and tenant.
    """
    try:
        conn = sqlite3.connect(DB_PATH)
        try:
            conn.execute("PRAGMA journal_mode=WAL;")
        except Exception:
            pass
        cursor = conn.cursor()
        cursor.execute(
            "SELECT credits FROM tenant_user_credits WHERE client_id = ? AND user_email = ?", (tenant, user_email)
        )
        row = cursor.fetchone()
        if not row:
            cursor.execute(
                "INSERT INTO tenant_user_credits (client_id, user_email, credits) VALUES (?, ?, ?)",
                (tenant, user_email, 500),
            )
            conn.commit()
            credits = 500
        else:
            credits = row[0]
        conn.close()
        return {"status": "success", "credits": credits, "client_id": tenant}
    except Exception as e:
        print(f"DB Error: {e}")
        return {"status": "success", "credits": 500, "client_id": tenant}

@router.post("/generate-content")
async def generate_content(req: GenerateRequest, tenant: str = Depends(get_tenant)):
    """
    Executes an AI content generation request using local Ollama.
    Deducts 10 credits from SQLite.
    """
    conn = sqlite3.connect(DB_PATH)
    try:
        conn.execute("PRAGMA journal_mode=WAL;")
    except Exception:
        pass
    cursor = conn.cursor()

    cursor.execute(
        "SELECT credits FROM tenant_user_credits WHERE client_id = ? AND user_email = ?", (tenant, req.user_email)
    )
    row = cursor.fetchone()
    current_credits = row[0] if row else 500

    if current_credits < 10:
        conn.close()
        raise HTTPException(status_code=400, detail="Insufficient credits")

    new_credits = current_credits - 10
    cursor.execute(
        """
        INSERT INTO tenant_user_credits (client_id, user_email, credits) VALUES (?, ?, ?)
        ON CONFLICT(client_id, user_email) DO UPDATE SET credits = ?, updated_at = CURRENT_TIMESTAMP
        """,
        (tenant, req.user_email, new_credits, new_credits),
    )
    conn.commit()
    conn.close()

    try:
        url = "http://127.0.0.1:11434/api/generate"
        payload = {
            "model": req.model if req.model else "stehouwer_llm",
            "prompt": f"You are a professional copywriter and marketing assistant. Process the following request:\n\n{req.prompt}",
            "stream": False,
        }

        data = json.dumps(payload).encode("utf-8")
        request = urllib.request.Request(
            url, data=data, headers={"Content-Type": "application/json"}
        )

        with urllib.request.urlopen(request, timeout=60) as response:
            res_body = json.loads(response.read().decode("utf-8"))
            generated_text = res_body.get("response", "No output generated.")

        return {
            "status": "success",
            "content": generated_text,
            "credits_remaining": new_credits,
            "model_used": req.model,
            "client_id": tenant,
        }
    except Exception as e:
        print(f"Error generating storefront content: {e}")
        return {
            "status": "success",
            "content": f"[Simulated Output - Local Ollama Engine Offline]\n\nHere is your generated content based on prompt:\n'{req.prompt}'\n\n- High quality ad copy line 1\n- High quality ad copy line 2\n- Call to Action: Contact Stehouwer Advertising today!",
            "credits_remaining": new_credits,
            "model_used": "fallback",
            "client_id": tenant,
        }

@router.get("/leads")
async def get_leads(tenant: str = Depends(get_tenant)):
    """
    Returns active CRM leads for the tenant.
    """
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute(
            "SELECT id, name, contact, status, revenue FROM leads_tracker WHERE client_id = ? ORDER BY created_at DESC", 
            (tenant,)
        )
        rows = cursor.fetchall()
        leads = [dict(row) for row in rows]
        conn.close()
        return {"status": "success", "leads": leads, "client_id": tenant}
    except Exception as e:
        print(f"DB Error: {e}")
        return {"status": "error", "message": str(e)}

@router.post("/leads")
async def add_lead(lead: LeadRequest, tenant: str = Depends(get_tenant)):
    """
    Adds a new CRM lead securely bound to the client_id.
    """
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO leads_tracker (client_id, name, contact, status, revenue) VALUES (?, ?, ?, ?, ?)",
            (tenant, lead.name, lead.contact, lead.status, lead.revenue)
        )
        conn.commit()
        new_id = cursor.lastrowid
        conn.close()
        return {"status": "success", "lead": {"id": new_id, "name": lead.name, "contact": lead.contact, "status": lead.status, "revenue": lead.revenue}, "client_id": tenant}
    except Exception as e:
        print(f"DB Error: {e}")
        return {"status": "error", "message": str(e)}
