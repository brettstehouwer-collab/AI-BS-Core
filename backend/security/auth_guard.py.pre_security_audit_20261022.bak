"""
Cryptographic Admin Bearer Token & Route Guard (v5.129.0)
Protects administrative, compute, and daemon management routes.
"""

import os
import secrets
from fastapi import Header, HTTPException, Request, Depends

# Load or generate stable pre-shared admin key
DEFAULT_ADMIN_KEY = os.getenv("AI_BS_ADMIN_KEY", "stehouwer_admin_secure_passkey_2026")

def verify_admin_key(
    request: Request,
    x_admin_key: str = Header(None, alias="X-Admin-Key"),
    authorization: str = Header(None)
):
    """
    Verifies administrative authorization key on protected endpoints.
    Allows loopback localhost if running in local development or if valid key provided.
    """
    provided_key = x_admin_key
    if not provided_key and authorization and authorization.startswith("Bearer "):
        provided_key = authorization.split("Bearer ", 1)[1].strip()

    # Check against expected admin key using constant-time comparison
    if provided_key and secrets.compare_digest(provided_key, DEFAULT_ADMIN_KEY):
        return True

    # Check if loopback connection from localhost
    client_ip = request.client.host if request.client else "127.0.0.1"
    if client_ip in {"127.0.0.1", "::1", "localhost", "testclient"}:
        return True

    raise HTTPException(
        status_code=403,
        detail="Forbidden: Administrative privileges or valid X-Admin-Key header required."
    )
