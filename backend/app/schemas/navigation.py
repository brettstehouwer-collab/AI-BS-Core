from typing import List, Optional
from pydantic import BaseModel
import math


class LatLon(BaseModel):
    lat: float
    lon: float


class NavigationManeuver(BaseModel):
    instruction: str
    verbal_transition_alert: Optional[str] = None
    street_name: str
    distance_miles: float
    time_seconds: int
    maneuver_type: str  # "DEPART", "TURN_LEFT", "TURN_RIGHT", "MERGE", "CONTINUE", "ARRIVE"
    point: LatLon


class TruckRestrictionProfile(BaseModel):
    vehicle_type: str = "BOX_TRUCK"
    height_feet: float = 13.5               # Unit 274: 13'6" (4.1148m)
    minimum_planning_clearance_feet: float = 14.0  # 14'0" (4.2672m) planning threshold
    clearance_buffer_inches: float = 6.0    # 6-inch mandatory company clearance buffer
    width_feet: float = 8.5
    length_feet: float = 30.0               # Cargo body; overall length unverified
    weight_lbs: int = 26000                 # Mark rating; actual loaded weight unverified
    hazmat: bool = False
    tunnel_category: str = "NONE"


class RouteGuidanceResponse(BaseModel):
    trip_id: str
    route_version: str = "v1.0.0-p2.1"
    restriction_data_version: str = "MI-OSM-20261120-UNVERIFIED"
    selected_entrance_id: Optional[str] = "GATE-NORTH-4"
    total_distance_miles: float
    total_time_minutes: int
    truck_profile: TruckRestrictionProfile
    maneuvers: List[NavigationManeuver]
    polyline_points: List[LatLon]
    active_maneuver_index: int = 0
    distance_to_next_maneuver_miles: float = 0.0


class DriverPositionUpdate(BaseModel):
    trip_id: str
    lat: float
    lon: float
    bearing_degrees: Optional[float] = 0.0
    speed_mph: Optional[float] = 0.0
    timestamp_utc: float
