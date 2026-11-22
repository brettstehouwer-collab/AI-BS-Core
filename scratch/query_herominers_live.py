import requests, json

headers = {"User-Agent": "Mozilla/5.0"}
url_addr = "https://pearl.herominers.com/api/stats_address?address=prl1p5r4kvz636h2pa9fuww723s4r02flt25rec9qs6yjckk7lyejkvjs67a4n5&recentBlocksAmount=20"
url_pool = "https://pearl.herominers.com/api/stats"

try:
    r_addr = requests.get(url_addr, headers=headers, timeout=10).json()
    r_pool = requests.get(url_pool, headers=headers, timeout=10).json()
    height = r_pool.get("network", {}).get("height", 0)
    print("CURRENT_NETWORK_HEIGHT:", height)
    
    stats = r_addr.get("stats", {})
    print("BALANCE_RAW:", stats.get("balance"))
    print("PAID_RAW:", stats.get("paid"))
    print("HASHRATE:", stats.get("hashrate"))
    
    workers = r_addr.get("workers", [])
    for w in workers:
        print(f"WORKER: {w.get('name')} | Hashrate: {w.get('hashrate')} | Shares: {w.get('shares')} | Rating: {w.get('rating')}")
        
    unconf = r_addr.get("unconfirmed", [])
    print(f"TOTAL_UNCONFIRMED_BLOCKS: {len(unconf)}")
    for b in unconf:
        b_height = b.get("height", 0)
        reward = int(b.get("reward", 0)) / 1e9 if b.get("reward") else 0.0
        confs = height - b_height
        print(f"Block #{b_height} -> Confs: {confs}/100 | Est Reward: {reward:.4f} PRL")
        
    payments = r_addr.get("payments", [])
    print(f"PAYMENTS_COUNT: {len(payments)}")
    for p in payments:
        print(f"PAYMENT: {p}")
except Exception as e:
    print("Error:", e)
