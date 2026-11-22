import urllib.request
import json

req = urllib.request.Request(
    'https://pearl.herominers.com/api/stats_address?address=prl1p5r4kvz636h2pa9fuww723s4r02flt25rec9qs6yjckk7lyejkvjs67a4n5',
    headers={'User-Agent': 'Mozilla/5.0'}
)
data = json.loads(urllib.request.urlopen(req, timeout=10).read().decode())

stats_req = urllib.request.Request('https://pearl.herominers.com/api/stats', headers={'User-Agent': 'Mozilla/5.0'})
global_stats = json.loads(urllib.request.urlopen(stats_req, timeout=10).read().decode())
net_height = global_stats.get('network', {}).get('height', 0)
print(f"CURRENT NETWORK HEIGHT: #{net_height}")

unconfirmed = data.get('unconfirmed', [])
total_pending = 0.0
print(f"Found {len(unconfirmed)} unconfirmed block(s):")
for b in unconfirmed:
    h = int(b.get('height', 0))
    reward = float(b.get('reward', 0)) / 1e8
    total_pending += reward
    confs = net_height - h if net_height else 0
    remaining = max(0, 100 - confs)
    pct = min(100.0, (confs / 100.0) * 100.0)
    print(f"  Block #{h}: {reward:.4f} PRL | {confs}/100 confs ({pct:.1f}%) | {remaining} blocks to unlock (~{remaining*3.2:.1f} min)")

print(f"\nTOTAL PENDING REWARDS: {total_pending:.4f} PRL (~${total_pending * 3.11:.2f} USD)")
