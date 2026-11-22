import os
import sqlite3
import shutil

MASTER_DB_PATH = "C:/AI-BS/backend/aibs_master.db"

DBS_TO_CONSOLIDATE = {
    "state": ("C:/AI-BS/backend/state.db", "stehouwer_publishing"),
    "clients": ("C:/AI-BS/backend/clients.db", "action_glass"),
    "unreal_assets": ("C:/AI-BS/backend/unreal_assets.db", "stehouwer_publishing"),
    "stehouwer_vault": ("C:/AI-BS/backend/stehouwer_vault.db", "stehouwer_publishing"),
    "stehouwer_accounting": ("C:/AI-BS/backend/stehouwer_accounting.db", "stehouwer_publishing"),
    "west_michigan": ("C:/AI-BS/backend/west_michigan.db", "joey_hamilton"),
    "drip_ledger": ("C:/AI-BS/backend/drip_ledger.db", "stehouwer_publishing")
}

def consolidate():
    print(f"=== Starting Consolidation into {MASTER_DB_PATH} ===")
    
    # Remove existing master if rebuilding
    if os.path.exists(MASTER_DB_PATH):
        os.remove(MASTER_DB_PATH)
        
    master_conn = sqlite3.connect(MASTER_DB_PATH)
    master_conn.execute("PRAGMA journal_mode = WAL;")
    master_conn.execute("PRAGMA synchronous = NORMAL;")
    master_conn.execute("PRAGMA busy_timeout = 30000;")
    master_conn.execute("PRAGMA mmap_size = 268435456;")
    master_conn.execute("PRAGMA cache_size = -64000;")
    master_conn.execute("PRAGMA foreign_keys = ON;")
    
    total_tables_migrated = 0
    total_rows_migrated = 0
    
    for db_key, (source_path, default_tenant) in DBS_TO_CONSOLIDATE.items():
        if not os.path.exists(source_path):
            print(f"[-] Warning: {source_path} does not exist, skipping.")
            continue
            
        print(f"\n[*] Ingesting from {db_key} ({source_path})...")
        src_conn = sqlite3.connect(source_path)
        src_cursor = src_conn.cursor()
        
        # Get all tables
        src_cursor.execute("SELECT name, sql FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")
        tables = src_cursor.fetchall()
        
        for table_name, create_sql in tables:
            print(f"    - Migrating table: {table_name}")
            
            # Check source columns
            src_cursor.execute(f"PRAGMA table_info('{table_name}')")
            cols_info = src_cursor.fetchall()
            col_names = [col[1] for col in cols_info]
            has_client_id = "client_id" in col_names
            
            # Create table in master if not exists
            if create_sql:
                # Sanitize create_sql to ensure clean creation
                try:
                    master_conn.execute(create_sql)
                except sqlite3.OperationalError as e:
                    print(f"      [!] Create table warning: {e}")
            
            # Ensure client_id column exists
            master_cursor = master_conn.cursor()
            master_cursor.execute(f"PRAGMA table_info('{table_name}')")
            m_cols = [c[1] for c in master_cursor.fetchall()]
            if "client_id" not in m_cols:
                master_conn.execute(f"ALTER TABLE '{table_name}' ADD COLUMN client_id TEXT DEFAULT '{default_tenant}'")
            
            # Copy rows
            src_cursor.execute(f"SELECT * FROM '{table_name}'")
            rows = src_cursor.fetchall()
            
            if rows:
                if has_client_id:
                    placeholders = ", ".join(["?"] * len(col_names))
                    cols_str = ", ".join([f"'{c}'" for c in col_names])
                    master_conn.executemany(f"INSERT OR REPLACE INTO '{table_name}' ({cols_str}) VALUES ({placeholders})", rows)
                else:
                    # Append default client_id
                    new_rows = [tuple(list(r) + [default_tenant]) for r in rows]
                    placeholders = ", ".join(["?"] * (len(col_names) + 1))
                    cols_str = ", ".join([f"'{c}'" for c in col_names] + ["'client_id'"])
                    master_conn.executemany(f"INSERT OR REPLACE INTO '{table_name}' ({cols_str}) VALUES ({placeholders})", new_rows)
            
            master_conn.commit()
            row_count = len(rows)
            total_rows_migrated += row_count
            total_tables_migrated += 1
            print(f"      [OK] {row_count} rows migrated.")
            
        # Copy indexes
        src_cursor.execute("SELECT name, sql FROM sqlite_master WHERE type='index' AND sql IS NOT NULL AND name NOT LIKE 'sqlite_%'")
        indexes = src_cursor.fetchall()
        for idx_name, idx_sql in indexes:
            try:
                master_conn.execute(idx_sql)
            except Exception:
                pass
        master_conn.commit()
        src_conn.close()
        
    # Check integrity
    cur = master_conn.cursor()
    cur.execute("PRAGMA quick_check;")
    check_res = cur.fetchone()[0]
    
    sz = os.path.getsize(MASTER_DB_PATH)
    print(f"\n=======================================================")
    print(f"SUCCESS: Consolidated {total_tables_migrated} tables and {total_rows_migrated:,} rows into {MASTER_DB_PATH}")
    print(f"File Size: {sz:,} bytes")
    print(f"Integrity Check: {check_res}")
    print(f"=======================================================")
    master_conn.close()

if __name__ == "__main__":
    consolidate()
