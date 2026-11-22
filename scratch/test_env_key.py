import sys, os
sys.path.insert(0, r"C:\AI-BS\scratch")
import live_cro_usdt_trader as trader

env_vars = {}
with open(r"C:\AI-BS\.env", "r", encoding="utf-8") as f:
    for line in f:
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" in line:
            parts = line.split("=", 1)
            env_vars[parts[0].strip()] = parts[1].strip().strip('"\'')

env_key = env_vars.get("CRYPTO_COM_API_KEY")
env_sec = env_vars.get("CRYPTO_COM_SECRET_KEY")

print("Checking .env credentials...")
print("Env key prefix:", env_key[:6] if env_key else "None")
if env_key and env_sec:
    client = trader.CryptoComClient(env_key, env_sec)
    try:
        res = client.get_balances()
        print("SUCCESS WITH .ENV KEY:", res)
    except Exception as e:
        print("FAIL with .env key:", e)
