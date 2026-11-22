from fastapi import APIRouter
from pydantic import BaseModel, Field, model_validator
from typing import Dict, Any, List, Optional
import os
import sys

_backend_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _backend_dir not in sys.path:
    sys.path.insert(0, _backend_dir)

from core.aibs_event_bus import event_bus

router = APIRouter(prefix="/api/noco", tags=["Project NoCo & Living Stage Module"])

class SensorReading(BaseModel):
    zone: str # 'living_stage', 'greenhouse', 'compound'
    ambient_db: float
    soil_moisture: float
    solar_generation_kw: float

@router.get("/status")
async def get_noco_status():
    return {"module": "noco_stage", "enclave_acres": 23.0, "status": "active"}

@router.post("/telemetry")
async def record_sensor_telemetry(data: SensorReading):
    await event_bus.publish(
        "events.noco.sensor_update",
        {"zone": data.zone, "ambient_db": data.ambient_db, "solar_kw": data.solar_generation_kw},
        source="noco_module"
    )
    return {"status": "recorded", "zone": data.zone, "acoustic_db": data.ambient_db}


class HydroDosingRequest(BaseModel):
    current_ec: float = Field(ge=0, allow_inf_nan=False)
    current_ph: float = Field(ge=0, le=14, allow_inf_nan=False)
    water_volume_liters: float = Field(1000.0, gt=0, allow_inf_nan=False)
    crop_type: str = "leafy_greens"
    target_ec_override: Optional[float] = Field(None, gt=0, allow_inf_nan=False)
    target_ph_override: Optional[float] = Field(None, ge=0, le=14, allow_inf_nan=False)


class MicrogridSimRequest(BaseModel):
    solar_capacity_kw: float = Field(150.0, ge=0, allow_inf_nan=False)
    battery_capacity_kwh: float = Field(500.0, gt=0, allow_inf_nan=False)
    initial_battery_kwh: float = Field(350.0, ge=0, allow_inf_nan=False)
    base_campus_load_kw: float = Field(45.0, ge=0, allow_inf_nan=False)
    stage_event_load_kw: float = Field(85.0, ge=0, allow_inf_nan=False)

    @model_validator(mode='after')
    def validate_initial_charge(self):
        if self.initial_battery_kwh > self.battery_capacity_kwh:
            raise ValueError('Initial battery charge exceeds capacity.')
        return self


@router.post("/hydro-dosing")
async def calculate_hydro_dosing(req: HydroDosingRequest):
    """Role 34 (hydro_nutrient_solver): Computes Part A/B stock and pH buffer dosing."""
    from .biosystem_solvers import HydroNutrientSolver
    return HydroNutrientSolver.calculate_dosing(
        current_ec=req.current_ec,
        current_ph=req.current_ph,
        water_volume_liters=req.water_volume_liters,
        crop_type=req.crop_type,
        target_ec_override=req.target_ec_override,
        target_ph_override=req.target_ph_override,
    )


@router.post("/microgrid-sim")
async def simulate_microgrid(req: MicrogridSimRequest):
    """Role 35 (microgrid_load_sim): 24-hour simulation of 500 kWh BESS & solar balance."""
    from .biosystem_solvers import MicrogridLoadSim
    return MicrogridLoadSim.simulate_24h_cycle(
        solar_capacity_kw=req.solar_capacity_kw,
        battery_capacity_kwh=req.battery_capacity_kwh,
        initial_battery_kwh=req.initial_battery_kwh,
        base_campus_load_kw=req.base_campus_load_kw,
        stage_event_load_kw=req.stage_event_load_kw,
    )


@router.get("/capex-summary")
async def get_noco_capex():
    """Role 40 (noco_capex_estimator): Itemized CAPEX infrastructure budget."""
    from .biosystem_solvers import NoCoCapexEstimator
    return NoCoCapexEstimator.generate_capex_summary()

def init_module(app):
    print("[Module: NoCoStage] Initialized successfully.")
