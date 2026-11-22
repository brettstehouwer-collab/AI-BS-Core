import urllib.request
import json
import re

url = "https://polygonscan.com/address/0xD6277C501465CFc329D8dd429908769718aa49FA"
try:
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"})
    html = urllib.request.urlopen(req, timeout=10).read().decode('utf-8', errors='ignore')
    
    # Check for balance or transaction mentions
    bal_match = re.search(r'\$([\d\.,]+)', html)
    tx_match = re.search(r'([\d,]+)\s+transactions?', html, re.IGNORECASE)
    print("POLYGONSCAN SCRAPE:")
    print("Page Title:", re.search(r'<title>(.*?)</title>', html).group(1) if re.search(r'<title>(.*?)</title>', html) else 'N/A')
    if "There are no matching entries" in html or "No transactions found" in html or "0 txn" in html or "0 transactions" in html:
        print("Transaction Status: 0 Transactions found on Polygon.")
    else:
        print("Transactions section found.")
except Exception as e:
    print("Scrape error:", e)

# Also check Ethereum mainnet balance
eth_payload = json.dumps({"jsonrpc":"2.0","method":"eth_getBalance","params":["0xD6277C501465CFc329D8dd429908769718aa49FA", "latest"],"id":1}).encode()
try:
    req_eth = urllib.request.Request("https://eth.llamarpc.com", data=eth_payload, headers={"Content-Type": "application/json", "User-Agent": "AI-BS/1.0"})
    res = json.loads(urllib.request.urlopen(req_eth, timeout=5).read().decode())
    eth_bal = int(res.get("result", "0x0"), 16) / 1e18
    print(f"ETHEREUM MAINNET BALANCE: {eth_bal:.6f} ETH")
except Exception as e:
    print("ETH check error:", e)
