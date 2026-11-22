import math
from typing import List, Dict, Optional
from app.schemas.navigation import (
    RouteGuidanceResponse,
    NavigationManeuver,
    TruckRestrictionProfile,
    LatLon,
    DriverPositionUpdate
)


class NavigationGuidanceService:
    def __init__(self):
        self._guidance_cache: Dict[str, RouteGuidanceResponse] = {}
        self._latest_fixes: Dict[str, DriverPositionUpdate] = {}
        self._init_michigan_corridor_route()

    def _init_michigan_corridor_route(self):
        trip_id = "TRIP-2026-DEVIN-01"
        profile = TruckRestrictionProfile(
            vehicle_type="BOX_TRUCK",
            height_feet=13.5,
            minimum_planning_clearance_feet=14.0,
            clearance_buffer_inches=6.0,
            width_feet=8.5,
            length_feet=30.0,
            weight_lbs=26000
        )

        maneuvers = [
            NavigationManeuver(
                instruction="Head west on Fort St toward I-96 West",
                verbal_transition_alert="Head west toward I-96 West",
                street_name="W Fort St",
                distance_miles=1.8,
                time_seconds=180,
                maneuver_type="DEPART",
                point=LatLon(lat=42.3314, lon=-83.0458)
            ),
            NavigationManeuver(
                instruction="Merge onto I-96 West toward Lansing / Grand Rapids (Truck corridor clearance 14'6\")",
                verbal_transition_alert="Merge onto I-96 West",
                street_name="I-96 W",
                distance_miles=65.4,
                time_seconds=3900,
                maneuver_type="MERGE",
                point=LatLon(lat=42.3482, lon=-83.0721)
            ),
            NavigationManeuver(
                instruction="Continue on I-96 West past Lansing corridor",
                verbal_transition_alert="Continue on I-96 West for 60 miles",
                street_name="I-96 W",
                distance_miles=62.3,
                time_seconds=3700,
                maneuver_type="CONTINUE",
                point=LatLon(lat=42.7325, lon=-84.5555)
            ),
            NavigationManeuver(
                instruction="Take exit 43A to merge onto US-131 South toward 44th St SW",
                verbal_transition_alert="In 1 mile, take exit 43A for US-131 South",
                street_name="US-131 S",
                distance_miles=16.8,
                time_seconds=1020,
                maneuver_type="TURN_RIGHT",
                point=LatLon(lat=42.9634, lon=-85.6681)
            ),
            NavigationManeuver(
                instruction="Turn right onto 44th St SW (Commercial Delivery Route)",
                verbal_transition_alert="Turn right onto 44th Street Southwest",
                street_name="44th St SW",
                distance_miles=1.7,
                time_seconds=150,
                maneuver_type="TURN_RIGHT",
                point=LatLon(lat=42.8851, lon=-85.6702)
            ),
            NavigationManeuver(
                instruction="Arrive at FE Logistics Terminal - North Shipping Gate 4 on right",
                verbal_transition_alert="Arriving at North Shipping Gate 4 on your right",
                street_name="Clay Ave / Terminal Rd",
                distance_miles=0.5,
                time_seconds=60,
                maneuver_type="ARRIVE",
                point=LatLon(lat=42.8856, lon=-85.6738)
            )
        ]

        # Generate polyline nodes
        polyline = [
            LatLon(lat=42.3314, lon=-83.0458),
            LatLon(lat=42.3482, lon=-83.0721),
            LatLon(lat=42.5000, lon=-83.4500),
            LatLon(lat=42.7325, lon=-84.5555),
            LatLon(lat=42.8500, lon=-85.2000),
            LatLon(lat=42.9634, lon=-85.6681),
            LatLon(lat=42.8851, lon=-85.6702),
            LatLon(lat=42.8856, lon=-85.6738)
        ]

        self._guidance_cache[trip_id] = RouteGuidanceResponse(
            trip_id=trip_id,
            total_distance_miles=148.5,
            total_time_minutes=150,
            truck_profile=profile,
            maneuvers=maneuvers,
            polyline_points=polyline,
            active_maneuver_index=2,  # Currently on I-96 W
            distance_to_next_maneuver_miles=42.1
        )

    def get_guidance(self, trip_id: str) -> Optional[RouteGuidanceResponse]:
        return self._guidance_cache.get(trip_id)

    def record_driver_fix(self, update: DriverPositionUpdate) -> RouteGuidanceResponse:
        self._latest_fixes[update.trip_id] = update
        guidance = self._guidance_cache.get(update.trip_id)
        if not guidance:
            self._init_michigan_corridor_route()
            guidance = self._guidance_cache[update.trip_id]

        # Update closest maneuver index
        min_dist = float('inf')
        closest_idx = 0
        for i, m in enumerate(guidance.maneuvers):
            d = math.hypot(m.point.lat - update.lat, m.point.lon - update.lon)
            if d < min_dist:
                min_dist = d
                closest_idx = i

        guidance.active_maneuver_index = closest_idx
        # Calculate approximate distance to next maneuver
        if closest_idx < len(guidance.maneuvers) - 1:
            next_m = guidance.maneuvers[closest_idx + 1]
            # 1 deg ~ 69 miles
            deg_dist = math.hypot(next_m.point.lat - update.lat, next_m.point.lon - update.lon)
            guidance.distance_to_next_maneuver_miles = round(deg_dist * 69.0, 1)

        return guidance

    def get_latest_fix(self, trip_id: str) -> Optional[DriverPositionUpdate]:
        return self._latest_fixes.get(trip_id)


# Singleton
guidance_service = NavigationGuidanceService()
