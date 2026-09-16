import asyncio
import json
import sqlite3
import time
from aiohttp import web
import datetime

# --- Configuration ---
BROKER_PORT = 8085
DB_PATH = "C:\\AI-BS\\database\\message_broker.db"
BATCH_SIZE = 100
FLUSH_INTERVAL = 5.0 # seconds

# The in-memory Queue
message_queue = asyncio.Queue()

# --- Database Setup ---
def init_db():
    conn = sqlite3.connect(DB_PATH)
    try:
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA synchronous=NORMAL;")
    except Exception:
        pass
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS broker_messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    topic TEXT NOT NULL,
                    payload TEXT NOT NULL,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
                 )''')
    c.execute('''CREATE TABLE IF NOT EXISTS broker_stats (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    messages_processed INTEGER,
                    flush_duration_ms REAL,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
                 )''')
    conn.commit()
    conn.close()

# --- Batch Processing Task ---
async def batch_processor():
    while True:
        batch = []
        try:
            # Wait for at least one message, or flush interval
            msg = await asyncio.wait_for(message_queue.get(), timeout=FLUSH_INTERVAL)
            batch.append(msg)
            
            # Drain the queue up to BATCH_SIZE
            while not message_queue.empty() and len(batch) < BATCH_SIZE:
                batch.append(message_queue.get_nowait())
                
        except asyncio.TimeoutError:
            pass # Flush interval reached
            
        if batch:
            start_time = time.time()
            conn = sqlite3.connect(DB_PATH)
            try:
                conn.execute("PRAGMA journal_mode=WAL;")
                conn.execute("PRAGMA synchronous=NORMAL;")
            except Exception:
                pass
            c = conn.cursor()
            c.executemany("INSERT INTO broker_messages (topic, payload) VALUES (?, ?)", batch)
            
            duration_ms = (time.time() - start_time) * 1000
            c.execute("INSERT INTO broker_stats (messages_processed, flush_duration_ms) VALUES (?, ?)", (len(batch), duration_ms))
            conn.commit()
            conn.close()
            print(f"[Broker] Flushed {len(batch)} messages to disk in {duration_ms:.2f}ms")

# --- Web Server Routes ---
async def handle_publish(request):
    try:
        data = await request.json()
        topic = data.get("topic", "default")
        payload = json.dumps(data.get("payload", {}))
        
        # Non-blocking put to memory
        message_queue.put_nowait((topic, payload))
        
        return web.json_response({"status": "queued", "queue_depth": message_queue.qsize()})
    except Exception as e:
        return web.json_response({"status": "error", "error": str(e)}, status=400)

async def handle_stats(request):
    conn = sqlite3.connect(DB_PATH)
    try:
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA synchronous=NORMAL;")
    except Exception:
        pass
    c = conn.cursor()
    c.execute("SELECT SUM(messages_processed) FROM broker_stats")
    total = c.fetchone()[0] or 0
    conn.close()
    
    return web.json_response({
        "status": "online",
        "current_queue_depth": message_queue.qsize(),
        "total_messages_processed": total
    })

# --- Main Entry ---
async def init_app():
    init_db()
    app = web.Application()
    app.router.add_post('/publish', handle_publish)
    app.router.add_get('/stats', handle_stats)
    
    # Start background task
    asyncio.create_task(batch_processor())
    return app

if __name__ == '__main__':
    web.run_app(init_app(), port=BROKER_PORT)
