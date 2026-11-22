from enum import Enum
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
import time


class TripStatus(str, Enum):
    NO_TRIP = "NO_TRIP"
    ROUTE_PREVIEW = "ROUTE_PREVIEW"
    EN_ROUTE = "EN_ROUTE"
    APPROACHING_GATE = "APPROACHING_GATE"
    ARRIVED = "ARRIVED"
    CHECKED_IN = "CHECKED_IN"
    COMPLETED = "COMPLETED"


class MediaSessionStatus(str, Enum):
    INACTIVE = "INACTIVE"
    REQUESTED = "REQUESTED"
    CONNECTED = "CONNECTED"
    DENIED = "DENIED"


class TripEvent(BaseModel):
    event_id: str
    event_type: str
    observed_at: float = Field(default_factory=time.time)
    payload: Dict[str, Any] = Field(default_factory=dict)


class MediaSession(BaseModel):
    call_active: bool = False
    camera_active: bool = False
    call_status: MediaSessionStatus = MediaSessionStatus.INACTIVE
    camera_status: MediaSessionStatus = MediaSessionStatus.INACTIVE
    driver_consent: bool = False
    last_requested_at: Optional[float] = None
    last_connected_at: Optional[float] = None


class DestinationGate(BaseModel):
    facility_name: str
    gate_name: str
    approach_road: str
    confidence: str = "driver_reported"
    notes: Optional[str] = None
    lat: Optional[float] = None
    lon: Optional[float] = None


class TripDetail(BaseModel):
    trip_id: str
    vehicle_id: str = "Unit 274"
    driver_name: str = "Devin"
    origin: str
    destination_gate: DestinationGate
    status: TripStatus = TripStatus.NO_TRIP
    mileage_miles: float = 0.0
    elapsed_minutes: int = 0
    route_progress_pct: float = 0.0
    camera_active: bool = False
    call_active: bool = False
    media: MediaSession = Field(default_factory=MediaSession)
    events: List[TripEvent] = Field(default_factory=list)
    created_at: float = Field(default_factory=time.time)
    updated_at: float = Field(default_factory=time.time)


class TripCreateRequest(BaseModel):
    trip_id: Optional[str] = None
    vehicle_id: str = "Unit 274"
    driver_name: str = "Devin"
    origin: str
    destination_gate: DestinationGate
    status: TripStatus = TripStatus.ROUTE_PREVIEW
    mileage_miles: float = 0.0


class MediaSessionRequest(BaseModel):
    action: str  # "REQUEST_AUDIO", "JOIN_AUDIO", "LEAVE_AUDIO", "REQUEST_CAMERA", "GRANT_CAMERA", "STOP_CAMERA"
    requested_by: str = "dispatcher"  # "dispatcher" or "driver"
