import os
import re
import sqlite3
import logging
from typing import List, Dict, Optional, Any
from pathlib import Path

logger = logging.getLogger("FE_Express_Backhaul")
DB_PATH = Path(r"C:\AI-BS\saved_data\fe_express.db")


class BackhaulEngine:
    @staticmethod
    def extract_state(city_state: str) -> str:
        if not city_state:
            return ""
        parts = city_state.split(",")
        if len(parts) > 1:
            return parts[-1].strip().upper()[:2]
        return ""

    @classmethod
    def find_backhauls(
        cls,
        outbound_dest: str,
        home_base: str = "Grand Rapids, MI",
        max_pickup_radius_mi: float = 120.0
    ) -> List[Dict[str, Any]]:
        """
        Finds matching return freight that picks up near the outbound destination
        and delivers towards the terminal home base or adjacent freight corridor.
        """
        dest_state = cls.extract_state(outbound_dest)
        home_state = cls.extract_state(home_base)

        conn = sqlite3.connect(str(DB_PATH))
        conn.row_factory = sqlite3.Row
        c = conn.cursor()

        # Target Midwestern return states if home_state is MI
        favorable_home_corridors = [home_state, "IN", "OH", "IL", "WI"] if home_state == "MI" else [home_state]

        c.execute("SELECT * FROM fe_express_loads")
        all_loads = [dict(r) for r in c.fetchall()]
        conn.close()

        candidates = []
        for load in all_loads:
            origin = load.get("origin_city_state", "")
            destination = load.get("dest_city_state", "")
            orig_state = cls.extract_state(origin)
            dest_st = cls.extract_state(destination)

            # Match origin state or nearby states
            origin_match = (orig_state == dest_state) or (dest_state in origin.upper())
            delivers_home = (dest_st in favorable_home_corridors) or (home_base.lower() in destination.lower())

            if origin_match and delivers_home:
                candidates.append(load)
            elif origin_match:
                # Favorable pickup near destination even if delivering elsewhere in corridor
                candidates.append(load)

        # Sort by True RPM / RPM descending
        candidates.sort(key=lambda x: float(x.get("true_rpm") or x.get("rpm") or 0.0), reverse=True)
        return candidates[:6]
