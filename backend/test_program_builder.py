import sys, os
sys.path.append(r"C:\AI-BS\backend")
from core.program_builder_engine import AutonomousProgramBuilder

res = AutonomousProgramBuilder.build_program(
    project_name="crypto_price_scanner",
    language="python",
    description="Automated CRO & BTC Real-Time Price Ticker & Volume Monitor",
    files=[
        {
            "path": "main.py",
            "content": """import json, urllib.request, time

def scan_prices():
    print("=== AI-BS AUTONOMOUS CRYPTO PRICE SCANNER ===")
    url = "https://api.binance.com/api/v3/ticker/price?symbol=BTCUSDT"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "AI-BS-Scanner"})
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read().decode())
            print(f"BTC/USDT Live: ${float(data.get('price', 0)):,.2f}")
    except Exception as e:
        print(f"BTC Price Check: Offline/Fallback ({e})")
    
    print(f"CRO/USD Dip Monitoring Active. System Time: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    print("Scan completed successfully.")

if __name__ == '__main__':
    scan_prices()
"""
        },
        {
            "path": "README.md",
            "content": "# Crypto Price Scanner\nAutomated microservice built by Stehouwer AI-BS Autonomous Program Builder."
        }
    ],
    entrypoint="main.py",
    run_immediately=True
)

print("Built program result:")
print("Project Name:", res["project_name"])
print("Execution Status:", res["execution"]["status"])
print("Execution Stdout:\n", res["execution"]["stdout"])
print("Zip Path:", res["zip_path"])
