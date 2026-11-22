"""
FE Express — Secondary Load Board Connectors & Adapters
Provides normalized ingestion adapters for:
  1. Trulos Public Real-Time API (Nationwide Live Board)
  2. DAT One / Freight Automation Format Adapter
  3. Truckstop.com Integration & CSV/JSON Relay
  4. 123Loadboard & Hotshot/Box Truck Direct Parser
"""

import re
import json
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime

logger = logging.getLogger("FE_LoadBoardAdapters")

class NormalizedLoad:
    @staticmethod
    def create(
        load_id: str,
        source: str,
        origin: str,
        destination: str,
        equipment: str,
        weight_lbs: float,
        miles: float,
        pay: float,
        broker_name: str,
        broker_phone: str = "",
        broker_email: str = "",
        pickup_date: str = ""
    ) -> Dict[str, Any]:
        return {
            "load_id": str(load_id).strip(),
            "source": str(source).strip(),
            "origin_city_state": str(origin).strip(),
            "dest_city_state": str(destination).strip(),
            "equipment_type": str(equipment).strip(),
            "weight_lbs": float(weight_lbs),
            "total_miles": max(float(miles), 1.0),
            "flat_rate_pay": float(pay),
            "broker_name": str(broker_name).strip(),
            "broker_phone": str(broker_phone).strip(),
            "broker_email": str(broker_email).strip(),
            "pickup_date": str(pickup_date).strip()
        }

class DATOneAdapter:
    """Parses DAT One web export, webhook payloads, or API responses."""
    @classmethod
    def parse_payload(cls, data: Any) -> List[Dict[str, Any]]:
        results = []
        items = data if isinstance(data, list) else data.get("loads", data.get("results", []))
        for item in items:
            try:
                lid = item.get("id") or item.get("loadId") or item.get("referenceNumber")
                if not lid:
                    continue
                orig = f"{item.get('originCity', '')}, {item.get('originState', '')}".strip(", ")
                dest = f"{item.get('destinationCity', '')}, {item.get('destinationState', '')}".strip(", ")
                eq = item.get("equipmentType") or item.get("equipment") or "Box Truck (26')"
                wt = float(item.get("weight") or item.get("weightPounds") or 8500.0)
                miles = float(item.get("distanceMiles") or item.get("tripMiles") or item.get("miles") or 150.0)
                pay = float(item.get("rateUsd") or item.get("targetRate") or item.get("flatPay") or 0.0)
                broker = item.get("companyName") or item.get("broker") or "DAT Broker"
                phone = item.get("contactPhone") or item.get("phone") or ""
                email = item.get("contactEmail") or item.get("email") or ""
                
                results.append(NormalizedLoad.create(
                    load_id=f"DAT-{lid}",
                    source="DAT One Adapter",
                    origin=orig,
                    destination=dest,
                    equipment=eq,
                    weight_lbs=wt,
                    miles=miles,
                    pay=pay,
                    broker_name=broker,
                    broker_phone=phone,
                    broker_email=email
                ))
            except Exception as e:
                logger.warning(f"Error parsing DAT item: {e}")
        return results

class TruckstopAdapter:
    """Parses Truckstop.com API / webhook JSON payloads."""
    @classmethod
    def parse_payload(cls, data: Any) -> List[Dict[str, Any]]:
        results = []
        items = data if isinstance(data, list) else data.get("loadList", data.get("loads", []))
        for item in items:
            try:
                lid = item.get("loadId") or item.get("id") or item.get("postingId")
                if not lid:
                    continue
                orig = f"{item.get('origin', {}).get('city', '')}, {item.get('origin', {}).get('state', '')}".strip(", ")
                if not orig or orig == ",":
                    orig = str(item.get("originLocation") or "Chicago, IL")
                dest = f"{item.get('destination', {}).get('city', '')}, {item.get('destination', {}).get('state', '')}".strip(", ")
                if not dest or dest == ",":
                    dest = str(item.get("destinationLocation") or "Detroit, MI")
                
                eq = item.get("equipmentType") or "Straight Truck"
                wt = float(item.get("weight") or 9000.0)
                miles = float(item.get("miles") or item.get("totalMileage") or 200.0)
                pay = float(item.get("rate") or item.get("grossPay") or 0.0)
                broker = item.get("broker", {}).get("companyName") or item.get("company") or "Truckstop Broker"
                phone = item.get("broker", {}).get("phone") or item.get("contactPhone") or ""
                email = item.get("broker", {}).get("email") or item.get("contactEmail") or ""
                
                results.append(NormalizedLoad.create(
                    load_id=f"TS-{lid}",
                    source="Truckstop.com Adapter",
                    origin=orig,
                    destination=dest,
                    equipment=eq,
                    weight_lbs=wt,
                    miles=miles,
                    pay=pay,
                    broker_name=broker,
                    broker_phone=phone,
                    broker_email=email
                ))
            except Exception as e:
                logger.warning(f"Error parsing Truckstop item: {e}")
        return results
