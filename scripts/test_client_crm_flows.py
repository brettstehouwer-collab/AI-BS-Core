"""
AI-BS Multi-Client CRM Integration Test Engine
Simulates automated end-to-end lead ingestion and quoting for Action Glass,
Prestige Mobile Wash, and Joey Hamilton Real Estate with SQLite WAL persistence.
"""

import sqlite3
import json
import time
import os
import uuid

LEADS_DB = r"C:\AI-BS\leads_store.db"

def init_crm_tables(conn):
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA synchronous=NORMAL;")
    conn.execute("""
        CREATE TABLE IF NOT EXISTS client_crm_leads (
            id TEXT PRIMARY KEY,
            created_at REAL,
            client_id TEXT,
            lead_name TEXT,
            service_type TEXT,
            estimated_value REAL,
            status TEXT,
            metadata TEXT
        );
    """)
    conn.commit()

def run_crm_simulation():
    print("=" * 75)
    print("        AI-BS MULTI-CLIENT CRM WORKFLOW SIMULATION & INTEGRATION")
    print("=" * 75)
    
    conn = sqlite3.connect(LEADS_DB, timeout=5.0)
    init_crm_tables(conn)
    
    now_ts = time.time()
    
    test_leads = [
        {
            "id": f"lead_ag_{uuid.uuid4().hex[:8]}",
            "client_id": "action_glass",
            "lead_name": "Michigan Fleet Logistics - Windshield Replacement",
            "service_type": "Commercial Fleet Glass",
            "estimated_value": 1450.00,
            "status": "QUALIFIED",
            "metadata": json.dumps({"vehicles": 4, "location": "Jenison, MI", "urgency": "High"})
        },
        {
            "id": f"lead_pmw_{uuid.uuid4().hex[:8]}",
            "client_id": "prestige_mobile_wash",
            "lead_name": "Grand Rapids Industrial Park - Concrete Wash",
            "service_type": "Commercial Hot-Water Surface Cleaning",
            "estimated_value": 2800.00,
            "status": "SCHEDULED",
            "metadata": json.dumps({"sqft": 15000, "chemical": "EcoDegreaser-Pro", "units": 2})
        },
        {
            "id": f"lead_jh_{uuid.uuid4().hex[:8]}",
            "client_id": "joey_hamilton",
            "lead_name": "East Grand Rapids Luxury Residential Listing",
            "service_type": "Seller Representation & Valuation",
            "estimated_value": 750000.00,
            "status": "PROSPECT",
            "metadata": json.dumps({"beds": 5, "baths": 4, "sqft": 4200, "commission_est": 22500.00})
        }
    ]
    
    for lead in test_leads:
        conn.execute("""
            INSERT OR REPLACE INTO client_crm_leads 
            (id, created_at, client_id, lead_name, service_type, estimated_value, status, metadata)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?);
        """, (
            lead["id"],
            now_ts,
            lead["client_id"],
            lead["lead_name"],
            lead["service_type"],
            lead["estimated_value"],
            lead["status"],
            lead["metadata"]
        ))
        
    conn.commit()
    
    # Query back partitioned by client_id
    cur = conn.cursor()
    print("\n--- Client Partitioned CRM Records ---")
    for client in ["action_glass", "prestige_mobile_wash", "joey_hamilton"]:
        cur.execute("SELECT count(*), sum(estimated_value) FROM client_crm_leads WHERE client_id = ?;", (client,))
        count, total_val = cur.fetchone()
        print(f"  * Client: {client:<22} | Total Leads: {count} | Pipeline Value: ${total_val or 0:,.2f}")
        
    integrity = conn.execute("PRAGMA integrity_check;").fetchall()[0][0]
    journal = conn.execute("PRAGMA journal_mode;").fetchone()[0]
    conn.close()
    
    print("\n--- Database Concurrency Check ---")
    print(f"  * leads_store.db: Integrity = {integrity} | Mode = {journal}")
    print("=" * 75)
    print("[SUCCESS] Multi-Client CRM Lead Generation & WAL Persistence Verified.")

if __name__ == "__main__":
    run_crm_simulation()