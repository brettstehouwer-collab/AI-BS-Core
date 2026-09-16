import sqlite3
import json
from fastapi import APIRouter

router = APIRouter(prefix="/feeds", tags=["Live Data Feeds"])

DB_PATH = "C:\\AI-BS\\database\\message_broker.db"

@router.get("/latest/{topic}")
def get_latest_feed(topic: str, limit: int = 5):
    try:
        conn = sqlite3.connect(DB_PATH)
        try:
            conn.execute("PRAGMA journal_mode=WAL;")
            conn.execute("PRAGMA synchronous=NORMAL;")
        except Exception:
            pass
        c = conn.cursor()
        # Get the most recent payloads for the given topic
        c.execute("SELECT payload, timestamp FROM broker_messages WHERE topic = ? ORDER BY timestamp DESC LIMIT ?", (topic, limit))
        rows = c.fetchall()
        conn.close()
        
        results = []
        for row in rows:
            try:
                payload = json.loads(row[0])
            except:
                payload = row[0]
            results.append({
                "payload": payload,
                "timestamp": row[1]
            })
            
        return {"status": "success", "topic": topic, "data": results}
    except Exception as e:
        return {"status": "error", "message": str(e)}
