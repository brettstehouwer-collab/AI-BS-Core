"""
AI-BS Sovereign Multi-Tenant Isolation & Row-Level Security (RLS) Engine
Provides async-safe ContextVar tenant context, query scoping, and Pydantic v2 validation.
"""
from __future__ import annotations
import sqlite3
import contextvars
from typing import Optional, List, Dict, Any, Tuple
from pydantic import BaseModel, Field, StringConstraints
from typing_extensions import Annotated
import logging

logger = logging.getLogger("tenant_isolation")

# Thread/coroutine safe tenant context variable
_CURRENT_TENANT: contextvars.ContextVar[Optional[str]] = contextvars.ContextVar("current_tenant", default=None)

# Validated tenant identifier: 3 to 64 chars, alphanumeric, underscores, hyphens
TenantId = Annotated[str, StringConstraints(min_length=3, max_length=64, pattern=r"^[a-zA-Z0-9_\-]+$")]

class TenantContextModel(BaseModel):
    tenant_id: TenantId
    tier: str = Field(default="standard", description="Tenant service tier: standard, enterprise, sovereign")
    is_active: bool = Field(default=True)

class TenantSecurityError(RuntimeError):
    """Raised when an operation attempts to bypass tenant boundaries."""
    pass

def set_current_tenant(tenant_id: str) -> contextvars.Token:
    """Sets the active tenant for the current async task context."""
    # Validate format
    validated = TenantContextModel(tenant_id=tenant_id).tenant_id
    return _CURRENT_TENANT.set(validated)

def reset_current_tenant(token: contextvars.Token) -> None:
    """Restores prior tenant context."""
    _CURRENT_TENANT.reset(token)

def get_current_tenant(default: Optional[str] = None) -> str:
    """Retrieves current tenant or default if set. Raises TenantSecurityError if none set."""
    val = _CURRENT_TENANT.get()
    if val:
        return val
    if default:
        return default
    raise TenantSecurityError("No active tenant context established for this execution frame.")

class tenant_scope:
    """Async & sync context manager for tenant execution scoping."""
    def __init__(self, tenant_id: str):
        self.tenant_id = tenant_id
        self._token: Optional[contextvars.Token] = None

    def __enter__(self):
        self._token = set_current_tenant(self.tenant_id)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self._token:
            reset_current_tenant(self._token)

    async def __aenter__(self):
        self._token = set_current_tenant(self.tenant_id)
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self._token:
            reset_current_tenant(self._token)

def apply_sqlite_tenant_filter(
    base_sql: str, 
    tenant_id: Optional[str] = None, 
    tenant_column: str = "client_id"
) -> Tuple[str, Dict[str, Any]]:
    """
    Appends or wraps SQL statement with explicit tenant isolation.
    Guarantees client_id parameterization.
    """
    active_tenant = tenant_id or get_current_tenant()
    
    # Strip trailing semicolons or whitespace
    sql = base_sql.strip().rstrip(";")
    sql_upper = sql.upper()
    
    param_name = f"_sec_{tenant_column}"
    param_dict = {param_name: active_tenant}
    
    if " WHERE " in sql_upper:
        # Wrap existing where clause inside grouping to prevent logic escape (e.g. OR injection)
        where_pos = sql_upper.find(" WHERE ")
        pre = sql[:where_pos]
        post = sql[where_pos + 7:]
        scoped_sql = f"{pre} WHERE ({post}) AND {tenant_column} = :{param_name}"
    else:
        # Check if query has ORDER BY, GROUP BY, LIMIT
        order_pos = -1
        for kw in (" ORDER BY ", " GROUP BY ", " LIMIT "):
            pos = sql_upper.find(kw)
            if pos != -1 and (order_pos == -1 or pos < order_pos):
                order_pos = pos
                
        if order_pos != -1:
            pre = sql[:order_pos]
            post = sql[order_pos:]
            scoped_sql = f"{pre} WHERE {tenant_column} = :{param_name}{post}"
        else:
            scoped_sql = f"{sql} WHERE {tenant_column} = :{param_name}"
            
    return scoped_sql, param_dict

def generate_postgres_rls_ddl(tables: List[str], tenant_col: str = "client_id") -> str:
    """
    Generates PostgreSQL Row-Level Security (RLS) migration DDL for production migration.
    """
    lines = [
        "-- AI-BS Sovereign Database Migration: PostgreSQL Row-Level Security (RLS)",
        "-- Auto-generated for Enterprise Multi-Tenant Boundary Enforcement",
        ""
    ]
    for table in tables:
        lines.append(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY;")
        lines.append(f"DROP POLICY IF EXISTS {table}_tenant_isolation ON {table};")
        lines.append(
            f"CREATE POLICY {table}_tenant_isolation ON {table}\n"
            f"    FOR ALL\n"
            f"    USING ({tenant_col} = current_setting('app.current_tenant', true))\n"
            f"    WITH CHECK ({tenant_col} = current_setting('app.current_tenant', true));\n"
        )
    return "\n".join(lines)
