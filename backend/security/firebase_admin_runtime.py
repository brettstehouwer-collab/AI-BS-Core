"""Explicit, lazy server SDK credentials; independent of user authorization.

Importing this module performs no credential reads or SDK initialization. Calling
the helper validates a private Windows Credential Manager record and constructs
only a named app. It does not contact Firebase or establish cloud permissions.
"""
from __future__ import annotations

import json
import os
import threading
import ctypes
from ctypes import wintypes
from typing import Any

CREDENTIAL_TARGET_ENV = "AI_BS_FIREBASE_ADMIN_CREDENTIAL_TARGET"
CREDENTIAL_TARGET = "AI-BS/RuntimeRecovery/FirebaseAdmin/ai-bs-dashboard/v1"
PROJECT_ID = "ai-bs-dashboard"
APP_NAME = "aibs-admin-runtime"
_TOKEN_URI = "https://oauth2.googleapis.com/token"
_lock = threading.Lock()
_app: Any = None


class _CredentialW(ctypes.Structure):
    # Native CREDENTIALW alignment; only BlobSize/Blob are inspected.
    _fields_ = [
        ("Flags", wintypes.DWORD), ("Type", wintypes.DWORD),
        ("TargetName", wintypes.LPWSTR), ("Comment", wintypes.LPWSTR),
        ("LastWritten", wintypes.FILETIME),
        ("CredentialBlobSize", wintypes.DWORD),
        ("CredentialBlob", ctypes.POINTER(ctypes.c_ubyte)),
        ("Persist", wintypes.DWORD), ("AttributeCount", wintypes.DWORD),
        ("Attributes", ctypes.c_void_p), ("TargetAlias", wintypes.LPWSTR),
        ("UserName", wintypes.LPWSTR),
    ]


class FirebaseAdminRuntimeError(RuntimeError):
    """A safe error code; never includes credential data or SDK exception text."""

    def __init__(self, code: str):
        self.code = code
        super().__init__("Firebase Admin local validation failed: " + code)


def _read_credential_blob() -> bytes:
    # Read one explicitly configured record. Never enumerate other credentials.
    # Raw Win32 preserves UTF-8 bytes; no Unicode credential-wrapper conversion.
    api = ctypes.WinDLL("Advapi32.dll", use_last_error=True)
    api.CredReadW.argtypes = [
        wintypes.LPCWSTR, wintypes.DWORD, wintypes.DWORD,
        ctypes.POINTER(ctypes.POINTER(_CredentialW)),
    ]
    api.CredReadW.restype = wintypes.BOOL
    api.CredFree.argtypes = [ctypes.c_void_p]
    api.CredFree.restype = None
    record = ctypes.POINTER(_CredentialW)()
    if not api.CredReadW(CREDENTIAL_TARGET, 1, 0, ctypes.byref(record)):
        raise FirebaseAdminRuntimeError("credential_unavailable")
    try:
        size = record.contents.CredentialBlobSize
        pointer = record.contents.CredentialBlob
        if not 0 < size < 2560 or not pointer:
            raise FirebaseAdminRuntimeError("invalid_record")
        return ctypes.string_at(pointer, size)
    finally:
        api.CredFree(record)


def _credential_info(blob: bytes) -> dict[str, Any]:
    if not isinstance(blob, bytes) or not 0 < len(blob) < 2560:
        raise FirebaseAdminRuntimeError("invalid_record")
    try:
        info = json.loads(blob.decode("utf-8"))
    except (ValueError, UnicodeError):
        raise FirebaseAdminRuntimeError("invalid_record") from None
    if not isinstance(info, dict) or info.get("type") != "service_account":
        raise FirebaseAdminRuntimeError("invalid_type")
    if info.get("project_id") != PROJECT_ID:
        raise FirebaseAdminRuntimeError("project_mismatch")
    if info.get("token_uri") != _TOKEN_URI:
        raise FirebaseAdminRuntimeError("invalid_token_uri")
    if info.get("universe_domain", "googleapis.com") != "googleapis.com":
        raise FirebaseAdminRuntimeError("invalid_universe")
    return info


def get_firebase_admin_app() -> Any:
    """Return our locally validated named app, without token refresh or RPCs.

    Credentials are read only on first successful initialization. Changes to the
    private record require an owned backend restart; no other SDK app is adopted.
    Firebase user token verification and local-admin ownership remain separate.
    """
    global _app
    target = os.environ.get(CREDENTIAL_TARGET_ENV, "")
    if not target:
        raise FirebaseAdminRuntimeError("not_configured")
    if target != CREDENTIAL_TARGET:
        raise FirebaseAdminRuntimeError("invalid_target")
    if os.environ.get("FIREBASE_PROJECT_ID", PROJECT_ID) != PROJECT_ID:
        raise FirebaseAdminRuntimeError("project_mismatch")
    with _lock:
        if _app is not None:
            return _app
        try:
            blob = _read_credential_blob()
        except Exception:
            raise FirebaseAdminRuntimeError("credential_unavailable") from None
        info = _credential_info(blob)
        try:
            import firebase_admin
            from firebase_admin import credentials

            # Certificate parses the signer locally. Explicit options prevent
            # FIREBASE_CONFIG fallback; an explicit credential prevents ADC.
            certificate = credentials.Certificate(info)
            if certificate.project_id != PROJECT_ID:
                raise FirebaseAdminRuntimeError("project_mismatch")
            app = firebase_admin.initialize_app(
                certificate, {"projectId": PROJECT_ID}, name=APP_NAME
            )
        except FirebaseAdminRuntimeError:
            raise
        except Exception:
            raise FirebaseAdminRuntimeError("certificate_or_app_invalid") from None
        _app = app
        return app


def firebase_admin_local_status() -> dict[str, Any]:
    """Initialize on explicit request and return only non-secret local status."""
    get_firebase_admin_app()
    return {
        "initialized": True,
        "app_name": APP_NAME,
        "project_id": PROJECT_ID,
        "local_validation": "passed",
        "cloud_access_verified": False,
    }
