import urllib.request
import json

address = "0xD6277C501465CFc329D8dd429908769718aa49FA"
chains = {
    "Polygon": "https://polygon-bor-rpc.publicnode.com",
    "Base": "https://mainnet.base.org",
    "Arbitrum One": "https://arb1.arbitrum.io/rpc",
    "BSC": "https://bsc-dataseed.binance.org"
}

print(f"MULTI-CHAIN AUDIT FOR {address}:")
for name, rpc in chains.items():
    payload = json.dumps({"jsonrpc":"2.0","method":"eth_getBalance","params":[address, "latest"],"id":1}).encode()
    try:
        req = urllib.request.Request(rpc, data=payload, headers={"Content-Type": "application/json", "User-Agent": "AI-BS/1.0"})
        res = json.loads(urllib.request.urlopen(req, timeout=5).read().decode())
        bal = int(res.get("result", "0x0"), 16) / 1e18
        print(f"  {name}: {bal:.6f}")
    except Exception as e:
        print(f"  {name}: Error ({e})")
