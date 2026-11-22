from typing import List
from fastapi import APIRouter, HTTPException, Depends
from app.schemas.trip import (
    TripDetail,
    TripCreateRequest,
    TripEvent,
    MediaSessionRequest
)
from app.services.trip_service import trip_service

router = APIRouter(prefix="/v1/trips", tags=["Trips & Dispatcher"])


@router.get("", response_model=List[TripDetail])
def list_trips():
    """Retrieve all trips tracked by dispatcher."""
    return trip_service.list_trips()


@router.get("/{trip_id}", response_model=TripDetail)
def get_trip(trip_id: str):
    """Devin's primary dashboard query."""
    trip = trip_service.get_trip(trip_id)
    if not trip:
        raise HTTPException(status_code=404, detail=f"Trip '{trip_id}' not found.")
    return trip


@router.post("", response_model=TripDetail)
def create_trip(payload: TripCreateRequest):
    """Initialize a new trip."""
    return trip_service.create_trip(payload)


@router.post("/{trip_id}/events", response_model=TripDetail)
def post_trip_event(trip_id: str, event: TripEvent):
    """Idempotent driver event stream ingest (arrival, check-in, pause, etc.)."""
    updated = trip_service.add_event(trip_id, event)
    if not updated:
        raise HTTPException(status_code=404, detail=f"Trip '{trip_id}' not found.")
    return updated


@router.post("/{trip_id}/media/session", response_model=TripDetail)
def update_media_session(trip_id: str, payload: MediaSessionRequest):
    """Request/grant driver road camera & two-way voice session."""
    updated = trip_service.update_media_session(trip_id, payload)
    if not updated:
        raise HTTPException(status_code=404, detail=f"Trip '{trip_id}' not found.")
    return updated
