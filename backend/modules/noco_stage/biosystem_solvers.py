"""
Project NoCo Biosystem Computational Solvers (Roles 34, 35, 40)
Precision Math Engines for 23-Acre Campus:
- hydro_nutrient_solver (Role 34)
- microgrid_load_sim    (Role 35)
- noco_capex_estimator  (Role 40)
"""

from typing import Dict, Any, List, Optional
import math
import copy


def _finite(value: float, name: str, minimum: float = 0.0, maximum: Optional[float] = None,
            positive: bool = False) -> None:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise ValueError(f"{name} must be finite.")
    if value < minimum or (positive and value <= minimum) or (maximum is not None and value > maximum):
        raise ValueError(f"{name} is outside the supported model range.")

# Standard Optimal Targets by Crop Type
CROP_NUTRIENT_TARGETS = {
    "leafy_greens": {"target_ec": 1.4, "target_ph": 5.8, "ratio_a_b": 1.0},
    "tomatoes_flowering": {"target_ec": 2.2, "target_ph": 6.2, "ratio_a_b": 1.2},
    "strawberries": {"target_ec": 1.0, "target_ph": 5.7, "ratio_a_b": 0.9},
    "culinary_herbs": {"target_ec": 1.2, "target_ph": 6.0, "ratio_a_b": 1.0},
    "default": {"target_ec": 1.6, "target_ph": 6.0, "ratio_a_b": 1.0},
}


class HydroNutrientSolver:
    """Calculates dosing requirements for CEA closed-loop hydroponics."""

    @staticmethod
    def calculate_dosing(
        current_ec: float,
        current_ph: float,
        water_volume_liters: float,
        crop_type: str = "leafy_greens",
        target_ec_override: Optional[float] = None,
        target_ph_override: Optional[float] = None,
    ) -> Dict[str, Any]:
        _finite(current_ec, 'current_ec')
        _finite(current_ph, 'current_ph', maximum=14.0)
        _finite(water_volume_liters, 'water_volume_liters', positive=True)
        if target_ec_override is not None:
            _finite(target_ec_override, 'target_ec_override', positive=True)
        if target_ph_override is not None:
            _finite(target_ph_override, 'target_ph_override', maximum=14.0)
        targets = CROP_NUTRIENT_TARGETS.get(crop_type.lower(), CROP_NUTRIENT_TARGETS["default"])
        target_ec = target_ec_override if target_ec_override is not None else targets["target_ec"]
        target_ph = target_ph_override if target_ph_override is not None else targets["target_ph"]

        ec_delta = target_ec - current_ec
        # Formula: 1.0 mS/cm EC delta across 1000L requires ~1,000 ml of standard concentrated 100x Stock
        # (1 ml per liter per 1.0 EC)
        if ec_delta > 0:
            total_stock_ml = ec_delta * water_volume_liters * 1.0
            dose_part_a_ml = round(total_stock_ml / (1.0 + targets["ratio_a_b"]), 2)
            dose_part_b_ml = round(total_stock_ml - dose_part_a_ml, 2)
            water_topup_liters = 0.0
        elif ec_delta < -0.1:
            # Overconcentrated: dilute with fresh RO water
            dilution_factor = current_ec / target_ec
            water_topup_liters = round(water_volume_liters * (dilution_factor - 1.0), 2)
            dose_part_a_ml = 0.0
            dose_part_b_ml = 0.0
        else:
            dose_part_a_ml = 0.0
            dose_part_b_ml = 0.0
            water_topup_liters = 0.0

        # pH Correction
        ph_delta = target_ph - current_ph
        # ~1 ml of 10% phosphoric acid lowers 100L of water by ~0.1 pH unit
        if ph_delta < -0.05:
            # Current pH is too high -> Need pH Down (Phosphoric Acid)
            ph_down_ml = round(abs(ph_delta) * (water_volume_liters / 100.0) * 10.0, 2)
            ph_up_ml = 0.0
            ph_action = "DOSE_PH_DOWN"
        elif ph_delta > 0.05:
            # Current pH is too low -> Need pH Up (KOH)
            ph_up_ml = round(ph_delta * (water_volume_liters / 100.0) * 8.0, 2)
            ph_down_ml = 0.0
            ph_action = "DOSE_PH_UP"
        else:
            ph_down_ml = 0.0
            ph_up_ml = 0.0
            ph_action = "NOMINAL"

        return {
            "specialist": "hydro_nutrient_solver",
            "role_index": 34,
            "crop_type": crop_type,
            "water_volume_liters": water_volume_liters,
            "current_ec": current_ec,
            "target_ec": target_ec,
            "ec_delta": round(ec_delta, 3),
            "current_ph": current_ph,
            "target_ph": target_ph,
            "ph_delta": round(ph_delta, 3),
            "dosing_plan": {
                "nutrient_part_a_ml": dose_part_a_ml,
                "nutrient_part_b_ml": dose_part_b_ml,
                "fresh_water_dilution_liters": water_topup_liters,
                "ph_adjustment_action": ph_action,
                "ph_down_phosphoric_ml": ph_down_ml,
                "ph_up_koh_ml": ph_up_ml,
            },
            "status": "REFERENCE_MODEL",
            "model_status": "simulation_model",
            "assumptions": "Illustrative stock-strength and pH-response constants; not field-calibrated dosing instructions.",
        }


class MicrogridLoadSim:
    """Hour-by-hour simulation of 500 kWh BESS battery storage, solar production, and living campus loads."""

    @staticmethod
    def simulate_24h_cycle(
        solar_capacity_kw: float = 150.0,
        battery_capacity_kwh: float = 500.0,
        initial_battery_kwh: float = 350.0,
        base_campus_load_kw: float = 45.0,
        stage_event_load_kw: float = 85.0,
        stage_active_hours: Optional[List[int]] = None,
    ) -> Dict[str, Any]:
        _finite(solar_capacity_kw, 'solar_capacity_kw')
        _finite(battery_capacity_kwh, 'battery_capacity_kwh', positive=True)
        _finite(initial_battery_kwh, 'initial_battery_kwh', maximum=battery_capacity_kwh)
        _finite(base_campus_load_kw, 'base_campus_load_kw')
        _finite(stage_event_load_kw, 'stage_event_load_kw')
        stage_active_hours = [19, 20, 21, 22] if stage_active_hours is None else stage_active_hours
        if not isinstance(stage_active_hours, (list, tuple)) or any(
            isinstance(h, bool) or not isinstance(h, int) or not 0 <= h < 24 for h in stage_active_hours):
            raise ValueError('Stage hours must be integers between 0 and 23.')
        hourly_records = []
        current_battery = initial_battery_kwh
        total_solar_generated = 0.0
        total_load_consumed = 0.0
        generator_backup_kwh = 0.0

        # Typical Michigan Solar Insolation curve across 24h
        sunlight_factors = [
            0.0, 0.0, 0.0, 0.0, 0.0, 0.0,
            0.05, 0.20, 0.50, 0.75, 0.90, 1.00,
            0.95, 0.85, 0.65, 0.40, 0.15, 0.05,
            0.0, 0.0, 0.0, 0.0, 0.0, 0.0,
        ]

        for hour in range(24):
            solar_in = solar_capacity_kw * sunlight_factors[hour]
            load_demand = base_campus_load_kw + (stage_event_load_kw if hour in stage_active_hours else 0.0)

            net_flow = solar_in - load_demand
            total_solar_generated += solar_in
            total_load_consumed += load_demand

            if net_flow > 0:
                # Excess solar charges battery
                chargable = battery_capacity_kwh - current_battery
                charging = min(net_flow, chargable)
                current_battery += charging
                curtailed = net_flow - charging
                gen_needed = 0.0
            else:
                # Deficit draws from battery
                needed = abs(net_flow)
                discharged = min(needed, current_battery)
                current_battery -= discharged
                deficit = needed - discharged
                curtailed = 0.0
                gen_needed = deficit
                generator_backup_kwh += deficit

            hourly_records.append({
                "hour": hour,
                "solar_kw": round(solar_in, 1),
                "load_kw": round(load_demand, 1),
                "battery_kwh": round(current_battery, 1),
                "battery_soc_pct": round((current_battery / battery_capacity_kwh) * 100.0, 1),
                "backup_gen_kwh": round(gen_needed, 1),
                "curtailed_kw": round(curtailed, 1),
            })

        min_soc = min(h["battery_soc_pct"] for h in hourly_records)
        return {
            "specialist": "microgrid_load_sim",
            "role_index": 35,
            "battery_capacity_kwh": battery_capacity_kwh,
            "total_solar_generated_kwh": round(total_solar_generated, 1),
            "total_load_consumed_kwh": round(total_load_consumed, 1),
            "generator_backup_kwh": round(generator_backup_kwh, 1),
            "grid_independence_pct": None if total_load_consumed == 0 else round(
                ((total_load_consumed - generator_backup_kwh) / total_load_consumed) * 100.0, 1
            ),
            "minimum_soc_pct": min_soc,
            "hours_simulated": 24,
            "sample_snapshot_noon": hourly_records[12],
            "sample_snapshot_evening_stage": hourly_records[20],
            "model_status": "simulation_model",
            "assumptions": "Fixed illustrative 24-hour solar/load curve and ideal battery; no measured hardware telemetry or efficiency losses.",
        }


class NoCoCapexEstimator:
    """CAPEX budget and material sizing calculator for campus modules."""

    BASE_CAPEX_ITEMS = [
        {"item": "150 kW Commercial Ground-Mount Solar Array", "unit_cost": 165000, "qty": 1, "category": "Energy"},
        {"item": "500 kWh LiFePO4 BESS Containerized Storage", "unit_cost": 210000, "qty": 1, "category": "Energy"},
        {"item": "High-Tunnel Automated CEA Greenhouse (30x100ft)", "unit_cost": 48000, "qty": 2, "category": "Agriculture"},
        {"item": "Koi Aquaculture Closed Water Reclaim Loop", "unit_cost": 32000, "qty": 1, "category": "Water"},
        {"item": "Living Stage Curved Acoustic Shell & DMX Lighting", "unit_cost": 75000, "qty": 1, "category": "Stage"},
        {"item": "Private Fiber & LoRaWAN Sensor Mesh (23 Acres)", "unit_cost": 22000, "qty": 1, "category": "IT"},
    ]

    @classmethod
    def generate_capex_summary(cls) -> Dict[str, Any]:
        items = copy.deepcopy(cls.BASE_CAPEX_ITEMS)
        total = sum(i["unit_cost"] * i["qty"] for i in items)
        by_cat = {}
        for i in items:
            cat = i["category"]
            by_cat[cat] = by_cat.get(cat, 0) + (i["unit_cost"] * i["qty"])
        return {
            "specialist": "noco_capex_estimator",
            "role_index": 40,
            "campus_acres": 23.0,
            "total_capex_usd": total,
            "category_breakdown": by_cat,
            "line_items": items,
            "model_status": "reference_estimate",
            "assumptions": "Illustrative catalog prices; not supplier quotes or a financial commitment.",
        }
