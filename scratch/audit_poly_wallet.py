import urllib.request
import json

address = "0xD6277C501465CFc329D8dd429908769718aa49FA"
rpc_endpoints = [
    "https://polygon-bor-rpc.publicnode.com",
    "https://polygon-rpc.com",
    "https://rpc.ankr.com/polygon"
]

def rpc_call(method, params):
    payload = json.dumps({"jsonrpc": "2.0", "method": method, "params": params, "id": 1}).encode("utf-8")
    for rpc in rpc_endpoints:
        try:
            req = urllib.request.Request(rpc, data=payload, headers={"Content-Type": "application/json", "User-Agent": "AI-BS/1.0"})
            with urllib.request.urlopen(req, timeout=5) as resp:
                data = json.loads(resp.read().decode())
                if "result" in data:
                    return data["result"]
        except Exception as e:
            continue
    return None

# 1. Native POL balance
bal_hex = rpc_call("eth_getBalance", [address, "latest"])
pol_bal = int(bal_hex, 16) / 1e18 if bal_hex else 0.0

# 2. Transaction Count (Nonce)
tx_count_hex = rpc_call("eth_getTransactionCount", [address, "latest"])
tx_count = int(tx_count_hex, 16) if tx_count_hex else 0

# 3. Code (to check if it's a smart contract or EOA wallet)
code_hex = rpc_call("eth_getCode", [address, "latest"])
is_contract = code_hex != "0x" and code_hex is not None

# 4. USDC Balance
# ERC-20 balanceOf(address) signature: 0x70a08231 + 12 zero bytes + address
usdc_contract = "0x3c499c542cEF5E3811e1192ce70d8cC03d5c3359"
data_payload = "0x70a08231000000000000000000000000" + address[2:].lower()
usdc_hex = rpc_call("eth_call", [{"to": usdc_contract, "data": data_payload}, "latest"])
usdc_bal = int(usdc_hex, 16) / 1e6 if usdc_hex and usdc_hex != "0x" else 0.0

# 5. USDT Balance
usdt_contract = "0xc2132D05D31c914a87C6611C10748AEb04B58e8F"
usdt_hex = rpc_call("eth_call", [{"to": usdt_contract, "data": data_payload}, "latest"])
usdt_bal = int(usdt_hex, 16) / 1e6 if usdt_hex and usdt_hex != "0x" else 0.0

print(f"ADDRESS: {address}")
print(f"ACCOUNT TYPE: {'Smart Contract' if is_contract else 'Standard Wallet (EOA)'}")
print(f"TOTAL TRANSACTIONS SENT: {tx_count}")
print(f"POL (NATIVE GAS) BALANCE: {pol_bal:.6f} POL")
print(f"USDC BALANCE: {usdc_bal:.6f} USDC")
print(f"USDT BALANCE: {usdt_bal:.6f} USDT")
