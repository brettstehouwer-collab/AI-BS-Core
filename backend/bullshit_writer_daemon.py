import sqlite3
import queue
import threading
import time
import os
import uvicorn
from contextlib import asynccontextmanager
from fastapi import FastAPI
from pydantic import BaseModel
from typing import List, Optional
import socket
from fastapi import FastAPI, Header, Depends


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    # Start the singular background worker thread
    thread = threading.Thread(target=writer_worker, daemon=True)
    thread.start()
    yield


app = FastAPI(title="AI-BS Database Writer Daemon", lifespan=lifespan)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PORT_FILE = os.path.join(BASE_DIR, ".writer_daemon_port")
DB_PATH = os.path.join(BASE_DIR, "state.db")

write_queue = queue.PriorityQueue()


# Ensure table exists
def init_db():
    conn = sqlite3.connect(DB_PATH)
    try:
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA synchronous=NORMAL;")
    except Exception:
        pass
    conn.execute("PRAGMA journal_mode=WAL;")
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS file_state (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            drive TEXT,
            filepath TEXT UNIQUE,
            filename TEXT,
            extension TEXT,
            size_bytes INTEGER,
            last_scanned REAL,
            client_id TEXT DEFAULT 'stehouwer_publishing'
        )
    """)
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_filename ON file_state(filename)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_extension ON file_state(extension)")
    conn.commit()
    conn.close()


def writer_worker():
    """Background thread that pops from the queue and writes to the DB to prevent locks."""
    print("[DB Writer] Worker thread started. Connecting to state.db.")
    conn = sqlite3.connect(DB_PATH)
    try:
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA synchronous=NORMAL;")
    except Exception:
        pass
    conn.execute("PRAGMA journal_mode=WAL;")
    cursor = conn.cursor()

    while True:
        try:
            # PriorityQueue returns a tuple (priority, item)
            queue_item = write_queue.get(timeout=1.0)  # Check every 1 second

            if queue_item is None:
                break  # Poison pill to exit

            priority, task_payload = queue_item
            task_type, data = task_payload

            if task_type == "insert_batch":
                cursor.executemany(
                    """
                    INSERT OR REPLACE INTO file_state 
                    (drive, filepath, filename, extension, size_bytes, last_scanned, client_id) 
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                    data,
                )
                conn.commit()
                print(f"[DB Writer] Successfully committed {len(data)} rows.")

            elif task_type == "delete_path":
                cursor.execute("DELETE FROM file_state WHERE filepath = ?", (data,))
                conn.commit()
                print(f"[DB Writer] Successfully deleted path: {data}")

            elif task_type == "execute_raw":
                query, params = data
                cursor.execute(query, params)
                conn.commit()
                print(f"[DB Writer] Executed raw query.")

            write_queue.task_done()

        except queue.Empty:
            continue
        except Exception as e:
            print(f"[DB Writer Error] {e}")


# Models
class InsertBatchPayload(BaseModel):
    priority: int = 10  # Default low priority
    rows: List[list]


class DeletePathPayload(BaseModel):
    priority: int = 1  # Deletes usually need to happen fast
    filepath: str


def get_tenant(x_client_id: Optional[str] = Header(None)):
    return x_client_id if x_client_id else "stehouwer_publishing"


@app.post("/write_batch")
def write_batch(payload: InsertBatchPayload, tenant: str = Depends(get_tenant)):
    # Convert lists back to tuples for executemany and append client_id
    tuples_data = [tuple(row) + (tenant,) for row in payload.rows]
    write_queue.put((payload.priority, ("insert_batch", tuples_data)))
    return {
        "status": "queued",
        "priority": payload.priority,
        "message": f"{len(tuples_data)} rows queued for insertion.",
    }


@app.post("/delete_path")
def delete_path(payload: DeletePathPayload):
    write_queue.put((payload.priority, ("delete_path", payload.filepath)))
    return {
        "status": "queued",
        "priority": payload.priority,
        "message": "Deletion queued.",
    }


def get_free_port():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("", 0))
        return s.getsockname()[1]


if __name__ == "__main__":
    port = get_free_port()
    with open(PORT_FILE, "w") as f:
        f.write(str(port))

    print("==================================================")
    print(f"AI-BS DB Writer Daemon Initializing on dynamic port {port}...")
    print("==================================================")
    uvicorn.run(app, host="127.0.0.1", port=port, log_level="info")
