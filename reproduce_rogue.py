import sys, os, sqlite3, json, asyncio
sys.path.insert(0, r"C:\AI-BS\backend")
from core.sovereign_reasoning.dispatcher import stream_sovereign_response

conn = sqlite3.connect(r"C:\AI-BS\backend\stehouwer_vault.db")
cur = conn.cursor()
cur.execute("SELECT payload_json FROM conversation_revisions ORDER BY rowid DESC LIMIT 1")
payload = json.loads(cur.fetchone()[0])
messages = payload.get("messages", [])

# Let's test with messages[1:13] (which was the history when Message 13 "OPERATION ROGUE INTELLIGENCE" arrived)
recent13 = [m["message"] for m in messages[1:13] if "message" in m][-8:]

msg13_content = messages[13]["message"]["content"]
print("Prompt len:", len(msg13_content))

async def test():
    try:
        async for chunk in stream_sovereign_response(msg13_content, messages=recent13):
            print("CHUNK:", repr(chunk[:40]))
    except Exception as e:
        print("EXCEPTION TYPE:", type(e).__name__)
        print("EXCEPTION DETAILS:", repr(e))
        if hasattr(e, "receipt"):
            print("RECEIPT:", json.dumps(e.receipt, indent=2))

asyncio.run(test())