"""
Unit tests for AI-BS Sovereign Multi-Tenant Isolation & RLS Engine.
Tests async safety, SQL scoping, Pydantic v2 validation, and real SQLite querying.
"""
import sys
import asyncio
import sqlite3
from pathlib import Path
import pytest

# Ensure backend directory is in sys.path
backend_path = Path(r"C:\AI-BS\backend")
if str(backend_path) not in sys.path:
    sys.path.insert(0, str(backend_path))

from core.tenant_isolation import (
    set_current_tenant,
    get_current_tenant,
    tenant_scope,
    TenantSecurityError,
    TenantContextModel,
    apply_sqlite_tenant_filter,
    generate_postgres_rls_ddl
)

def test_tenant_validation():
    # Valid IDs
    assert TenantContextModel(tenant_id="stehouwer_publishing").tenant_id == "stehouwer_publishing"
    assert TenantContextModel(tenant_id="client-42_test").tenant_id == "client-42_test"
    
    # Invalid IDs (too short, forbidden characters)
    with pytest.raises(Exception):
        TenantContextModel(tenant_id="a") # < 3 chars
    with pytest.raises(Exception):
        TenantContextModel(tenant_id="invalid; injection; DROP TABLE") # Disallowed characters

def test_tenant_scope_sync():
    with pytest.raises(TenantSecurityError):
        get_current_tenant() # None set
        
    with tenant_scope("tenant_alpha"):
        assert get_current_tenant() == "tenant_alpha"
        
        # Nested scope
        with tenant_scope("tenant_beta"):
            assert get_current_tenant() == "tenant_beta"
            
        # Restored outer
        assert get_current_tenant() == "tenant_alpha"
        
    with pytest.raises(TenantSecurityError):
        get_current_tenant()

def test_tenant_scope_async():
    async def task_worker(tenant_name: str, delay: float):
        async with tenant_scope(tenant_name):
            await asyncio.sleep(delay)
            return get_current_tenant()
            
    async def runner():
        return await asyncio.gather(
            task_worker("tenant_1", 0.02),
            task_worker("tenant_2", 0.01),
            task_worker("tenant_3", 0.03)
        )
        
    res = asyncio.run(runner())
    assert res == ["tenant_1", "tenant_2", "tenant_3"], "Async contextvars were corrupted across tasks!"

def test_sql_filter_generation():
    # 1. Simple SELECT
    sql1, p1 = apply_sqlite_tenant_filter("SELECT * FROM assets", tenant_id="client_A")
    assert sql1 == "SELECT * FROM assets WHERE client_id = :_sec_client_id"
    assert p1 == {"_sec_client_id": "client_A"}
    
    # 2. SELECT with WHERE and OR (must be enclosed in parentheses to prevent escape)
    sql2, p2 = apply_sqlite_tenant_filter("SELECT id, name FROM assets WHERE type = 'mesh' OR type = 'texture'", tenant_id="client_B")
    assert sql2 == "SELECT id, name FROM assets WHERE (type = 'mesh' OR type = 'texture') AND client_id = :_sec_client_id"
    assert p2 == {"_sec_client_id": "client_B"}
    
    # 3. SELECT with ORDER BY and LIMIT
    sql3, p3 = apply_sqlite_tenant_filter("SELECT * FROM assets ORDER BY id DESC LIMIT 10", tenant_id="client_C")
    assert sql3 == "SELECT * FROM assets WHERE client_id = :_sec_client_id ORDER BY id DESC LIMIT 10"

def test_real_sqlite_execution():
    db_path = Path(r"C:\AI-BS\backend\aibs_master.db")
    if not db_path.exists():
        pytest.skip("aibs_master.db not available")
        
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    
    # Query with tenant isolation
    with tenant_scope("stehouwer_publishing"):
        sql, params = apply_sqlite_tenant_filter("SELECT COUNT(*) FROM client_profiles")
        c.execute(sql, params)
        count = c.fetchone()[0]
        # Must execute cleanly with parameterization
        assert count >= 0
        
    conn.close()

def test_postgres_rls_ddl_generation():
    tables = ["assets", "vault_data", "accounting_entries"]
    ddl = generate_postgres_rls_ddl(tables, "client_id")
    assert "ALTER TABLE assets ENABLE ROW LEVEL SECURITY;" in ddl
    assert "CREATE POLICY assets_tenant_isolation ON assets" in ddl
    assert "USING (client_id = current_setting('app.current_tenant', true))" in ddl
    assert "ALTER TABLE vault_data ENABLE ROW LEVEL SECURITY;" in ddl
