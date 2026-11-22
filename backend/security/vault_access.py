"""Administrator authorization for credential vaults and database inspection."""
import asyncio

from fastapi import HTTPException, Request

from security.firebase_auth import verify_admin_credentials


PREFIXES = (
    "/api/vault", "/v1/vault", "/v1/api/vault", "/api/v1/vault",
    "/api/v1/api/vault", "/api/v1/vaults", "/api/vaults",
    "/v1/vaults", "/v1/api/vaults",
)


def is_vault_path(path: str) -> bool:
    path = path.lower().rstrip("/")
    return any(path == prefix or path.startswith(prefix + "/") for prefix in PREFIXES)


async def require_vault_access(request: Request):
    key = request.headers.get("x-admin-key", "") or request.headers.get("x-api-key", "")
    authorization = request.headers.get("authorization", "")
    if not await asyncio.to_thread(verify_admin_credentials, key, authorization):
        raise HTTPException(403, "Administrator authorization is required for vault access.")
