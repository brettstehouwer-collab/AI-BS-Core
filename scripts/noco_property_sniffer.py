#!/usr/bin/env python3
"""
NoCo Property Sniffer & Due Diligence Condition Engine
AI-BS Sovereign Intelligence Operations Suite

Translates the 112 Due Diligence Questions into multi-factor condition scoring,
generates geo-targeted MLS/GIS search queries across Tier 1 & 2 regional hubs,
and maintains the autonomous noco_property_ledger.json.

CLI Flags:
  --audit    : Evaluates all candidate parcels, scores them against the 6 dimensions, and outputs formatted scorecards.
  --queries  : Generates and prints geo-targeted search strings and GIS queries across target hubs.
  --sync     : Synchronizes evaluated parcels into noco_property_ledger.json.
"""

import sys
import os
import json
import argparse
from datetime import datetime

# Configure UTF-8 output on Windows consoles
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

LEDGER_PATH = os.path.join(os.path.dirname(__file__), "noco_property_ledger.json")

# Candidate parcels tracked by the NoCo Living Stage acquisition team
CANDIDATE_PARCELS = [
    {
        "id": "PROP-VT-001",
        "address": "63 Big Story Ln, Grafton, VT 05146",
        "county": "Windham County, VT",
        "region_hub": "Windham_VT",
        "tier": "Tier 1 Cultural & Ecological",
        "acres": 23.0,
        "price": 595000,
        "acoustic_topography_score": 96,
        "water_rights_score": 100,
        "zoning_flexibility_score": 80,
        "industrial_shield_score": 98,
        "due_diligence_matches": [
            "Q13-16: Natural concave mountain bowl with south-facing slope",
            "Q24: Ambient noise floor <30 dBA with zero highway rumble",
            "Q25-27: Active perennial spring and crystalline brook on deed",
            "Q49: Protected by Vermont Act 250 anti-sprawl land use mandates",
            "Q105: Acquired under $26k/acre"
        ],
        "due_diligence_flags": "Verify town road winter maintenance on Big Story Ln and Act 250 cultural venue permit criteria.",
        "url": "https://www.zillow.com/homedetails/63-Big-Story-Ln-Grafton-VT-05146/2056242318_zpid/"
    },
    {
        "id": "PROP-NY-001",
        "address": "Lot #4 Hill Rd, Danby / Ithaca, NY 14850",
        "county": "Tompkins County, NY",
        "region_hub": "Tompkins_NY",
        "tier": "Tier 1 Academic & Agricultural",
        "acres": 25.0,
        "price": 172500,
        "acoustic_topography_score": 88,
        "water_rights_score": 85,
        "zoning_flexibility_score": 92,
        "industrial_shield_score": 90,
        "due_diligence_matches": [
            "Q1: Exactly 25.0 contiguous acres in sweet spot",
            "Q3: 129 ft road frontage opening to wide interior bowl",
            "Q61: Town Code § 144-202.1(B)(1)(b) ag energy exemption applies",
            "Q105: $6,900/acre exceptional baseline valuation (acquisition <$175k)",
            "Q110: 8-minute transit radius to Cornell CEA & Ithaca College Theatre"
        ],
        "due_diligence_flags": "Perform deep soil perc test for 350-occupant wetland septic system and verify driveway grade.",
        "url": "https://www.zillow.com/homedetails/LOT-4-Hill-Rd-Ithaca-NY-14850/465219664_zpid/"
    },
    {
        "id": "PROP-NY-002",
        "address": "Danby Rd 12.1-Acre Pond Parcel, Ithaca, NY 14850",
        "county": "Tompkins County, NY",
        "region_hub": "Tompkins_NY",
        "tier": "Tier 1 Academic & Agricultural",
        "acres": 12.1,
        "price": 169000,
        "acoustic_topography_score": 82,
        "water_rights_score": 95,
        "zoning_flexibility_score": 90,
        "industrial_shield_score": 80,
        "due_diligence_matches": [
            "Q1: 12.1-acre footprint inside 10-25 acre sweet spot",
            "Q28: Existing natural retention pond on parcel",
            "Q61: Tompkins rural agricultural zoning allows farm-to-table assembly",
            "Q105: $13,967/acre valuation"
        ],
        "due_diligence_flags": "Acoustic decibel test along Danby Rd corridor; wetland setback survey around pond edge.",
        "url": "https://www.zillow.com/ithaca-ny/land/"
    },
    {
        "id": "PROP-NJ-001",
        "address": "Hunterdon Ag Belt Parcel, Hunterdon County, NJ 08822",
        "county": "Hunterdon County, NJ",
        "region_hub": "Hunterdon_NJ",
        "tier": "Tier 1 Ag-Preservation & Donor Nexus",
        "acres": 15.0,
        "price": 495000,
        "acoustic_topography_score": 84,
        "water_rights_score": 90,
        "zoning_flexibility_score": 88,
        "industrial_shield_score": 95,
        "due_diligence_matches": [
            "Q1: 15.0 contiguous agricultural acres",
            "Q29: 50-year unconfined aquifer recharge security",
            "Q49: Shielded by over 110 municipal zoning bans against industrial data centers",
            "Q61: New Jersey Right to Farm Act statutory defense",
            "Q111: 1.5-hour transit radius to Manhattan philanthropic and patron base"
        ],
        "due_diligence_flags": "Verify existing Farmland Assessment tax status and local municipal assembly permit guidelines.",
        "url": "https://www.zillow.com/hunterdon-county-nj/land/"
    },
    {
        "id": "PROP-NY-003",
        "address": "0 Lower Creek Rd #36, Ithaca, NY 14850",
        "county": "Tompkins County, NY",
        "region_hub": "Tompkins_NY",
        "tier": "Tier 1 Academic & Agricultural",
        "acres": 78.5,
        "price": 700000,
        "acoustic_topography_score": 92,
        "water_rights_score": 94,
        "zoning_flexibility_score": 85,
        "industrial_shield_score": 92,
        "due_diligence_matches": [
            "Q1: 78.5-acre mega-buffer providing acoustic isolation",
            "Q25: Extensive stream and creek frontage on property",
            "Q105: Bulk wholesale pricing ($8,917/acre)",
            "Q11: High potential for agricultural cluster subdivision into separate LLC nodes"
        ],
        "due_diligence_flags": "Exceeds 25-acre sweet spot; evaluate multi-entity ownership or agricultural conservation easement carve-out.",
        "url": "https://www.zillow.com/homedetails/0-Lower-Creek-Rd-36-Ithaca-NY-14850/340762830_zpid/"
    },
    {
        "id": "PROP-NY-004",
        "address": "212 Hill Rd, Ithaca, NY 14850",
        "county": "Tompkins County, NY",
        "region_hub": "Tompkins_NY",
        "tier": "Tier 1 Academic & Agricultural",
        "acres": 12.5,
        "price": 250000,
        "acoustic_topography_score": 85,
        "water_rights_score": 86,
        "zoning_flexibility_score": 88,
        "industrial_shield_score": 86,
        "due_diligence_matches": [
            "Q1: 12.5-acre sweet spot footprint",
            "Q14: Rolling topography with elevated natural stage knoll",
            "Q105: $20,000/acre acquisition basis",
            "Q110: Direct Cornell University transit corridor"
        ],
        "due_diligence_flags": "Confirm well recharge rate (GPM) and check road speed limits.",
        "url": "https://www.zillow.com/ithaca-ny/land/"
    },
    {
        "id": "PROP-NY-005",
        "address": "75 Bush Ln, Lansing / Ithaca, NY 14882",
        "county": "Tompkins County, NY",
        "region_hub": "Tompkins_NY",
        "tier": "Tier 1 Academic & Agricultural",
        "acres": 6.97,
        "price": 549000,
        "acoustic_topography_score": 70,
        "water_rights_score": 75,
        "zoning_flexibility_score": 72,
        "industrial_shield_score": 68,
        "due_diligence_matches": [
            "Q1: 6.97 acres meets minimum 5.0 acre threshold",
            "Q25: Cayuga Lake watershed proximity"
        ],
        "due_diligence_flags": "High price per acre ($78,766/ac); suburban lake corridor traffic creates acoustic floor friction (>45 dBA).",
        "url": "https://www.zillow.com/homedetails/75-Bush-Ln-Ithaca-NY-14850/32811444_zpid/"
    },
    {
        "id": "PROP-MI-001",
        "address": "4680 Luce St Parcel C, Jenison, MI 49428",
        "county": "Ottawa County, MI",
        "region_hub": "Ottawa_MI",
        "tier": "Tier 2 Regional Base",
        "acres": 3.0,
        "price": 225000,
        "acoustic_topography_score": 55,
        "water_rights_score": 70,
        "zoning_flexibility_score": 60,
        "industrial_shield_score": 50,
        "due_diligence_matches": [
            "Q17: Prevailing southwesterly winds off Lake Michigan",
            "Q29: Abundant Great Lakes freshwater table"
        ],
        "due_diligence_flags": "Under 5-acre minimum (3.0 acres); high $75,000/acre cost; residential suburban zoning restrictions on commercial assembly.",
        "url": "https://www.zillow.com/homedetails/4680-Luce-St-Jenison-MI-49428/2056382104_zpid/"
    }
]

# Automated search matrices combining regions with NoCo criteria
SEARCH_MATRICES = [
    {
        "hub": "Tompkins County / Finger Lakes, NY",
        "municipalities": ["Ithaca", "Danby", "Lansing", "Trumansburg", "Ulysses", "Newfield", "Enfield"],
        "filters": "Acreage: 10-40 ac | Price: <$600,000 | Keywords: pond spring creek bowl agritourism",
        "key_statute": "Tompkins County Town Code § 144-202.1(B)(1)(b) Agricultural Building Energy Exemption",
        "zillow_query": "https://www.zillow.com/tompkins-county-ny/land/?searchQueryState=%7B%22filterState%22%3A%7B%22lot%22%3A%7B%22min%22%3A435600%2C%22max%22%3A1742400%7D%2C%22price%22%3A%7B%22max%22%3A600000%7D%7D%7D",
        "gis_portal": "https://www.tompkinscountyny.gov/gis"
    },
    {
        "hub": "Windham & Addison Counties, VT",
        "municipalities": ["Grafton", "Middlebury", "Townshend", "Rockingham", "Chester", "Newfane", "Ripton"],
        "filters": "Acreage: 10-35 ac | Price: <$650,000 | Keywords: spring stream mountain bowl secluded view",
        "key_statute": "Vermont Act 250 Land Use Regulations (10 V.S.A. Ch. 151) Anti-Sprawl Shield",
        "zillow_query": "https://www.zillow.com/windham-county-vt/land/?searchQueryState=%7B%22filterState%22%3A%7B%22lot%22%3A%7B%22min%22%3A435600%7D%2C%22price%22%3A%7B%22max%22%3A650000%7D%7D%7D",
        "gis_portal": "https://maps.vcgi.vermont.gov/parcelviewer/"
    },
    {
        "hub": "Hunterdon & Warren Counties, NJ",
        "municipalities": ["Kingwood", "Franklin", "Delaware Twp", "Alexandria", "East Amwell", "Hope"],
        "filters": "Acreage: 10-30 ac | Price: <$700,000 | Keywords: farmland preserved spring pond right to farm",
        "key_statute": "NJ Right to Farm Act (N.J.S.A. 4:1C-1) & 110+ Municipal Data Center Zoning Bans",
        "zillow_query": "https://www.zillow.com/hunterdon-county-nj/land/?searchQueryState=%7B%22filterState%22%3A%7B%22lot%22%3A%7B%22min%22%3A435600%7D%2C%22price%22%3A%7B%22max%22%3A700000%7D%7D%7D",
        "gis_portal": "https://njogis-newjersey.opendata.arcgis.com/"
    },
    {
        "hub": "Ottawa & Allegan Counties, MI",
        "municipalities": ["Jenison", "Georgetown Twp", "Grand Haven", "Spring Lake", "Allendale", "Zeeland"],
        "filters": "Acreage: 10-30 ac | Price: <$500,000 | Keywords: acreage ravine pond wooded agritourism",
        "key_statute": "Michigan Right to Farm Act (PA 93 of 1981) & GAAMPs (Generally Accepted Ag Practices)",
        "zillow_query": "https://www.zillow.com/ottawa-county-mi/land/?searchQueryState=%7B%22filterState%22%3A%7B%22lot%22%3A%7B%22min%22%3A435600%7D%2C%22price%22%3A%7B%22max%22%3A500000%7D%7D%7D",
        "gis_portal": "https://www.miottawa.org/Property/"
    }
]

def evaluate_property(parcel):
    """
    Evaluates a candidate parcel using the master NoCo condition scoring formula.
    Weights:
      Acoustic Topography: 25%
      Water Rights & Hydrology: 20%
      Acreage Fit: 15%
      Ag/CEA Zoning Flexibility: 15%
      Industrial / Sprawl Shield: 15%
      Price per Acre: 10%
    """
    acres = float(parcel.get("acres", 1.0))
    price = float(parcel.get("price", 0.0))
    price_per_acre = price / acres if acres > 0 else 0.0

    # Acreage Fit (15%): Sweet spot 10-25 acres (100 pts), 5-9.9 acres (75 pts), <5 or >40 acres (40 pts)
    if 10.0 <= acres <= 25.0:
        acreage_score = 100.0
    elif 5.0 <= acres < 10.0 or 25.0 < acres <= 40.0:
        acreage_score = 75.0
    else:
        acreage_score = 40.0

    # Price Score (10%): <= $30,000/ac (100 pts), <= $50,000/ac (80 pts), > $50,000/ac (50 pts)
    if price_per_acre <= 30000:
        price_score = 100.0
    elif price_per_acre <= 50000:
        price_score = 80.0
    else:
        price_score = 50.0

    acoustic_score = float(parcel.get("acoustic_topography_score", 75.0))
    water_score = float(parcel.get("water_rights_score", 75.0))
    zoning_score = float(parcel.get("zoning_flexibility_score", 75.0))
    shield_score = float(parcel.get("industrial_shield_score", 75.0))

    composite = (
        acreage_score * 0.15 +
        acoustic_score * 0.25 +
        water_score * 0.20 +
        zoning_score * 0.15 +
        shield_score * 0.15 +
        price_score * 0.10
    )

    if composite >= 85.0:
        verdict = "PRIME ACQUISITION TARGET"
    elif composite >= 70.0:
        verdict = "FEASIBLE - CONTINGENT"
    else:
        verdict = "HIGH FRICTION / REJECT"

    return {
        "price_per_acre": round(price_per_acre),
        "acreage_score": acreage_score,
        "price_score": price_score,
        "composite_score": round(composite, 1),
        "verdict": verdict
    }

def run_audit():
    print("=" * 80)
    print("🎭 NOCO LIVING STAGE & THEATER PROPERTY ACQUISITION AUDIT")
    print("Master 6-Dimension Condition Engine | Sovereign Operations")
    print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80)

    evaluated = []
    for p in CANDIDATE_PARCELS:
        res = evaluate_property(p)
        eval_p = dict(p)
        eval_p.update(res)
        evaluated.append(eval_p)

    # Sort descending by composite score
    evaluated.sort(key=lambda x: x["composite_score"], reverse=True)

    print(f"\nRANKED CANDIDATE PARCELS ({len(evaluated)} Evaluated):\n")
    print(f"{'Rank':<4} {'Property Address':<36} {'County':<18} {'Acres':<7} {'Price/Ac':<11} {'Score':<7} {'Condition Verdict'}")
    print("-" * 110)

    for idx, p in enumerate(evaluated, 1):
        verdict_icon = "🟢" if "PRIME" in p["verdict"] else ("🟡" if "FEASIBLE" in p["verdict"] else "🔴")
        print(f"#{idx:<3} {p['address'][:35]:<36} {p['county'][:17]:<18} {p['acres']:<7.1f} ${p['price_per_acre']:<10,d} {p['composite_score']:<5.1f}% {verdict_icon} {p['verdict']}")

    print("\n" + "=" * 80)
    print("DETAILED PROPERTY SCORECARDS:")
    print("=" * 80)

    for idx, p in enumerate(evaluated, 1):
        print(f"\n[#{idx}] {p['address']} ({p['county']}) - {p['verdict']}")
        print(f"     Acres: {p['acres']} ac | Asking Price: ${p['price']:,} | Price/Acre: ${p['price_per_acre']:,}/ac")
        print(f"     Dimension Scores:")
        print(f"       • Acoustic Topography (25% wt): {p['acoustic_topography_score']}/100")
        print(f"       • Water Rights & Hydrology (20% wt): {p['water_rights_score']}/100")
        print(f"       • Acreage Fit (15% wt): {p['acreage_score']}/100 ({p['acres']} ac)")
        print(f"       • Zoning Flexibility (15% wt): {p['zoning_flexibility_score']}/100")
        print(f"       • Industrial / Sprawl Shield (15% wt): {p['industrial_shield_score']}/100")
        print(f"       • Price per Acre (10% wt): {p['price_score']}/100 (${p['price_per_acre']:,}/ac)")
        print(f"     Composite Score: {p['composite_score']}%")
        print("     Matched Due Diligence Criteria:")
        for m in p.get("due_diligence_matches", []):
            print(f"       ✔ {m}")
        print(f"     Due Diligence Flags: {p.get('due_diligence_flags')}")
        print(f"     Listing / Map Feed: {p.get('url')}")

def run_queries():
    print("=" * 80)
    print("🔍 NOCO QUESTIONNAIRE-DRIVEN SEARCH MATRICES & GIS LAUNCHPAD")
    print("=" * 80)
    for m in SEARCH_MATRICES:
        print(f"\n🌐 REGIONAL HUB: {m['hub']}")
        print(f"   Target Municipalities: {', '.join(m['municipalities'])}")
        print(f"   Filtering Parameters: {m['filters']}")
        print(f"   Regulatory Shield: {m['key_statute']}")
        print(f"   Zillow Land Feed: {m['zillow_query']}")
        print(f"   County GIS Portal: {m['gis_portal']}")

def run_sync():
    print(f"Synchronizing {len(CANDIDATE_PARCELS)} candidate parcels into {LEDGER_PATH}...")
    evaluated = []
    for p in CANDIDATE_PARCELS:
        res = evaluate_property(p)
        eval_p = dict(p)
        eval_p.update(res)
        evaluated.append(eval_p)

    payload = {
        "last_updated": datetime.now().isoformat(),
        "total_parcels": len(evaluated),
        "prime_targets_count": sum(1 for p in evaluated if "PRIME" in p["verdict"]),
        "feasible_contingent_count": sum(1 for p in evaluated if "FEASIBLE" in p["verdict"]),
        "reject_count": sum(1 for p in evaluated if "REJECT" in p["verdict"]),
        "search_matrices": SEARCH_MATRICES,
        "parcels": evaluated
    }

    with open(LEDGER_PATH, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)

    print(f"✔ Successfully wrote {len(evaluated)} records to {LEDGER_PATH}.")
    print(f"✔ Prime Targets: {payload['prime_targets_count']} | Feasible: {payload['feasible_contingent_count']} | Red Flag/Reject: {payload['reject_count']}")

def main():
    parser = argparse.ArgumentParser(description="NoCo Property Sniffer & Due Diligence Condition Engine")
    parser.add_argument("--audit", action="store_true", help="Run full discovery audit & print ranked scorecards")
    parser.add_argument("--queries", action="store_true", help="Print active search queries and GIS links")
    parser.add_argument("--sync", action="store_true", help="Sync evaluated parcels to noco_property_ledger.json")

    args = parser.parse_args()

    if not (args.audit or args.queries or args.sync):
        # Default behavior: run audit and sync
        run_audit()
        run_sync()
    else:
        if args.audit:
            run_audit()
        if args.queries:
            run_queries()
        if args.sync:
            run_sync()

if __name__ == "__main__":
    main()
