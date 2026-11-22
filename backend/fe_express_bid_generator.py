"""
FE Express — Automated Broker Bid & Dispatch Negotiation Generator
Produces pre-filled, professional rate confirmation bid emails and SMS scripts
for Tier 1 Greenlight loads, tailored for 26' Box Trucks and Hotshots.
"""

from typing import Dict, Any
from pathlib import Path
import json

PROFILE = json.loads((Path(__file__).resolve().parents[1] / "frontend/src/config/feExpressProfile.json").read_text(encoding="utf-8"))

class BrokerBidGenerator:
    @staticmethod
    def generate_email_bid(
        load: Dict[str, Any],
        carrier_name: str = PROFILE["company"],
        carrier_mc: str = PROFILE["mc"],
        carrier_dot: str = PROFILE["usdot"],
        driver_name: str = PROFILE["name"],
        driver_phone: str = PROFILE["phone"],
        home_base: str = "Grand Rapids, MI",
        equipment_type: str = PROFILE["equipment"]
    ) -> Dict[str, str]:
        load_id = load.get("load_id", "N/A")
        origin = load.get("origin_city_state", "Origin")
        dest = load.get("dest_city_state", "Destination")
        miles = load.get("total_miles", 0)
        posted_rate = load.get("flat_rate_pay", 0)
        broker_name = load.get("broker_name", "Broker Logistics")
        
        # Suggested counter offer (+10% - 15% negotiation headroom)
        target_bid = round(posted_rate * 1.10, 2) if posted_rate > 0 else 850.00
        
        subject = f"RATE CONFIRMATION / TRUCK IN HAND: {origin} -> {dest} [{load_id}] - {carrier_name}"
        
        body = f"""Hello {broker_name} Team,

We have an empty, clean {equipment_type} ready to roll near {origin} (Home Base: {home_base}) and can lock down your load {load_id} immediately.

LOAD DETAILS:
• Origin: {origin}
• Destination: {dest}
• Trip Distance: {miles} loaded miles
• Posted Pay: ${posted_rate:,.2f}
• Our All-In Rate Confirmation Bid: ${target_bid:,.2f} (Clean rate, no accessorials required)

EQUIPMENT SPECIFICATIONS:
• Equipment: {equipment_type}
• Capacity: Up to 10,000 lbs / 12 Standard Pallets
• Cargo Security: E-tracks, 4 load bars, 8 heavy-duty ratchet straps, moving blankets
• Insurance: $1,000,000 Auto Liability / $100,000 Cargo (Active COI ready to transmit)
• Authority: {carrier_mc} | {carrier_dot}

Can you send the rate confirmation packet to dispatch@feexpress.com or call {driver_phone} so we can assign our driver right away?

Thank you,
{driver_name}
{carrier_name}
Direct: {driver_phone}
Dispatch: dispatch@feexpress.com
"""

        # Ultra-short SMS format under 160 characters
        sms_text = (
            f"FE Express ({carrier_mc}) has a 26' box truck empty at {origin} for {load_id} ({origin}->{dest}). "
            f"Can take for ${target_bid:,.0f} all-in. Call/text {driver_phone}."
        )

        return {
            "subject": subject,
            "email_body": body,
            "sms_text": sms_text,
            "target_bid": target_bid,
            "posted_rate": posted_rate
        }
