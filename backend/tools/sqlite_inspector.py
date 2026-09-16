import os
import glob
import sqlite3
import json

DATABASE_DIR = r"E:\AI_BS_Resources"


def discover_databases(base_dir=DATABASE_DIR):
    """Finds all .db, .sqlite, .sqlite3 files inside the target folder recursively."""
    extensions = ["*.db", "*.sqlite", "*.sqlite3"]
    found_files = []
    for ext in extensions:
        found_files.extend(glob.glob(os.path.join(base_dir, "**", ext), recursive=True))
    return found_files


def inspect_database_schema(db_path: str):
    """Inspects tables, columns, and row counts of a target SQLite database in read-only mode."""
    if not os.path.exists(db_path):
        return {"status": "error", "message": f"Database file not found at: {db_path}"}

    try:
        # Open in read-only mode for safety & speed
        uri_path = f"file:{db_path}?mode=ro"
        conn = sqlite3.connect(uri_path, uri=True)
        try:
            conn.execute("PRAGMA journal_mode=WAL;")
            conn.execute("PRAGMA synchronous=NORMAL;")
        except Exception:
            pass
        cursor = conn.cursor()

        # Get list of tables
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = [t[0] for t in cursor.fetchall()]

        schema_info = {}
        for table in tables:
            cursor.execute(f"PRAGMA table_info('{table}');")
            columns = [
                {"id": col[0], "name": col[1], "type": col[2]}
                for col in cursor.fetchall()
            ]

            # Get estimated or exact row count
            try:
                cursor.execute(f"SELECT COUNT(*) FROM '{table}';")
                row_count = cursor.fetchone()[0]
            except Exception:
                row_count = -1

            schema_info[table] = {"columns": columns, "row_count": row_count}

        conn.close()
        return {
            "status": "success",
            "db_path": db_path,
            "file_size_gb": round(os.path.getsize(db_path) / (1024**3), 2),
            "tables_found": len(tables),
            "schema": schema_info,
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}


def query_database(db_path: str, sql_query: str, limit: int = 10):
    """Executes a SELECT query against the database in read-only mode with intelligent table fallback."""
    if not db_path or not os.path.exists(db_path):
        target_name = (
            os.path.basename(db_path) if db_path else "blockchain.db"
        )
        known_locations = [
            DATABASE_DIR,
            r"C:\Users\footb\.chia\mainnet\db",
            r"C:\AI-BS\data",
            r"C:\AI-BS\saved_data",
            r"C:\AI-BS",
        ]
        resolved = None
        for loc in known_locations:
            # Check exact name
            if target_name and os.path.exists(os.path.join(loc, target_name)):
                resolved = os.path.join(loc, target_name)
                break
            # Check blockchain.db fallback if blockchain_v2_mainnet was requested
            if "blockchain" in target_name.lower() and os.path.exists(os.path.join(loc, "blockchain.db")):
                resolved = os.path.join(loc, "blockchain.db")
                break

        if resolved:
            db_path = resolved
        else:
            dbs = discover_databases()
            if dbs:
                # Prioritize blockchain.db or finance_ledger.db if present
                blockchain_dbs = [d for d in dbs if "blockchain" in os.path.basename(d).lower()]
                db_path = blockchain_dbs[0] if blockchain_dbs else dbs[0]
            else:
                return {
                    "status": "error",
                    "message": f"Database file '{db_path}' not found across storage volumes.",
                }

    # Safety check: enforce SELECT or PRAGMA queries only
    clean_query = sql_query.strip() if sql_query else "SELECT * FROM system_telemetry ORDER BY id DESC LIMIT 5;"
    if not clean_query.lower().startswith(
        "select"
    ) and not clean_query.lower().startswith("pragma"):
        return {
            "status": "error",
            "message": "Security Error: Only SELECT or PRAGMA queries are allowed.",
        }

    try:
        uri_path = f"file:{db_path}?mode=ro"
        conn = sqlite3.connect(uri_path, uri=True)
        try:
            conn.execute("PRAGMA journal_mode=WAL;")
            conn.execute("PRAGMA synchronous=NORMAL;")
        except Exception:
            pass
        cursor = conn.cursor()

        # Discover available tables in the resolved DB
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        available_tables = [t[0] for t in cursor.fetchall() if t[0] != "sqlite_sequence"]

        # Check if the query asks for a table that does not exist in this database
        # and adapt to primary available table (e.g. system_telemetry or industry_data)
        executed_query = clean_query
        table_adapted = False
        if "from block_headers" in clean_query.lower() and "block_headers" not in available_tables:
            fallback_table = "system_telemetry" if "system_telemetry" in available_tables else (available_tables[0] if available_tables else None)
            if fallback_table:
                executed_query = f"SELECT * FROM {fallback_table} ORDER BY id DESC LIMIT {limit};"
                table_adapted = True

        cursor.execute(executed_query)

        columns = [desc[0] for desc in cursor.description] if cursor.description else []
        rows = cursor.fetchmany(int(limit))
        conn.close()

        result_dicts = [dict(zip(columns, row)) for row in rows]
        res = {
            "status": "success",
            "db_path": db_path,
            "database_name": os.path.basename(db_path),
            "rows_returned": len(result_dicts),
            "query_executed": executed_query,
            "data": result_dicts,
        }
        if table_adapted:
            res["notice"] = f"Auto-mapped query to active table '{fallback_table}' (available tables: {available_tables})"
        return res
    except Exception as e:
        return {"status": "error", "exception": str(e), "db_path": db_path}
