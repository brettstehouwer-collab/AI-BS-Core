import asyncio
import sys
import json
import urllib.request
sys.path.append(r"C:\AI-BS\backend")
from core.technical_indicators import CryptoTechnicals

async def check_bot_and_predictions():
    # 1. Check Telemetry
    try:
        t_res = urllib.request.urlopen("http://127.0.0.1:8007/api/v1/telemetry")
        telemetry = json.loads(t_res.read().decode())
        print("=== BOT TELEMETRY STATUS ===")
        print(f"Status: {telemetry.get('status')}")
        print(f"Positions: {telemetry.get('ledger', {}).get('positions')}")
        print(f"Pending Dip Orders: {telemetry.get('ledger', {}).get('pending_dip_buys')}")
        print(f"Last Action: {telemetry.get('ledger', {}).get('last_action')}")
        print(f"Active Parameters: TP={telemetry.get('take_profit_pct')*100:.1f}%, Dip={telemetry.get('buy_dip_pct')*100:.1f}%, Ceiling=${telemetry.get('macro_support_ceiling'):.5f}")
    except Exception as e:
        print(f"Telemetry error: {e}")

    # 2. Check Prediction Endpoint
    try:
        p_res = urllib.request.urlopen("http://127.0.0.1:8007/api/crypto/cro/predict")
        pred = json.loads(p_res.read().decode())
        print("\n=== PREDICTIVE PATTERN ENGINE ===")
        print(json.dumps(pred, indent=2))
    except Exception as e:
        print(f"Prediction endpoint error: {e}")

    # 3. Check Live Technical Signals from CryptoTechnicals
    try:
        tech = CryptoTechnicals()
        signals = await tech.get_all_signals("CRO/USD", "15m")
        print("\n=== LIVE TECHNICAL SIGNALS (15m Timeframe) ===")
        print(json.dumps(signals, indent=2))
        await tech.close()
    except Exception as e:
        print(f"Technicals error: {e}")

if __name__ == "__main__":
    asyncio.run(check_bot_and_predictions())
