from pathlib import Path
import os
import sys

# Test reading env and keys
script_dir = Path(r"C:\AI-BS\backend")
sys.path.insert(0, str(script_dir))
from crypto_trader_bot import keys

print("API Key configured:", bool(keys.get("CRYPTO_COM_API_KEY")))
print("Secret Key configured:", bool(keys.get("CRYPTO_COM_SECRET_KEY")))
print("Watcher Symbols:", keys.get("WATCHER_SYMBOLS", "CRO/USD,CRO/USDT"))
print("Macro Ceiling:", keys.get("MACRO_SUPPORT_CEILING", 0.05750))
print("Buy Dip Pct:", keys.get("BUY_DIP_PCT", keys.get("DCA_DIP_PCT", 0.042)))
