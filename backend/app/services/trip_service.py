from typing import Dict, Optional, List
import time
import uuid

from app.schemas.trip import (
    TripDetail,
    TripCreateRequest,
    TripEvent,
    TripStatus,
    MediaSessionRequest,
    MediaSessionStatus,
    DestinationGate
)


class TripService:
    def __init__(self):
        self._trips: Dict[str, TripDetail] = {}
        self._init_default_trip()

    def _init_default_trip(self):
        # Default mock active trip for Devin (Unit 274)
        default_id = "TRIP-2026-DEVIN-01"
        gate = DestinationGate(
            facility_name="FE Logistics Grand Rapids Terminal",
            gate_name="North Shipping Gate 4",
            approach_road="44th St SW & Clay Ave",
            confidence="driver_reported",
            notes="Use gate intercom 4# upon arrival. Staging area is past the security kiosk on the left.",
            lat=42.8856,
            lon=-85.6738
        )
        self._trips[default_id] = TripDetail(
            trip_id=default_id,
            vehicle_id="Unit 274",
            driver_name="Devin",
            origin="Detroit Distribution Depot",
            destination_gate=gate,
            status=TripStatus.EN_ROUTE,
            mileage_miles=148.5,
            elapsed_minutes=72,
            route_progress_pct=65.0,
            camera_active=False,
            call_active=False,
            events=[
                TripEvent(
                    event_id=str(uuid.uuid4())[:8],
                    event_type="TRIP_DISPATCHED",
                    observed_at=time.time() - 4500,
                    payload={"origin": "Detroit Distribution Depot", "vehicle": "Unit 274"}
                ),
                TripEvent(
                    event_id=str(uuid.uuid4())[:8],
                    event_type="DEPARTED",
                    observed_at=time.time() - 4320,
                    payload={"note": "Departed terminal on schedule"}
                ),
                TripEvent(
                    event_id=str(uuid.uuid4())[:8],
                    event_type="INTERSTATE_TRANSIT",
                    observed_at=time.time() - 2100,
                    payload={"corridor": "I-96 Westbound", "mile_marker": "MP 88"}
                )
            ]
        )

    def get_trip(self, trip_id: str) -> Optional[TripDetail]:
        return self._trips.get(trip_id)

    def list_trips(self) -> List[TripDetail]:
        return list(self._trips.values())

    def create_trip(self, req: TripCreateRequest) -> TripDetail:
        tid = req.trip_id or f"TRIP-{uuid.uuid4().hex[:8].upper()}"
        now = time.time()
        trip = TripDetail(
            trip_id=tid,
            vehicle_id=req.vehicle_id,
            driver_name=req.driver_name,
            origin=req.origin,
            destination_gate=req.destination_gate,
            status=req.status,
            mileage_miles=req.mileage_miles,
            elapsed_minutes=0,
            route_progress_pct=0.0,
            created_at=now,
            updated_at=now,
            events=[
                TripEvent(
                    event_id=str(uuid.uuid4())[:8],
                    event_type="TRIP_INITIALIZED",
                    observed_at=now,
                    payload={"origin": req.origin, "vehicle": req.vehicle_id}
                )
            ]
        )
        self._trips[tid] = trip
        return trip

    def add_event(self, trip_id: str, event: TripEvent) -> Optional[TripDetail]:
        trip = self._trips.get(trip_id)
        if not trip:
            return None

        # Check idempotent duplicate
        if any(e.event_id == event.event_id for e in trip.events):
            return trip

        trip.events.append(event)
        trip.updated_at = time.time()

        # Update status heuristics
        if event.event_type == "APPROACHING_GATE":
            trip.status = TripStatus.APPROACHING_GATE
        elif event.event_type == "ARRIVED":
            trip.status = TripStatus.ARRIVED
        elif event.event_type == "CHECKED_IN":
            trip.status = TripStatus.CHECKED_IN
        elif event.event_type == "COMPLETED":
            trip.status = TripStatus.COMPLETED

        if "route_progress_pct" in event.payload:
            trip.route_progress_pct = float(event.payload["route_progress_pct"])
        if "elapsed_minutes" in event.payload:
            trip.elapsed_minutes = int(event.payload["elapsed_minutes"])

        return trip

    def update_media_session(self, trip_id: str, req: MediaSessionRequest) -> Optional[TripDetail]:
        trip = self._trips.get(trip_id)
        if not trip:
            return None

        now = time.time()
        action = req.action.upper()

        if action == "REQUEST_AUDIO":
            trip.media.call_status = MediaSessionStatus.REQUESTED
            trip.media.last_requested_at = now
        elif action == "JOIN_AUDIO":
            trip.media.call_status = MediaSessionStatus.CONNECTED
            trip.media.call_active = True
            trip.call_active = True
            trip.media.last_connected_at = now
        elif action == "LEAVE_AUDIO":
            trip.media.call_status = MediaSessionStatus.INACTIVE
            trip.media.call_active = False
            trip.call_active = False
        elif action == "REQUEST_CAMERA":
            trip.media.camera_status = MediaSessionStatus.REQUESTED
            trip.media.last_requested_at = now
        elif action == "GRANT_CAMERA":
            trip.media.camera_status = MediaSessionStatus.CONNECTED
            trip.media.camera_active = True
            trip.media.driver_consent = True
            trip.camera_active = True
            trip.media.last_connected_at = now
        elif action in ("STOP_CAMERA", "DENY_CAMERA"):
            trip.media.camera_status = MediaSessionStatus.DENIED if action == "DENY_CAMERA" else MediaSessionStatus.INACTIVE
            trip.media.camera_active = False
            trip.media.driver_consent = False
            trip.camera_active = False

        trip.updated_at = now
        return trip


# Singleton instance
trip_service = TripService()
