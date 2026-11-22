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

print(f"MATURE_PRL: {mature_prl:.4f}")
print(f"PENDING_PRL: {pending_prl:.4f}")
print(f"TOTAL_PRL: {mature_prl + pending_prl:.4f}")
print(f"SHARES: {shares}")
print(f"HASHES: {hashes}")
print(f"HEIGHT: {height}")
print(f"POWER: {gpu_parts[0]}")
print(f"TEMP: {gpu_parts[1]}")
print(f"FAN: {gpu_parts[2]}")
print(f"CORE_CLOCK: {gpu_parts[3]}")
print(f"MEM_CLOCK: {gpu_parts[4]}")
print(f"UTIL: {gpu_parts[5]}")
print(f"BLOCKS_COUNT: {len(unconfirmed)}")

for b in sorted(unconfirmed, key=lambda x: int(x.get('height', 0))):
    b_height = int(b.get('height', 0))
    confirms = int(height) - b_height
    reward = float(b.get('reward', 0)) / 1e8
    print(f"BLOCK: #{b_height} | {confirms}/100 | +{reward:.4f} PRL | {max(0, 100 - confirms)} left")
