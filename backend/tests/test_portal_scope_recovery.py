"""Synthetic HTTP scope regressions; no provider, database, or live login calls.

Firebase SDK admission is disabled for this fixture. A separate configured
synthetic administrator key exercises the positive administrator guard path.
"""
import hashlib
import json
import sys
from pathlib import Path

import pytest
from fastapi import APIRouter, Depends, FastAPI
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from security import fe_express_access as fe
from security import firebase_auth
from security import website_phone_access as website
from security.auth_guard import verify_admin_key
from security.recdebut_access import require_recdebut_access


@pytest.fixture
def scoped_app(tmp_path, monkeypatch):
    salt = bytes(range(32))
    config = tmp_path / "synthetic_website_access.json"
    config.write_text(json.dumps({
        "salt": salt.hex(),
        "iterations": 600000,
        "digest": hashlib.pbkdf2_hmac(
            "sha256", b"+12025550123\x006789", salt, 600000
        ).hex(),
    }), encoding="utf-8")
    store = website.WebsiteSessions(config, lambda: 100.0)
    monkeypatch.setattr(website, "sessions", store)
    monkeypatch.setenv("AI_BS_ADMIN_KEY", "synthetic-scope-test-admin")
    monkeypatch.setattr(firebase_auth, "id_token", None)

    app = FastAPI()
    app.include_router(website.router)
    fe_router = APIRouter(prefix=fe.PREFIX, dependencies=[Depends(fe.require_fe_express_access)])

    @fe_router.get("/scope-test")
    def fe_view():
        return {"workspace": "fe_express"}

    app.include_router(fe_router)
    rec_router = APIRouter(dependencies=[Depends(require_recdebut_access)])

    @rec_router.get("/private-scope-test")
    def rec_view():
        return {"workspace": "recdebut"}

    app.include_router(rec_router, prefix="/api/v1/recdebut")
    app.include_router(rec_router, prefix="/api/recdebut")

    @app.get("/admin-scope-test", dependencies=[Depends(verify_admin_key)])
    def admin_view():
        return {"administrator": True}

    with TestClient(app) as client:
        response = client.post("/api/website-access/login", json={
            "phone": "2025550123", "pin": "6789",
        })
        assert response.status_code == 200
        assert response.json()["scope"] == "website_pages"
        headers = {"Authorization": "Bearer " + response.json()["access_token"]}
        yield client, headers


@pytest.mark.parametrize("path", [
    "/api/v1/recdebut/private-scope-test",
    "/api/recdebut/private-scope-test",
    "/admin-scope-test",
])
def test_phone_pin_session_is_denied_by_real_protected_guards(scoped_app, path):
    client, portal_headers = scoped_app
    assert client.get(path, headers=portal_headers).status_code == 403
    assert client.get(path, headers={"X-Admin-Key": "synthetic-scope-test-admin"}).status_code == 200


def test_same_portal_session_opens_fe_and_logout_revokes_it(scoped_app):
    client, portal_headers = scoped_app
    path = fe.PREFIX + "/scope-test"
    assert client.get(path).status_code == 401
    assert client.get(path, headers=portal_headers).status_code == 200
    assert client.post("/api/website-access/logout", headers=portal_headers).status_code == 200
    assert client.get(path, headers=portal_headers).status_code == 401
