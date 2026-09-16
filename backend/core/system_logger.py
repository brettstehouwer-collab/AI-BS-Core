import logging
import sqlite3
import os
import json
import asyncio
from datetime import datetime, timedelta

LOG_DB_PATH = os.path.join(os.path.dirname(__file__), "..", "system_logs.db")

# Global list of asyncio.Queue for SSE clients
active_sse_queues = []

def init_db():
    conn = sqlite3.connect(LOG_DB_PATH)
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT,
            level TEXT,
            name TEXT,
            message TEXT
        )
    ''')
    conn.commit()
    conn.close()

class SQLiteAndSSEHandler(logging.Handler):
    def __init__(self):
        super().__init__()
        init_db()

    def emit(self, record):
        try:
            timestamp = datetime.utcnow().isoformat() + "Z"
            msg = self.format(record)
            
            # Write to SQLite
            conn = sqlite3.connect(LOG_DB_PATH)
            c = conn.cursor()
            c.execute(
                "INSERT INTO logs (timestamp, level, name, message) VALUES (?, ?, ?, ?)",
                (timestamp, record.levelname, record.name, msg)
            )
            conn.commit()
            conn.close()

            # Push to SSE Queues
            log_entry = {
                "timestamp": timestamp,
                "level": record.levelname,
                "name": record.name,
                "message": msg
            }
            
            # Safely put to asyncio queues from the logging thread
            for q in list(active_sse_queues):
                try:
                    # Non-blocking put_nowait if we are in an event loop
                    loop = asyncio.get_running_loop()
                    loop.call_soon_threadsafe(q.put_nowait, log_entry)
                except RuntimeError:
                    # No running event loop
                    pass
        except Exception:
            self.handleError(record)

def setup_logger():
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)
    
    # Avoid duplicating handlers if setup_logger is called multiple times
    for handler in root_logger.handlers:
        if isinstance(handler, SQLiteAndSSEHandler):
            return
            
    custom_handler = SQLiteAndSSEHandler()
    formatter = logging.Formatter('%(message)s')
    custom_handler.setFormatter(formatter)
    
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(logging.Formatter('[%(levelname)s] %(name)s: %(message)s'))
    
    root_logger.addHandler(custom_handler)
    root_logger.addHandler(console_handler)
    
    logging.info("System Logger initialized. SQLite and SSE handlers active.")
