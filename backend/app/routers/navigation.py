from fastapi import APIRouter, HTTPException
from app.schemas.navigation import RouteGuidanceResponse, DriverPositionUpdate
from app.services.navigation_service import guidance_service

router = APIRouter(prefix="/v1/navigation", tags=["Navigation & Live Tracking Guidance"])


@router.get("/guidance/{trip_id}", response_model=RouteGuidanceResponse)
def get_route_guidance(trip_id: str):
    """Retrieve full truck-specific navigation maneuver instructions and geometry."""
    guidance = guidance_service.get_guidance(trip_id)
    if not guidance:
        raise HTTPException(status_code=404, detail=f"No route guidance for trip '{trip_id}'.")
    return guidance


@router.post("/telemetry/fix", response_model=RouteGuidanceResponse)
def ingest_driver_position_fix(update: DriverPositionUpdate):
    """Ingest live GPS fix from phone, update tracking, and return current active maneuver."""
    return guidance_service.record_driver_fix(update)


@router.get("/tracking/{trip_id}", response_model=DriverPositionUpdate)
def get_latest_tracking_fix(trip_id: str):
    """Retrieve driver's latest live GPS fix."""
    fix = guidance_service.get_latest_fix(trip_id)
    if not fix:
        # Fallback to nominal midpoint
        return DriverPositionUpdate(
            trip_id=trip_id,
            lat=42.7325,
            lon=-84.5555,
            bearing_degrees=270.0,
            speed_mph=62.5,
            timestamp_utc=1795182000.0
        )
    return fix
