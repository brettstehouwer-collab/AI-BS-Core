import logging
from typing import Dict, Any

logger = logging.getLogger("FE_Express_SpotBenchmark")

# Regional 7-day box truck / expediter lane rate averages ($/mi)
REGIONAL_BENCHMARKS = {
    ("midwest", "midwest"): {"avg_rpm": 2.65, "low_rpm": 2.15, "high_rpm": 3.40},
    ("midwest", "south"): {"avg_rpm": 2.45, "low_rpm": 2.00, "high_rpm": 3.10},
    ("midwest", "northeast"): {"avg_rpm": 2.85, "low_rpm": 2.30, "high_rpm": 3.75},
    ("midwest", "west"): {"avg_rpm": 2.20, "low_rpm": 1.85, "high_rpm": 2.75},
    ("south", "midwest"): {"avg_rpm": 2.35, "low_rpm": 1.95, "high_rpm": 2.95},
    ("northeast", "midwest"): {"avg_rpm": 2.10, "low_rpm": 1.70, "high_rpm": 2.60},
}

STATE_REGIONS = {
    "MI": "midwest", "OH": "midwest", "IN": "midwest", "IL": "midwest", "WI": "midwest", "MN": "midwest", "MO": "midwest", "IA": "midwest",
    "TX": "south", "TN": "south", "GA": "south", "FL": "south", "NC": "south", "SC": "south", "AL": "south", "KY": "south", "LA": "south",
    "PA": "northeast", "NY": "northeast", "NJ": "northeast", "NH": "northeast", "MA": "northeast", "CT": "northeast",
    "CA": "west", "WA": "west", "CO": "west", "AZ": "west", "NV": "west", "UT": "west"
}


class LaneSpotBenchmark:
    @staticmethod
    def get_state(city_state: str) -> str:
        if not city_state:
            return "MI"
        parts = city_state.split(",")
        if len(parts) > 1:
            return parts[-1].strip().upper()[:2]
        return "MI"

    @classmethod
    def get_lane_benchmark(cls, origin: str, dest: str, current_true_rpm: float, miles: float) -> Dict[str, Any]:
        orig_st = cls.get_state(origin)
        dest_st = cls.get_state(dest)

        orig_reg = STATE_REGIONS.get(orig_st, "midwest")
        dest_reg = STATE_REGIONS.get(dest_st, "midwest")

        bench = REGIONAL_BENCHMARKS.get((orig_reg, dest_reg), {"avg_rpm": 2.50, "low_rpm": 2.00, "high_rpm": 3.20})
        avg_rpm = bench["avg_rpm"]
        high_rpm = bench["high_rpm"]
        low_rpm = bench["low_rpm"]

        # Assess position against 7-day spot market
        diff_rpm = round(current_true_rpm - avg_rpm, 2)
        if current_true_rpm >= high_rpm:
            assessment = "PREMIUM_RATE"
            negotiation_tip = "Outstanding rate above 90th percentile! Lock down rate con immediately."
            suggested_counter = None
        elif current_true_rpm >= avg_rpm:
            assessment = "ABOVE_AVERAGE"
            negotiation_tip = "Strong rate above 7-day average. Solid booking."
            suggested_counter = round((current_true_rpm + 0.15) * miles, 0)
        elif current_true_rpm >= low_rpm:
            assessment = "MARKET_AVERAGE"
            suggested_counter = round(avg_rpm * miles, 0)
            negotiation_tip = f"Average spot rate. Counter-bid at ${suggested_counter:,.0f} (${avg_rpm:.2f}/mi) to match 7-day market average."
        else:
            assessment = "BELOW_MARKET"
            suggested_counter = round(avg_rpm * miles, 0)
            negotiation_tip = f"Broker is lowballing. Counter-bid at ${suggested_counter:,.0f} (${avg_rpm:.2f}/mi) or reject load."

        return {
            "origin_state": orig_st,
            "dest_state": dest_st,
            "corridor": f"{orig_st} ➡️ {dest_st}",
            "market_avg_rpm": avg_rpm,
            "market_high_rpm": high_rpm,
            "market_low_rpm": low_rpm,
            "current_rpm": current_true_rpm,
            "diff_from_avg_rpm": diff_rpm,
            "assessment": assessment,
            "negotiation_tip": negotiation_tip,
            "suggested_counter_pay": suggested_counter
        }
