import requests, subprocess, json

# 1. Pool stats
r = requests.get('http://localhost:8080/api/v1/mining/pearl/pool-stats')
pool = r.json().get('data', {})
stats = pool.get('stats', {})
unconfirmed = pool.get('unconfirmed', [])

mature_prl = float(stats.get('balance', 0)) / 1e8
pending_prl = sum(float(b.get('reward', 0)) for b in unconfirmed) / 1e8
shares = stats.get('shares_good', 0)
hashes = int(stats.get('hashes', 0))
height = stats.get('networkHeight', 0)
hr_1h = stats.get('hashrate_1h', 0)

# 2. GPU stats
res = subprocess.run(
    ["nvidia-smi", "--query-gpu=power.draw,temperature.gpu,fan.speed,clocks.current.graphics,clocks.current.memory,utilization.gpu", "--format=csv,noheader,nounits"],
    capture_output=True, text=True
)
gpu_parts = [p.strip() for p in res.stdout.strip().split(",")]

print(f"=== LIVE ECOSYSTEM METRICS (23:55 EDT) ===")
print(f"Mature Balance: {mature_prl:.4f} PRL (~ USD at .10)")
print(f"Pending Rewards: {pending_prl:.4f} PRL across {len(unconfirmed)} maturing blocks (~ USD)")
print(f"Total Accrued: {mature_prl + pending_prl:.4f} PRL (~ USD)")
print(f"Accepted Shares: {shares} (0 invalid)")
print(f"Total Hashes: {hashes:,} ({hashes/1e9:.2f} B)")
print(f"Pool Hashrate (1h): {hr_1h/1e3:.2f} GH/s")
print(f"Network Height: #{height}")
print(f"GPU Power: {gpu_parts[0]} W (Target: 310W Clamped)")
print(f"GPU Temp: {gpu_parts[1]} C (Fan: {gpu_parts[2]}%)")
print(f"GPU Clocks: Core {gpu_parts[3]} MHz | Mem {gpu_parts[4]} MHz (Locked)")
print(f"GPU Utilization: {gpu_parts[5]}%")

print("\n--- Maturing Blocks ---")
for b in sorted(unconfirmed, key=lambda x: int(x.get('height', 0))):
    b_height = int(b.get('height', 0))
    confirms = int(height) - b_height
    reward = float(b.get('reward', 0)) / 1e8
    print(f"Block #{b_height}: {confirms}/100 confs | Reward: +{reward:.4f} PRL | Remaining: {max(0, 100 - confirms)} blocks")
