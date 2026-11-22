import urllib.request
import json

for port in [8000, 8080]:
    url = f"http://127.0.0.1:{port}/api/accounting/crypto-transfers"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "AI-BS-Verification/1.0"})
        with urllib.request.urlopen(req, timeout=3) as resp:
            data = json.loads(resp.read().decode())
            print(f"PORT {port} 200 OK: Status={data.get('status')}, Transferred=${data.get('total_transferred_usd')}, PayoutDest={data.get('payout_dest_wallet')}, SoFi={data.get('sofi_linked_account')}")
    except Exception as e:
        print(f"PORT {port} error: {e}")
