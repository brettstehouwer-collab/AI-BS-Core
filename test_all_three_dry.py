import sys, os, sqlite3, json, asyncio
sys.path.insert(0, r"C:\AI-BS\backend")
from core.sovereign_reasoning.dispatcher import stream_sovereign_response

conn = sqlite3.connect(r"C:\AI-BS\backend\stehouwer_vault.db")
cur = conn.cursor()
cur.execute("SELECT payload_json FROM conversation_revisions ORDER BY rowid DESC LIMIT 1")
payload = json.loads(cur.fetchone()[0])
messages = payload.get("messages", [])

async def run_one(label, query, hist):
    print(f"\n=== TESTING {label}: '{query}' ===")
    try:
        count = 0
        async for chunk in stream_sovereign_response(query, messages=hist):
            count += 1
            if count <= 3:
                print(f"CHUNK {count}: {repr(chunk[:50])}")
    except Exception as e:
        print(f"CAUGHT EXCEPTION: {type(e).__name__}: {e}")

async def main():
    h9 = [m["message"] for m in messages[1:9] if "message" in m][-8:]
    await run_one("Message 9", "run task", h9)

    h11 = [m["message"] for m in messages[1:11] if "message" in m][-8:]
    await run_one("Message 11", "hello world test", h11)

    h13 = [m["message"] for m in messages[1:13] if "message" in m][-8:]
    await run_one("Message 13", messages[13]["message"]["content"], h13)

asyncio.run(main())