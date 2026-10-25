"""
Cryptographic Admin Bearer Token & Route Guard (v5.129.0)
Protects administrative, compute, and daemon management routes.
"""

import os
from fastapi import Header, HTTPException, Request, Depends
from security.firebase_auth import verify_admin_credentials

# Load or generate stable pre-shared admin key
DEFAULT_ADMIN_KEY = os.getenv("AI_BS_ADMIN_KEY", "")

def verify_admin_key(
    request: Request,
    x_admin_key: str = Header(None, alias="X-Admin-Key"),
    authorization: str = Header(None)
):
    """
    Verifies administrative authorization key on protected endpoints.
    Requires the configured admin key on every request.
    """
    provided_key = x_admin_key or request.headers.get("x-api-key", "")
    if verify_admin_credentials(provided_key, authorization or request.headers.get("authorization", "")):
        return True


    raise HTTPException(
        status_code=403,
        detail="Forbidden: Administrative privileges or valid X-Admin-Key header required."
    )
