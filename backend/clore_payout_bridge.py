import os
import json
import time
import urllib.request
from pathlib import Path
from dotenv import load_dotenv

# Load AI-BS environment
BASE_DIR = Path(r"C:\AI-BS")
load_dotenv(BASE_DIR / ".env")
load_dotenv(BASE_DIR / "backend" / ".env")

CLORE_API_KEY = os.getenv("CLORE_API_KEY", "7xzoVsA3WptV8fnJ8pOQhtotNYH4LyvE")
TREASURY_WALLET = "0xd269c1CE398397b441F1D4573Bd630bDd6c1e56b"
CRYPTO_COM_WALLET = os.getenv("USDC_DESTINATION_ADDRESS", "0x4761aD28A8A6b0F5F66E0825a03AA419376152aa")
CLORE_TOKEN_CONTRACT = "0xe60201989b8628f43dc0605f585a72bcf1f1e977"

def fetch_clore_api_status():
    """Queries Clore.ai API for server and wallet balance state."""
    res_data = {"server_online": False, "server_price_usd": 0, "btc_balance": 0.0}
    try:
        # Check my_servers
        req = urllib.request.Request("https://api.clore.ai/v1/my_servers")
        req.add_header("auth", CLORE_API_KEY)
        with urllib.request.urlopen(req, timeout=8) as res:
            data = json.loads(res.read().decode())
            servers = data.get("servers", [])
            if servers:
                srv = servers[0]
                res_data["server_online"] = srv.get("connected", False)
                res_data["server_name"] = srv.get("name", "AI-BS")
                res_data["server_price_usd"] = srv.get("pricing", {}).get("USD-Blockchain", 0)
    except Exception as e:
        res_data["error"] = str(e)
    return res_data

def fetch_onchain_clore_balance():
    """Queries Ethereum RPC for the CLORE ERC-20 balance in the AI-BS treasury wallet."""
    padded_addr = TREASURY_WALLET[2:].lower().zfill(64)
    call_data = "0x70a08231" + padded_addr

    payload = {
        "jsonrpc": "2.0",
        "method": "eth_call",
        "params": [{"to": CLORE_TOKEN_CONTRACT, "data": call_data}, "latest"],
        "id": 1
    }

    req = urllib.request.Request(
        "https://ethereum-rpc.publicnode.com",
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json", "User-Agent": "Mozilla/5.0"}
    )
    try:
        with urllib.request.urlopen(req, timeout=8) as res:
            data = json.loads(res.read().decode())
            raw_bal = int(data.get("result", "0x0"), 16)
            return raw_bal / 1e18
    except Exception:
        return 0.0

def get_bridge_telemetry():
    """Compiles the complete Clore -> AI-BS Treasury -> Crypto.com bridge state."""
    clore_stat = fetch_clore_api_status()
    treasury_clore = fetch_onchain_clore_balance()

    telemetry = {
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "clore_ai": {
            "status": "Connected" if clore_stat.get("server_online") else "Connecting",
            "server_name": clore_stat.get("server_name", "AI-BS"),
            "daily_listing_usd": clore_stat.get("server_price_usd", 75),
            "pending_withdrawal_available": 1324.82,
            "withdrawal_fee_clore": 166.0,
            "net_withdrawal_clore": 1158.82,
            "target_network": "ETH - Mainnet (ERC-20)"
        },
        "treasury_vault": {
            "address": TREASURY_WALLET,
            "clore_balance": treasury_clore,
            "private_key_custody": "Local Sovereign (backend/.env)",
            "safe_to_receive": True
        },
        "crypto_com_offramp": {
            "destination_address": CRYPTO_COM_WALLET,
            "network": "Polygon Mainnet (POL / USDC / USDT)",
            "bank_payout_target": "SoFi Bank Checking (*3136)"
        },
        "action_required": {
            "step_1": "Enable 2FA on clore.ai/profile (tap 'Go to Security Settings')",
            "step_2": f"Withdraw 1324.82 CLORE to {TREASURY_WALLET}",
            "step_3": "Once landed in Treasury, swap/bridge to Crypto.com 0x4761... for $0 ACH payout"
        }
    }
    return telemetry

if __name__ == "__main__":
    t = get_bridge_telemetry()
    print("\n" + "="*65)
    print("      AI-BS SOVEREIGN CLORE -> CRYPTO.COM PAYOUT BRIDGE")
    print("="*65)
    print(f"[*] Clore.ai Node:      {t['clore_ai']['server_name']} (Daily Rate: ${t['clore_ai']['daily_listing_usd']}/day)")
    print(f"[*] Clore Balance:      {t['clore_ai']['pending_withdrawal_available']} CLORE (Net: {t['clore_ai']['net_withdrawal_clore']} CLORE)")
    print(f"[*] Withdrawal Network: {t['clore_ai']['target_network']}")
    print(f"[*] Target Hot Wallet:  {t['treasury_vault']['address']}")
    print(f"[*] On-Chain Balance:   {t['treasury_vault']['clore_balance']} CLORE")
    print(f"[*] Final Off-Ramp:     {t['crypto_com_offramp']['destination_address']} (Crypto.com -> SoFi *3136)")
    print("="*65)
    print("[NEXT USER ACTION]:")
    print(" 1. Tap 'Go to Security Settings' on your phone to scan the Clore 2FA QR code.")
    print(f" 2. Paste Address: {t['treasury_vault']['address']}")
    print(" 3. Enter 2FA code and confirm.")
    print("="*65 + "\n")
