"""Side-effect-free shared FE Express capacity and trip scoring."""
import math
from typing import Dict, Any

class FilterScoringEngine:
    @staticmethod
    def classify_equipment(equipment_str: str, weight: float = 0.0) -> Dict[str, Any]:
        """Automates classification between 24'/26' Box Truck and Cargo/Sprinter Van."""
        eq_lower = equipment_str.lower()

        # Strict 53' semi or large flatbed rejection keywords
        semi_keywords = ["53'", "semi", "tractor", "double drop", "heavy haul", "lowboy"]
        is_semi = any(s in eq_lower for s in semi_keywords) and not any(k in eq_lower for k in ["box", "van", "straight"])

        # Van classification (Sprinter, Cargo Van, Transit, Cargo, Light partial under 4500 lbs)
        van_keywords = ["cargo van", "sprinter", "van", "transit", "promaster", "cube van"]
        # Box Truck classification (24ft, 26ft, straight truck, box, boxtruck)
        box_keywords = ["24'", "26'", "box truck", "straight truck", "boxtruck", "box", "straight"]

        is_van = any(v in eq_lower for v in van_keywords) and not any(b in eq_lower for b in ["53'", "dry van", "reefer"])
        is_box = any(b in eq_lower for b in box_keywords) and not is_semi

        # Hotshot / Flatbed partials that fit box or van capacity
        if not is_van and not is_box and not is_semi:
            if "hotshot" in eq_lower or "partial" in eq_lower:
                if weight > 0 and weight <= 4500:
                    is_van = True
                elif weight > 0 and weight <= 10000:
                    is_box = True

        vehicle_type = "UNKNOWN"
        if is_box:
            vehicle_type = "BOX_TRUCK"
        elif is_van:
            vehicle_type = "CARGO_VAN"

        return {
            "is_box_truck": is_box,
            "is_cargo_van": is_van,
            "vehicle_type": vehicle_type,
            "is_semi_rejected": is_semi
        }

    @classmethod
    def evaluate(cls, load: Dict[str, Any], min_greenlight_rpm: float = 2.50, min_caution_rpm: float = 2.00, max_weight: float = 10000.0) -> Dict[str, Any]:
        equipment = load.get("equipment_type", "")
        weight = float(load.get("weight_lbs", 0.0))
        miles = float(load.get("total_miles", 0.0))
        deadhead = float(load.get("deadhead_miles", 0.0))
        pay = float(load.get("flat_rate_pay", 0.0))

        if not all(math.isfinite(n) for n in (weight, miles, deadhead, pay)) or weight <= 0 or float(load.get("total_miles", 1.0)) <= 0 or deadhead < 0 or pay < 0:
            raise ValueError("Weight and loaded miles must be positive; deadhead and pay must be nonnegative finite numbers.")
        classification = cls.classify_equipment(equipment, weight)
        is_box = classification["is_box_truck"]
        is_van = classification["is_cargo_van"]
        vehicle_type = classification["vehicle_type"]

        # Capacity thresholds: Box truck <= 10,000 lbs, Cargo Van <= 4,500 lbs
        under_weight = (is_box and weight <= max_weight) or (is_van and weight <= 4500.0)

        rpm = round(pay / miles, 2)
        true_miles = miles + deadhead
        true_rpm = round(pay / true_miles, 2)

        matched_fleet = is_box or is_van

        eq_lower = equipment.lower()
        requires_liftgate = any(k in eq_lower for k in ("liftgate", "lift gate", "lift-gate", "lg req", "needs lg")) and not any(k in eq_lower for k in ("no liftgate", "no lift gate", "no lift-gate"))
        if not matched_fleet or not under_weight or classification["is_semi_rejected"] or requires_liftgate:
            score = "Reject"
            tier = 3
        elif true_rpm >= min_greenlight_rpm:
            score = "Greenlight"
            tier = 1
        elif true_rpm >= min_caution_rpm:
            score = "Caution"
            tier = 2
        else:
            score = "Reject"
            tier = 3

        evaluated = dict(load)
        evaluated["rpm"] = rpm
        evaluated["true_rpm"] = true_rpm
        evaluated["score"] = score
        evaluated["priority_tier"] = tier
        evaluated["is_valid_box_truck"] = is_box
        evaluated["is_valid_cargo_van"] = is_van
        evaluated["vehicle_match"] = vehicle_type
        evaluated["under_weight_limit"] = under_weight
        evaluated["requires_liftgate"] = requires_liftgate
        return evaluated

