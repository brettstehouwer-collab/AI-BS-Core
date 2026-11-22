import sqlite3
import os
import datetime
import json
import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s")

DB_PATH = os.path.join(
    os.path.dirname(
        os.path.abspath(__file__)),
    "telemetry_checkpoint.sqlite")


def initialize_database():
    """Initializes the SQLite database with WAL and the required schema."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Enable Write-Ahead Logging for high-concurrency across agent threads
    cursor.execute("PRAGMA journal_mode=WAL;")

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS hardware_telemetry (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            vram_allocated_mb REAL NOT NULL,
            system_ram_mb REAL NOT NULL,
            cpu_thread_utilization TEXT NOT NULL,
            active_task_id TEXT NOT NULL,
            keep_alive_trigger INTEGER NOT NULL DEFAULT 0
        )
    """)
    conn.commit()
    conn.close()
    logging.info(f"Initialized telemetry database at {DB_PATH}")


def log_telemetry(
        vram_mb,
        system_ram_mb,
        cpu_utilization_dict,
        active_task_id,
        keep_alive=0):
    """Inserts a new telemetry checkpoint into the time-series database."""
    timestamp = datetime.datetime.now(datetime.timezone.utc).isoformat() + "Z"
    cpu_json = json.dumps(cpu_utilization_dict)

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO hardware_telemetry
        (timestamp, vram_allocated_mb, system_ram_mb, cpu_thread_utilization, active_task_id, keep_alive_trigger)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (timestamp, vram_mb, system_ram_mb, cpu_json, active_task_id, keep_alive))
    conn.commit()
    conn.close()
    logging.info(f"Logged telemetry checkpoint for task: {active_task_id}")


if __name__ == "__main__":
    # Self-test / Initialization sequence
    initialize_database()

    # Mock data insertion to verify functionality
    mock_cpu = {"core_0": 45.2, "core_1": 60.1}
    log_telemetry(4500.5, 12000.0, mock_cpu, "init_test_agent", keep_alive=1)
    print("Database initialization and mock insertion complete.")
