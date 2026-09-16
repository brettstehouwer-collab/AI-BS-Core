import os
import re

backend_dir = r"C:\AI-BS\backend"
ai_bs_backend_path = os.path.join(backend_dir, "AI_BS_Backend.py")

# Read AI_BS_Backend.py
with open(ai_bs_backend_path, "r", encoding="utf-8") as f:
    content = f.read()

# 1. Inject FastAPI dependencies
if "from fastapi import Header, Depends" not in content:
    content = content.replace(
        "from fastapi import FastAPI",
        "from fastapi import FastAPI, Header, Depends\nfrom typing import Optional",
    )

# 2. Inject get_tenant function
tenant_func = """
def get_tenant(x_client_id: Optional[str] = Header(None)):
    return x_client_id if x_client_id else "stehouwer_publishing"
"""
if "def get_tenant" not in content:
    # Inject it after app = FastAPI()
    content = content.replace("app = FastAPI()", f"app = FastAPI()\n{tenant_func}")

# 3. Add client_id to Pydantic models
models_to_patch = [
    r"(class PublishingSecurityEventPayload\(BaseModel\):\n)",
    r"(class StateLeadPayload\(BaseModel\):\n)",
    r"(class BudgetPayload\(BaseModel\):\n)",
    r"(class TelemetryPayload\(BaseModel\):\n)",
]
for p in models_to_patch:
    content = re.sub(p, r'\1    client_id: str = "stehouwer_publishing"\n', content)

# 4. Route injection (telemetry, budgets)
content = content.replace(
    "def get_adv_budgets():", "def get_adv_budgets(tenant: str = Depends(get_tenant)):"
)
content = content.replace(
    "def save_adv_budgets(budgets: list[BudgetPayload]):",
    "def save_adv_budgets(budgets: list[BudgetPayload], tenant: str = Depends(get_tenant)):",
)
content = content.replace(
    "async def ingest_official_telemetry(payload: TelemetryPayload):",
    "async def ingest_official_telemetry(payload: TelemetryPayload, tenant: str = Depends(get_tenant)):",
)
content = content.replace(
    "async def ingest_shadow_telemetry(payload: TelemetryPayload):",
    "async def ingest_shadow_telemetry(payload: TelemetryPayload, tenant: str = Depends(get_tenant)):",
)
content = content.replace(
    "def security_log(payload: PublishingSecurityEventPayload):",
    "def security_log(payload: PublishingSecurityEventPayload, tenant: str = Depends(get_tenant)):",
)

# 5. SQLite Alter Table logic for AI_BS_Backend.py
# Find all CREATE TABLE IF NOT EXISTS occurrences and inject ALTER TABLE afterwards.
# Let's add a global startup script inside AI_BS_Backend.py to alter existing DBs.
alter_logic = """
# Multi-Tenant DB Migration
def run_db_migrations():
    import sqlite3
    db_paths = [
        os.path.join(get_base_dir(), "database", "ai_bs_omnidrive.db"),
        os.path.join(get_base_dir(), "database", "security_events.db")
    ]
    tables_to_check = ['advertising_leads', 'file_state', 'security_events']
    
    for p in db_paths:
        if os.path.exists(p):
            try:
                conn = sqlite3.connect(p)
                try:
                    conn.execute("PRAGMA journal_mode=WAL;")
                    conn.execute("PRAGMA synchronous=NORMAL;")
                except Exception:
                    pass
                cursor = conn.cursor()
                for table in tables_to_check:
                    try:
                        cursor.execute(f"ALTER TABLE {table} ADD COLUMN client_id TEXT DEFAULT 'stehouwer_publishing'")
                    except sqlite3.OperationalError as e:
                        # Column might already exist or table doesn't exist
                        pass
                conn.commit()
                conn.close()
            except Exception as e:
                print(f"Migration Error on {p}: {e}")

run_db_migrations()
"""
if "run_db_migrations()" not in content:
    content = content.replace("app = FastAPI()", f"{alter_logic}\napp = FastAPI()")

# Write back
with open(ai_bs_backend_path, "w", encoding="utf-8") as f:
    f.write(content)
print("Patched AI_BS_Backend.py")

# Patch calendar_integration.py
cal_path = os.path.join(backend_dir, "calendar_integration.py")
if os.path.exists(cal_path):
    with open(cal_path, "r", encoding="utf-8") as f:
        cal_content = f.read()

    # Add client_id to schema
    cal_content = re.sub(
        r"(class AppointmentCreate\(BaseModel\):\n)",
        r'\1    client_id: str = "stehouwer_publishing"\n',
        cal_content,
    )

    # Add alter table logic to init_db
    if "ALTER TABLE appointments ADD COLUMN client_id" not in cal_content:
        cal_content = cal_content.replace(
            "CREATE TABLE IF NOT EXISTS appointments (",
            "CREATE TABLE IF NOT EXISTS appointments (\n                client_id TEXT DEFAULT 'stehouwer_publishing',",
        )
        alter_snippet = """
        try:
            cursor.execute("ALTER TABLE appointments ADD COLUMN client_id TEXT DEFAULT 'stehouwer_publishing'")
        except:
            pass
"""
        cal_content = cal_content.replace(
            "        conn.commit()", f"{alter_snippet}\n        conn.commit()"
        )

    with open(cal_path, "w", encoding="utf-8") as f:
        f.write(cal_content)
    print("Patched calendar_integration.py")

# Patch enterprise_ledger.py
ledger_path = os.path.join(backend_dir, "enterprise_ledger.py")
if os.path.exists(ledger_path):
    with open(ledger_path, "r", encoding="utf-8") as f:
        led_content = f.read()

    if "ALTER TABLE ledger ADD COLUMN client_id" not in led_content:
        led_content = led_content.replace(
            "CREATE TABLE IF NOT EXISTS ledger (",
            "CREATE TABLE IF NOT EXISTS ledger (\n                    client_id TEXT DEFAULT 'stehouwer_publishing',",
        )
        alter_snippet = """
            try:
                cursor.execute("ALTER TABLE ledger ADD COLUMN client_id TEXT DEFAULT 'stehouwer_publishing'")
            except:
                pass
"""
        led_content = led_content.replace(
            "            conn.commit()", f"{alter_snippet}\n            conn.commit()"
        )

    with open(ledger_path, "w", encoding="utf-8") as f:
        f.write(led_content)
    print("Patched enterprise_ledger.py")

# Patch client_scheduler_engine.py
client_sch_path = os.path.join(backend_dir, "client_scheduler_engine.py")
if os.path.exists(client_sch_path):
    with open(client_sch_path, "r", encoding="utf-8") as f:
        sch_content = f.read()

    if "ALTER TABLE client_profiles ADD COLUMN client_id" not in sch_content:
        sch_content = sch_content.replace(
            "CREATE TABLE IF NOT EXISTS client_profiles (",
            "CREATE TABLE IF NOT EXISTS client_profiles (\n                    client_id TEXT DEFAULT 'stehouwer_publishing',",
        )
        sch_content = sch_content.replace(
            "CREATE TABLE IF NOT EXISTS client_email_requests (",
            "CREATE TABLE IF NOT EXISTS client_email_requests (\n                    client_id TEXT DEFAULT 'stehouwer_publishing',",
        )
        sch_content = sch_content.replace(
            "CREATE TABLE IF NOT EXISTS scheduled_posts_queue (",
            "CREATE TABLE IF NOT EXISTS scheduled_posts_queue (\n                    client_id TEXT DEFAULT 'stehouwer_publishing',",
        )
        alter_snippet = """
            tables = ['client_profiles', 'client_email_requests', 'scheduled_posts_queue']
            for t in tables:
                try:
                    cursor.execute(f"ALTER TABLE {t} ADD COLUMN client_id TEXT DEFAULT 'stehouwer_publishing'")
                except:
                    pass
"""
        sch_content = sch_content.replace(
            "            conn.commit()", f"{alter_snippet}\n            conn.commit()"
        )

    with open(client_sch_path, "w", encoding="utf-8") as f:
        f.write(sch_content)
    print("Patched client_scheduler_engine.py")
