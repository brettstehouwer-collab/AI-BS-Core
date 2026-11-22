import os
import json
from web3 import Web3
from dotenv import load_dotenv

# Load env variables
load_dotenv('C:/AI-BS/backend/.env')

# Setup Web3 connection
rpc_url = os.getenv("WEB3_PROVIDER_URI", "https://polygon-rpc.com")
w3 = Web3(Web3.HTTPProvider(rpc_url))

# Addresses
hot_wallet = "0xD6277C501465CFc329D8dd429908769718aa49FA"
hot_wallet = w3.to_checksum_address(hot_wallet)
usdc_address = os.getenv("USDC_CONTRACT_ADDRESS", "0x3c499c542cEF5E3811e1192ce70d8cC03d5c3359")
usdc_address = w3.to_checksum_address(usdc_address)

# ERC-20 ABI (minimal for balanceOf)
erc20_abi = json.loads('[{"constant":true,"inputs":[{"name":"_owner","type":"address"}],"name":"balanceOf","outputs":[{"name":"balance","type":"uint256"}],"type":"function"}]')

def check_balances():
    if not w3.is_connected():
        print("Failed to connect to Polygon network.")
        return

    # Check POL (MATIC) Balance
    pol_balance_wei = w3.eth.get_balance(hot_wallet)
    pol_balance = w3.from_wei(pol_balance_wei, 'ether')
    print(f"POL (Gas) Balance: {pol_balance} POL")

    # Check USDC Balance
    usdc_contract = w3.eth.contract(address=usdc_address, abi=erc20_abi)
    usdc_balance_raw = usdc_contract.functions.balanceOf(hot_wallet).call()
    usdc_balance = usdc_balance_raw / (10 ** 6) # USDC has 6 decimals on Polygon
    print(f"USDC (Liquidity) Balance: {usdc_balance} USDC")

if __name__ == "__main__":
    print(f"Checking balances for Hot Wallet: {hot_wallet} on Polygon")
    check_balances()
