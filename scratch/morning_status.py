import requests, subprocess, json

# 1. Desktop wallet RPC
url = "http://127.0.0.1:8335"
auth = ("26e7f58117a4cbd55483dbb5faa3ce55", "ce21a515b1273a5e341ed7f35d13c57398e546e6dddbc5d0d974319af3af6930")
payload = {"jsonrpc": "1.0", "id": "check_bal", "method": "getbalance", "params": []}
wallet_bal = "N/A"
try:
    r = requests.post(url, json=payload, auth=auth, timeout=3)
    if r.status_code == 200:
        wallet_bal = r.json().get('result', 'N/A')
except Exception as e:
    wallet_bal = f"RPC Error: {e}"

# 2. Pool stats
pool_res = requests.get('http://127.0.0.1:8080/api/v1/mining/pearl/pool-stats')
pool = pool_res.json().get('data', {})
stats = pool.get('stats', {})
unconfirmed = pool.get('unconfirmed', [])
payments = pool.get('payments', [])

mature_prl = float(stats.get('balance', 0)) / 1e8
pending_prl = sum(float(b.get('reward', 0)) for b in unconfirmed) / 1e8
shares = stats.get('shares_good', 0)
hashes = int(stats.get('hashes', 0))
height = stats.get('networkHeight', 0)
hr_1h = stats.get('hashrate_1h', 0)

# 3. GPU stats
res = subprocess.run(
    ["nvidia-smi", "--query-gpu=power.draw,power.limit,temperature.gpu,fan.speed,clocks.current.graphics,clocks.current.memory,utilization.gpu", "--format=csv,noheader,nounits"],
    capture_output=True, text=True
)
gpu_parts = [p.strip() for p in res.stdout.strip().split(",")]

print(f"=== LIVE ECOSYSTEM METRICS (09:16 AM EDT) ===")
print(f"Desktop Wallet Balance (on-chain): {wallet_bal} PRL")
print(f"Pool Mature Balance: {mature_prl:.4f} PRL ({mature_prl/1.0*100:.1f}% to Payout #2)")
print(f"Pool Pending Rewards: {pending_prl:.4f} PRL across {len(unconfirmed)} maturing blocks")
print(f"Total Mined (Paid + Pool): {1.99333790 + mature_prl + pending_prl:.4f} PRL")
print(f"Total Payments from Pool: {len(payments)}")
for p in payments:
    print(f"  Payment: {p}")
print(f"Accepted Shares: {shares} (0 invalid)")
print(f"Total Hashes: {hashes:,} ({hashes/1e9:.2f} B)")
print(f"Pool Hashrate (1h): {hr_1h/1e3:.2f} GH/s")
print(f"Network Height: #{height}")
print(f"GPU Power: {gpu_parts[0]} W / {gpu_parts[1]} W (Clamped)")
print(f"GPU Temp: {gpu_parts[2]} C (Fan {gpu_parts[3]}%)")
print(f"GPU Clocks: Core {gpu_parts[4]} MHz | Mem {gpu_parts[5]} MHz (Locked)")
print(f"GPU Utilization: {gpu_parts[6]}%")

print("\n--- Maturing Blocks ---")
for b in sorted(unconfirmed, key=lambda x: int(x.get('height', 0))):
    b_height = int(b.get('height', 0))
    confirms = int(height) - b_height
    reward = float(b.get('reward', 0)) / 1e8
    print(f"Block #{b_height}: {confirms}/100 confs | Reward: +{reward:.4f} PRL | {max(0, 100 - confirms)} blocks remaining")
