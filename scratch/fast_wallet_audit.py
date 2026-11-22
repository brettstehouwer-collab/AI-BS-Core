import os
import re
from pathlib import Path
from dotenv import load_dotenv

files_to_check = [
    r'C:\AI-BS\.env',
    r'C:\AI-BS\backend\.env',
    r'C:\AI-BS\pearl\.env',
    r'C:\AI-BS\docs\crypto_offramp_guide.md',
    r'C:\AI-BS\step_2_exchange_setup_guide.md',
    r'C:\AI-BS\Agent_Implementation_Plans_History\20260907_201500_plan_cryptocom_polygon_binding.md',
    r'C:\AI-BS\Agent_Implementation_Plans_History\20260908_161500_plan_treasury_card_and_deposit_address_update.md',
    r'C:\AI-BS\AI_BS_MASTER_ARCHITECTURAL_LEDGER.md'
]

wallets = []

def add_wallet(addr, network, label, context, source_file):
    if not any(w['address'] == addr for w in wallets):
        wallets.append({
            'address': addr,
            'network': network,
            'label': label,
            'context': context,
            'source': os.path.basename(source_file)
        })

for fpath in files_to_check:
    if os.path.exists(fpath):
        with open(fpath, 'r', encoding='utf-8', errors='ignore') as f:
            lines = f.readlines()
            for line in lines:
                line = line.strip()
                if not line: continue
                # Match EVM
                evm_m = re.findall(r'0x[a-fA-F0-9]{40}', line)
                for a in evm_m:
                    if a == '0x3c499c542cEF5E3811e1192ce70d8cC03d5c3359':
                        continue # USDC Contract
                    elif a == '0xe60201989b8628f43dc0605f585a72bcf1f1e977':
                        continue # CLORE Contract
                    elif a == '0xc2132D05D31c914a87C6611C10748AEb04B58e8F':
                        continue # USDT Contract
                    elif a.lower() == '0x4761ad28a8a6b0f5f66e0825a03aa419376152aa'.lower():
                        add_wallet(a, 'Polygon (MATIC) / EVM', 'Crypto.com App Deposit Wallet', 'Primary regulated cash-out destination (USDC/USDT)', fpath)
                    elif a.lower() == '0xd269c1ce398397b441f1d4573bd630bdd6c1e56b'.lower():
                        add_wallet(a, 'Ethereum (ERC-20) / Multi-chain EVM', 'AI-BS Sovereign Treasury Hot Wallet', 'Active self-custody vault (holds 1,158.82 CLORE)', fpath)
                    elif a.lower() == '0xd6277c501465cfc329d8dd429908769718aa49fa'.lower():
                        add_wallet(a, 'Polygon / EVM', 'Legacy Treasury Hot Wallet (Retired)', 'Old treasury address before Sept 2026 upgrade', fpath)
                    elif a.lower() == '0xadee155f468e9cd18fa62a18da259640b8dcbdc9'.lower():
                        add_wallet(a, 'Polygon / EVM', 'Phase 9 Gaming Treasury Wallet', 'Historical gaming and USDC payout vault', fpath)
                    else:
                        add_wallet(a, 'EVM Network', 'Detected EVM Address', line[:60], fpath)

                # Match Pearl
                prl_m = re.findall(r'prl1[a-zA-HJ-NP-Z0-9]{50,65}', line)
                for a in prl_m:
                    if 'p5r4kv' in a:
                        add_wallet(a, 'Pearl Layer-1 (PRL)', 'Pearl Mining Stratum Address', 'RTX 4090 HeroMiners mining pool target', fpath)
                    elif 'pkn5kx' in a:
                        add_wallet(a, 'Pearl Layer-1 (PRL)', 'Pearl Desktop GUI Receive Address', 'Local desktop wallet HD receive address', fpath)
                    elif 'p8e3ar' in a:
                        add_wallet(a, 'Pearl Layer-1 (PRL)', 'SafeTrade Exchange Deposit Address', 'SafeTrade exchange PRL bridge deposit address', fpath)
                    else:
                        add_wallet(a, 'Pearl Layer-1 (PRL)', 'Pearl Wallet Address', line[:60], fpath)

                # Match Chia
                xch_m = re.findall(r'xch1[a-zA-HJ-NP-Z0-9]{50,65}', line)
                for a in xch_m:
                    if 'y7l2q9' in a:
                        add_wallet(a, 'Chia Network (XCH)', 'Chia Primary Auto-Exchange Target', 'Chia farmer & NFT royalty address in root .env', fpath)
                    elif '7fhz6m' in a:
                        add_wallet(a, 'Chia Network (XCH)', 'Chia Secondary / Bladebit Target', 'Recorded in pearl/.env configuration', fpath)
                    else:
                        add_wallet(a, 'Chia Network (XCH)', 'Chia Address', line[:60], fpath)

                # Match Doge
                doge_m = re.findall(r'D[5-9A-HJ-NP-U][a-km-zA-HJ-NP-Z1-9]{32,34}', line)
                for a in doge_m:
                    add_wallet(a, 'Dogecoin (DOGE)', 'Dogecoin Dual-Miner Payout Wallet', 'Dual-mining target in root .env & pearl/.env', fpath)

# Also add the Clore Bitcoin deposit wallet
add_wallet('bc1qnmkdqygvx4llnwmfv7y08q2fcr4f0hndxwyz87', 'Bitcoin (BTC)', 'Clore.ai Custodial Bitcoin Address', 'Assigned BTC deposit address returned by Clore API', 'Clore API v1')

print(f"TOTAL DETECTED CRYPTO WALLETS: {len(wallets)}\n")
for idx, w in enumerate(wallets, 1):
    print(f"[{idx}] {w['label']} ({w['network']})")
    print(f"    Address: {w['address']}")
    print(f"    Usage:   {w['context']}")
    print(f"    Found:   {w['source']}")
    print("-" * 65)
