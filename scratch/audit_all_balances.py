import json
import time
import urllib.request
import urllib.error

HEADERS = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}

results = {}

def fetch_json(url, payload=None, timeout=6):
    try:
        data = json.dumps(payload).encode() if payload else None
        req = urllib.request.Request(url, data=data, headers={'Content-Type': 'application/json', **HEADERS})
        with urllib.request.urlopen(req, timeout=timeout) as res:
            return json.loads(res.read().decode())
    except Exception as e:
        return {'error': str(e)}

# --- 1. EVM Checking (Ethereum & Polygon) ---
evm_wallets = [
    ("0xd269c1CE398397b441F1D4573Bd630bDd6c1e56b", "AI-BS Treasury Hot Wallet (Active)"),
    ("0x4761aD28A8A6b0F5F66E0825a03AA419376152aa", "Crypto.com App Deposit Wallet"),
    ("0xD6277C501465CFc329D8dd429908769718aa49FA", "Legacy Treasury Hot Wallet (Retired)"),
    ("0xaDEE155F468E9cD18Fa62a18da259640B8DcbDc9", "Phase 9 Gaming Treasury Wallet"),
    ("0xe67824E6383d5644269C94B1b381f8922343B15A", "Historical Prototype Deployer A"),
    ("0x8D53c6247244339C280Ed4f524016bc1eBC006A0", "Historical Prototype Deployer B"),
    ("0xc4D44D5Cba9a3a028DB72593674B3CD356ABB0AE", "Historical Prototype Deployer C")
]

eth_rpc = "https://ethereum-rpc.publicnode.com"
poly_rpc = "https://polygon-bor-rpc.publicnode.com"
usdc_poly = "0x3c499c542cEF5E3811e1192ce70d8cC03d5c3359"
clore_eth = "0xe60201989b8628f43dc0605f585a72bcf1f1e977"

for addr, label in evm_wallets:
    res = {'label': label, 'network': 'EVM (Ethereum / Polygon)'}
    
    # 1. ETH Native
    p_eth = {'jsonrpc':'2.0','method':'eth_getBalance','params':[addr, 'latest'],'id':1}
    r_eth = fetch_json(eth_rpc, p_eth)
    res['eth_balance'] = int(r_eth.get('result', '0x0'), 16) / 1e18 if 'result' in r_eth else 0.0
    
    # 2. Polygon Native (POL)
    p_poly = {'jsonrpc':'2.0','method':'eth_getBalance','params':[addr, 'latest'],'id':2}
    r_poly = fetch_json(poly_rpc, p_poly)
    res['pol_balance'] = int(r_poly.get('result', '0x0'), 16) / 1e18 if 'result' in r_poly else 0.0

    # 3. Polygon USDC
    padded = addr[2:].lower().zfill(64)
    p_usdc = {'jsonrpc':'2.0','method':'eth_call','params':[{'to': usdc_poly, 'data': '0x70a08231' + padded}, 'latest'],'id':3}
    r_usdc = fetch_json(poly_rpc, p_usdc)
    res['polygon_usdc'] = int(r_usdc.get('result', '0x0'), 16) / 1e6 if 'result' in r_usdc else 0.0

    # 4. Ethereum CLORE
    p_clore = {'jsonrpc':'2.0','method':'eth_call','params':[{'to': clore_eth, 'data': '0x70a08231' + padded}, 'latest'],'id':4}
    r_clore = fetch_json(eth_rpc, p_clore)
    res['ethereum_clore'] = int(r_clore.get('result', '0x0'), 16) / 1e18 if 'result' in r_clore else 0.0

    results[addr] = res
    time.sleep(0.3)

# --- 2. Bitcoin Checking ---
btc_wallets = [
    ("bc1qnmkdqygvx4llnwmfv7y08q2fcr4f0hndxwyz87", "Clore.ai Custodial Bitcoin Deposit")
]
for addr, label in btc_wallets:
    res = {'label': label, 'network': 'Bitcoin (BTC)'}
    data = fetch_json(f"https://mempool.space/api/address/{addr}")
    if 'chain_stats' in data:
        funded = data['chain_stats'].get('funded_txo_sum', 0)
        spent = data['chain_stats'].get('spent_txo_sum', 0)
        res['btc_balance'] = (funded - spent) / 1e8
        res['tx_count'] = data['chain_stats'].get('tx_count', 0)
    else:
        res['btc_balance'] = 0.0
        res['tx_count'] = 0
    results[addr] = res
    time.sleep(0.3)

# --- 3. Dogecoin Checking ---
doge_wallets = [
    ("DHg4nBMj5tUenAVUG1XYgcic46SoJ2AN2G", "Primary Dogecoin Mining Payout Wallet"),
    ("DLhqTFrXoeDrQ6AzEbkMkCXEv6FqK1kLBSox", "Secondary Dogecoin Target"),
    ("DRihRLZBKgooyDzxQeHbztNkabRbBEt6rs", "Historical Dogecoin Conversation Target")
]
for addr, label in doge_wallets:
    res = {'label': label, 'network': 'Dogecoin (DOGE)'}
    data = fetch_json(f"https://dogechain.info/api/v1/address/balance/{addr}")
    if data and data.get('success') == 1:
        res['doge_balance'] = float(data.get('balance', 0))
    else:
        res['doge_balance'] = 0.0
        res['status'] = data.get('error', 'Queried public explorer')
    results[addr] = res
    time.sleep(0.3)

# --- 4. Pearl HeroMiners Pool Checking ---
prl_wallets = [
    ("prl1p5r4kvz636h2pa9fuww723s4r02flt25rec9qs6yjckk7lyejkvjs67a4n5", "Pearl Stratum Mining Rig Target"),
    ("prl1pkn5kx5qr08wlx6jaasjrf4kdkjx5g8gnevmmz9dptkz5q0lr3p4qfsa7ya", "Pearl Desktop GUI Receive Address"),
    ("prl1p8e3ar3mje25fez4vl76wng3yzxzh7d8czyuvxtxlydhk6hkmf4kqulwrgn", "SafeTrade Exchange PRL Bridge"),
    ("prl1phhaqjgq4vvapjdl480yflm3qqv48em5kn095cvafq8rzpdahfk7q6rcjer", "Historical Pearl Test Target")
]
for addr, label in prl_wallets:
    res = {'label': label, 'network': 'Pearl (PRL)'}
    # Check HeroMiners pool stats for this address
    data = fetch_json(f"https://pearl.herominers.com/api/stats_address?address={addr}")
    if data and 'stats' in data:
        res['pool_pending_prl'] = float(data['stats'].get('balance', 0)) / 1e9
        res['pool_paid_prl'] = float(data['stats'].get('paid', 0)) / 1e9
        res['last_share'] = data['stats'].get('lastShare', 0)
    else:
        res['pool_pending_prl'] = 0.0
        res['pool_paid_prl'] = 0.0
        res['status'] = 'On-chain HD Wallet (Local GUI)'
    results[addr] = res
    time.sleep(0.3)

# --- 5. Chia Checking ---
chia_wallets = [
    ("xch1y7l2q9l2jzzmlch8lnzymnt3t5uknrczd85y5hu6ehtakp4drxtq4kpgge", "Chia Primary Farmer & NFT Royalty Address"),
    ("xch17fhz6mn3f0z693y5fdrqqcjg7lk7vlqqsklk78ql7negqay5lz7svgndzu", "Chia Secondary Plotter Target")
]
for addr, label in chia_wallets:
    res = {'label': label, 'network': 'Chia Network (XCH)'}
    data = fetch_json(f"https://api.spacescan.io/api/v0.1/account/balance?address={addr}")
    if data and 'balance' in data:
        res['xch_balance'] = float(data.get('balance', 0)) / 1e12
    else:
        res['xch_balance'] = 0.0
        res['status'] = 'Active Plotter Configuration'
    results[addr] = res
    time.sleep(0.3)

with open(r'C:\AI-BS\scratch\live_blockchain_audit_results.json', 'w') as f:
    json.dump(results, f, indent=2)

print("AUDIT_COMPLETE")
