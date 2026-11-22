import requests
import json
import time

BASE_URL = "http://127.0.0.1:8000"

def test_endpoints():
    print("Testing Screenplay Adaptation Job Management API...")

    # 1. Reset any existing job for test project
    test_proj = "Test Adaptation Project"
    r = requests.post(f"{BASE_URL}/api/screenplay/adapt/reset", json={"project_name": test_proj})
    assert r.status_code == 200, f"Reset failed: {r.text}"
    print("  [OK] POST /api/screenplay/adapt/reset succeeded.")

    # 2. Get active jobs
    r = requests.get(f"{BASE_URL}/api/screenplay/adapt/active-jobs")
    assert r.status_code == 200, f"Active jobs failed: {r.text}"
    jobs = r.json().get("jobs", {})
    print(f"  [OK] GET /api/screenplay/adapt/active-jobs returned {len(jobs)} jobs.")

    # 3. Cancel test
    r = requests.post(f"{BASE_URL}/api/screenplay/adapt/cancel", json={"project_name": test_proj})
    assert r.status_code == 200, f"Cancel failed: {r.text}"
    print("  [OK] POST /api/screenplay/adapt/cancel succeeded.")

if __name__ == "__main__":
    test_endpoints()
    print("\nALL JOB MANAGEMENT API TESTS PASSED!")
