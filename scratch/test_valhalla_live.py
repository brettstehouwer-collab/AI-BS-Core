import urllib.request
import json
import sys

url = 'https://valhalla1.openstreetmap.de/route'
payload = {
    "locations": [
        {"lat": 42.9634, "lon": -85.6681, "name": "Grand Rapids Hub"},
        {"lat": 42.5803, "lon": -83.0302, "name": "Sterling Heights Terminal"}
    ],
    "costing": "truck",
    "costing_options": {
        "truck": {
            "height": 4.1148, # 13'6" Unit 274
            "width": 2.59,
            "length": 9.144,
            "weight": 11.793,
            "hazmat": False
        }
    },
    "directions_options": {
        "units": "miles",
        "language": "en-US"
    }
}

req = urllib.request.Request(
    url,
    data=json.dumps(payload).encode('utf-8'),
    headers={
        'Content-Type': 'application/json',
        'User-Agent': 'FEExpressNavigation/1.0 (Unit 274 Commercial Pilot)'
    }
)

try:
    with urllib.request.urlopen(req, timeout=15) as resp:
        data = json.loads(resp.read().decode('utf-8'))
        trip = data['trip']
        summary = trip['summary']
        leg = trip['legs'][0]
        print("=== OFFICIAL VALHALLA ENGINE: TRUCK COSTING SUCCEEDED ===")
        print(f"Status Code: {resp.status} OK")
        print(f"Total Distance: {summary['length']} miles")
        print(f"Total Transit Duration: {round(summary['time']/60.0)} minutes")
        print(f"Total Maneuvers: {len(leg['maneuvers'])}")
        print(f"Shape Polyline Nodes: {len(leg['shape'])} characters (encoded polyline6)")
        print("\n--- SAMPLE MANEUVERS WITH TRUCK INSTRUCTIONS ---")
        for idx, m in enumerate(leg['maneuvers'][:5]):
            print(f"Step {idx+1}: [{m['type']}] {m['instruction']} ({m.get('length', 0)} mi, {m.get('time', 0)}s)")
            if 'verbal_transition_alert_instruction' in m:
                print(f"   Verbal Alert: {m['verbal_transition_alert_instruction']}")
except Exception as e:
    print(f"Error querying Valhalla: {e}")
