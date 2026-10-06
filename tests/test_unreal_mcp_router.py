import sys
import os
import pytest
from fastapi.testclient import TestClient
from fastapi import FastAPI

# Ensure root and backend are on sys.path
_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_backend = os.path.join(_root, "backend")
if _root not in sys.path:
    sys.path.insert(0, _root)
if _backend not in sys.path:
    sys.path.insert(0, _backend)

from backend.routers.unreal_mcp_router import router as unreal_router

@pytest.fixture
def client():
    app = FastAPI()
    app.include_router(unreal_router)
    return TestClient(app)

def test_unreal_status_endpoint(client):
    response = client.get("/api/v1/unreal/status")
    assert response.status_code == 200
    data = response.json()
    assert "unreal_editor_running" in data
    assert "mcp_server_online" in data
    assert data["mcp_url"] == "http://127.0.0.1:8000/mcp"
    assert data["engine_version"] == "Unreal Engine 5.8"
    assert "recommended_action" in data

def test_unreal_assets_catalog(client):
    response = client.get("/api/v1/unreal/assets?limit=10")
    assert response.status_code == 200
    data = response.json()
    assert "total_matched" in data
    assert "returned" in data
    assert "categories" in data
    assert "results" in data
    assert isinstance(data["results"], list)

def test_unreal_assets_filtering(client):
    response = client.get("/api/v1/unreal/assets?query=camera&limit=5")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data["results"], list)

def test_unreal_rpc_fallback_when_offline(client):
    payload = {
        "method": "ping",
        "params": {}
    }
    response = client.post("/api/v1/unreal/rpc", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert "success" in data
    if not data["success"]:
        assert data.get("fallback_available") is True

def test_unreal_spawn_camera_endpoint(client):
    payload = {
        "camera_name": "Test_CineCamera",
        "location": [100.0, 200.0, 300.0],
        "rotation": [0.0, 45.0, 0.0],
        "focal_length": 50.0
    }
    response = client.post("/api/v1/unreal/camera/spawn", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert "success" in data

def test_unreal_sequencer_trigger_endpoint(client):
    payload = {
        "sequence_path": "/Game/Cinematics/Shot01",
        "action": "play"
    }
    response = client.post("/api/v1/unreal/sequencer/trigger", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert "success" in data
