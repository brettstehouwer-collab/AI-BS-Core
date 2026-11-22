import os
import sys

sys.stdout.reconfigure(encoding='utf-8')

_backend_dir = r"C:\AI-BS\backend"
if _backend_dir not in sys.path:
    sys.path.insert(0, _backend_dir)

from fastapi import FastAPI
from fastapi.testclient import TestClient
from routers.power_washing_router import router as power_washing_router, PRESTIGE_RIG_SPECS

app = FastAPI()
app.include_router(power_washing_router)

client = TestClient(app)

def run_tests():
    print(f"Prestige Primary Rig: {PRESTIGE_RIG_SPECS['truck_model']}")
    print(f"Direct Phone Line: {PRESTIGE_RIG_SPECS['phone']}")

    # 1. Test Telemetry Endpoint
    res = client.get("/api/powerwash/telemetry")
    print(f"\n1. GET /api/powerwash/telemetry: status {res.status_code}")
    tel = res.json()
    print(f"   Company: {tel['company_name']} ({tel['service_area']})")
    print(f"   Total Clients: {tel['total_clients']}")
    print(f"   Active Jobs: {tel['active_jobs_count']}")
    assert res.status_code == 200

    # 2. Tool 1: Surface & Chemical Ratio Estimator
    res2 = client.post("/api/powerwash/analyze_surface", json={
        "substrate_type": "vinyl",
        "contamination_type": "black_algae",
        "contamination_severity": "moderate",
        "square_footage": 2400.0,
        "story_count": 2
    })
    print(f"\n2. POST /api/powerwash/analyze_surface: status {res2.status_code}")
    surf = res2.json()
    rec = surf["recommended_recipe"]
    print(f"   Target SH: {rec['target_sh_percentage']} | Max PSI: {rec['max_safe_psi']}")
    print(f"   Nozzle: {rec['recommended_nozzle_tip']}")
    print(f"   50-Gal Mix: {rec['batch_50_gal_mix']['raw_12_5_sh_gallons']} Gal SH + {rec['batch_50_gal_mix']['water_gallons']} Gal Water")
    print(f"   Proposal: ${surf['pricing_proposal']['total_quote_price']} (Duration: {surf['pricing_proposal']['estimated_duration_hours']} hrs)")
    assert res2.status_code == 200
    assert "1.5%" in rec['target_sh_percentage']

    # 3. Tool 2: GIS Quoting Pipeline & Route Density Discount
    res3 = client.post("/api/powerwash/gis_quote", json={
        "address": "1840 Lake Michigan Dr NW, Grand Rapids, MI 49504",
        "property_type": "residential",
        "building_sqft": 2500.0,
        "roof_pitch": "8/12",
        "driveway_sqft": 950.0,
        "include_roof": True,
        "include_siding": True,
        "include_driveway": True,
        "nearby_jobs_in_zip": 2
    })
    print(f"\n3. POST /api/powerwash/gis_quote: status {res3.status_code}")
    gis = res3.json()
    print(f"   Subtotal: ${gis['subtotal']}")
    print(f"   Route Discount: {gis['route_density_discount_pct']}% ({gis['discount_reason']}) -> -${gis['discount_amount']}")
    print(f"   Final Total Quote: ${gis['final_total_quote']}")
    print(f"   SMS Preview: {gis['proposal_dispatch_sms']}")
    assert res3.status_code == 200
    assert gis['route_density_discount_pct'] == 15

    # 4. Tool 3: Route & Water Payload (GVWR) Optimizer
    res4 = client.post("/api/powerwash/route_payload", json={
        "stops_addresses": ["1840 Lake Michigan Dr NW", "4450 44th St SE", "1200 Waverly Rd"],
        "water_tank_fill_gal": 275.0,
        "sh_chemical_gal": 45.0,
        "jobs_estimated_gallons": [80.0, 140.0, 90.0]
    })
    print(f"\n4. POST /api/powerwash/route_payload: status {res4.status_code}")
    pld = res4.json()
    print(f"   Gross Vehicle Weight: {pld['total_gross_vehicle_weight_lbs']} lbs (Max Legal: {pld['legal_gvwr_limit_lbs']} lbs)")
    print(f"   GVWR Status: {pld['gvwr_status_badge']} (Margin: {pld['remaining_payload_capacity_lbs']} lbs)")
    print(f"   Water Stations Mapped: {len(pld['recommended_west_mi_fill_stations'])}")
    assert res4.status_code == 200
    assert pld['is_gvwr_compliant'] is True

    # 5. Tool 4: Weather Dispatch & Seasonal Recirculation
    res5 = client.get("/api/powerwash/weather_dispatch")
    print(f"\n5. GET /api/powerwash/weather_dispatch: status {res5.status_code}")
    wth = res5.json()
    print(f"   Temp: {wth['current_temperature_f']}°F | Wind: {wth['wind_speed_mph']} mph | Rain: {wth['precipitation_chance_pct']}%")
    print(f"   Dispatch Status: {wth['spray_dispatch_status']}")
    print(f"   Seasonal Campaigns: {len(wth['seasonal_campaigns'])}")
    assert res5.status_code == 200

    # 6. Tool 5: Commercial Fleet Wash Verification
    res6 = client.get("/api/powerwash/fleet")
    print(f"\n6. GET /api/powerwash/fleet: status {res6.status_code}")
    flt = res6.json()
    print(f"   Fleet Units Tracked: {flt['count']}")
    first_unit = flt['units'][0]
    print(f"   - {first_unit['company_name']} ({first_unit['unit_number']}) - Tier: {first_unit['wash_tier']}")
    assert res6.status_code == 200

    # Test Log Completion
    res6b = client.post("/api/powerwash/fleet_log", json={
        "unit_id": first_unit['id'],
        "unit_number": first_unit['unit_number'],
        "company_name": first_unit['company_name'],
        "wash_tier": first_unit['wash_tier'],
        "technician_name": "Prestige Lead #1",
        "gps_coords": "42.9634° N, 85.6681° W (Grand Rapids, MI)",
        "water_temp_deg_f": 140.0,
        "soap_applied": "Prestige Citrus-Foam Citrus Wash",
        "notes": "GPS verified wash record"
    })
    print(f"   POST /api/powerwash/fleet_log: status {res6b.status_code}, response: {res6b.json()['message']}")
    assert res6b.status_code == 200

    # 7. Client CRM & Job List
    res7 = client.get("/api/powerwash/clients")
    print(f"\n7. GET /api/powerwash/clients: status {res7.status_code}, count: {res7.json()['count']}")
    res8 = client.get("/api/powerwash/jobs")
    print(f"   GET /api/powerwash/jobs: status {res8.status_code}, count: {res8.json()['count']}")
    assert res7.status_code == 200
    assert res8.status_code == 200

    print("\n✅ ALL PRESTIGE MOBILE SERVICES SUITE TESTS PASSED WITH 100% SUCCESS!")

if __name__ == "__main__":
    run_tests()
