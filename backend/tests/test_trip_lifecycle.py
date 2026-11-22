import pytest
import time
from fastapi.testclient import TestClient

from app.main import app
from app.schemas.trip import TripStatus, MediaSessionStatus

client = TestClient(app)


def test_health_check():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "HEALTHY"


def test_trip_lifecycle_and_events():
    # 1. Query initial default trip
    trip_id = "TRIP-2026-DEVIN-01"
    res = client.get(f"/v1/trips/{trip_id}")
    assert res.status_code == 200
    trip = res.json()
    assert trip["trip_id"] == trip_id
    assert trip["driver_name"] == "Devin"
    assert trip["vehicle_id"] == "Unit 274"
    assert trip["destination_gate"]["gate_name"] == "North Shipping Gate 4"

    # 2. Ingest driver event: approaching gate
    event_payload = {
        "event_id": f"ev-{int(time.time())}-1",
        "event_type": "APPROACHING_GATE",
        "observed_at": time.time(),
        "payload": {
            "route_progress_pct": 94.5,
            "elapsed_minutes": 88,
            "distance_remaining_miles": 1.2
        }
    }
    res_ev = client.post(f"/v1/trips/{trip_id}/events", json=event_payload)
    assert res_ev.status_code == 200
    updated_trip = res_ev.json()
    assert updated_trip["status"] == TripStatus.APPROACHING_GATE.value
    assert updated_trip["route_progress_pct"] == 94.5
    assert updated_trip["elapsed_minutes"] == 88

    # 3. Idempotent check (re-posting exact same event does not duplicate)
    res_dup = client.post(f"/v1/trips/{trip_id}/events", json=event_payload)
    assert res_dup.status_code == 200
    events_count = len(res_dup.json()["events"])
    assert events_count == len(updated_trip["events"])


def test_media_session_consent():
    trip_id = "TRIP-2026-DEVIN-01"

    # 1. Request audio call
    res = client.post(
        f"/v1/trips/{trip_id}/media/session",
        json={"action": "REQUEST_AUDIO", "requested_by": "dispatcher"}
    )
    assert res.status_code == 200
    assert res.json()["media"]["call_status"] == MediaSessionStatus.REQUESTED.value

    # 2. Join audio call
    res_join = client.post(
        f"/v1/trips/{trip_id}/media/session",
        json={"action": "JOIN_AUDIO", "requested_by": "driver"}
    )
    assert res_join.status_code == 200
    assert res_join.json()["media"]["call_active"] is True
    assert res_join.json()["call_active"] is True

    # 3. Request road camera
    res_cam = client.post(
        f"/v1/trips/{trip_id}/media/session",
        json={"action": "REQUEST_CAMERA", "requested_by": "dispatcher"}
    )
    assert res_cam.status_code == 200
    assert res_cam.json()["media"]["camera_status"] == MediaSessionStatus.REQUESTED.value

    # 4. Driver grants camera consent
    res_grant = client.post(
        f"/v1/trips/{trip_id}/media/session",
        json={"action": "GRANT_CAMERA", "requested_by": "driver"}
    )
    assert res_grant.status_code == 200
    assert res_grant.json()["media"]["camera_active"] is True
    assert res_grant.json()["media"]["driver_consent"] is True
    assert res_grant.json()["camera_active"] is True

    # 5. Stop camera
    res_stop = client.post(
        f"/v1/trips/{trip_id}/media/session",
        json={"action": "STOP_CAMERA", "requested_by": "dispatcher"}
    )
    assert res_stop.status_code == 200
    assert res_stop.json()["media"]["camera_active"] is False
    assert res_stop.json()["camera_active"] is False
