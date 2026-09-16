import os
import sys
from pathlib import Path
from dotenv import load_dotenv
from web3 import Web3
from eth_account import Account

sys.path.append("C:/AI-BS/backend")
from commercial_gateway.gpu_network_router import decrypt_vault_key

env_path = "C:/AI-BS/backend/.env"
load_dotenv(env_path, override=True)

pk_raw = os.environ.get("PAYOUT_WALLET_PRIVATE_KEY", "").strip("'\" ")
print(f"[+] Raw env var starts with gAAAAA: {pk_raw.startswith('gAAAAA')}")
private_key = decrypt_vault_key(pk_raw)
print(f"[+] Decrypted key length: {len(private_key)}")

rpc_url = os.environ.get("WEB3_PROVIDER_URI", "https://polygon-bor-rpc.publicnode.com").strip("'\" ")
print(f"[+] Connecting to Web3 RPC: {rpc_url}")
web3 = Web3(Web3.HTTPProvider(rpc_url))
is_conn = web3.is_connected()
print(f"[+] Web3 Connected: {is_conn}")

if is_conn and len(private_key) > 10:
    try:
        account = Account.from_key(private_key)
        print(f"[+] Derived Hot Wallet Address: {account.address}")
        balance_wei = web3.eth.get_balance(account.address)
        print(f"[+] MATIC Balance: {web3.from_wei(balance_wei, 'ether')}")
    except Exception as e:
        print(f"[-] Error loading wallet: {e}")
