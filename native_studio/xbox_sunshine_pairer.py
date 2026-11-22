import sys
import time
import requests
import urllib3
urllib3.disable_warnings()

SUNSHINE_URL = "https://localhost:49001"
AUTH = ("admin", "admin")

def get_pending_pairings():
    try:
        r = requests.get(f"{SUNSHINE_URL}/api/pin", auth=AUTH, verify=False, timeout=3)
        if r.status_code == 200:
            return r.json().get("pairings", [])
    except Exception as e:
        print(f"[-] Error connecting to Sunshine: {e}")
    return []

def submit_pin(pin: str, pairing_id: str = None) -> bool:
    pairings = get_pending_pairings()
    if not pairing_id:
        if pairings:
            pairing_id = pairings[0].get("id") or pairings[0].get("pairing_id")
            print(f"[*] Found active pairing request for client: {pairings[0].get('name', 'Xbox')} (ID: {pairing_id})")
        else:
            print("[-] No pending pairing request found in Sunshine yet.")
            print("    Please click on your PC inside Moonlight on the Xbox TV first!")
            return False

    client_name = pairings[0].get("name", "Xbox One")
    payload = {"pin": pin, "pairing_id": pairing_id, "name": client_name}

    try:
        r = requests.post(f"{SUNSHINE_URL}/api/pin", auth=AUTH, json=payload, verify=False, timeout=5)
        if r.status_code == 200:
            print(f"[+] SUCCESS! Xbox Moonlight paired successfully with Sunshine!")
            return True
        else:
            print(f"[-] Pairing failed: HTTP {r.status_code} - {r.text}")
            return False
    except Exception as e:
        print(f"[-] Network error submitting PIN: {e}")
        return False

if __name__ == "__main__":
    if len(sys.argv) > 1:
        pin = sys.argv[1].strip()
        submit_pin(pin)
    else:
        print("Checking pending Moonlight pairing requests in Sunshine...")
        pairings = get_pending_pairings()
        print(f"Pending pairings: {pairings}")
        if not pairings:
            print("\nTo pair:")
            print("1. On Xbox TV in Moonlight, click Add Host and enter: 192.168.10.1:49000")
            print("2. Click on the PC tile in Moonlight.")
            print("3. When the 4-digit PIN appears on your TV screen, run:")
            print("   python xbox_sunshine_pairer.py <PIN>")
