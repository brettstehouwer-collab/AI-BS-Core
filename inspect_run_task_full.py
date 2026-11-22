import sys, os, sqlite3, json, asyncio
sys.path.insert(0, r"C:\AI-BS\backend")
from core.sovereign_reasoning.dispatcher import stream_sovereign_response

conn = sqlite3.connect(r"C:\AI-BS\backend\stehouwer_vault.db")
cur = conn.cursor()
cur.execute("SELECT payload_json FROM conversation_revisions ORDER BY rowid DESC LIMIT 1")
payload = json.loads(cur.fetchone()[0])
messages = payload.get("messages", [])

h9 = [m["message"] for m in messages[1:9] if "message" in m][-8:]

# Let's inspect all chunks produced by stream_sovereign_response for "run task" without consuming an actual model generation
async def inspect():
    async for chunk in stream_sovereign_response("run task", messages=h9):
        print("YIELD CHUNK:", repr(chunk[:60]))
        if "metadata" in chunk.lower() or "error" in chunk.lower() or "specialist" in chunk.lower():
            print("   FULL:", repr(chunk))

asyncio.run(inspect())