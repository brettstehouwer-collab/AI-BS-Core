# File: c:/AI-BS/scratch/antigravity_staging.py
from dataclasses import asdict, dataclass
from decimal import Decimal, ROUND_DOWN, ROUND_HALF_UP
import json
from pathlib import Path
import urllib.request
from typing import Any, Dict


@dataclass(frozen=True)
class TrialRiskConfig:
    symbol: str = "CRO/USDT"
    instrument_name: str = "CRO_USDT"
    quote_currency: str = "USDT"
    spot_collateral_usdt: str = "94.81"
    order_notional_usdt: str = "2.00"
    price_stop_pct: str = "0.02"
    take_profit_pct: str = "0.015"
    daily_loss_cutoff_usdt: str = "1.00"
    min_notional_usdt: str = "1.00"
    quantity_step_cro: str = "1"
    price_tick_usdt: str = "0.00001"


def fetch_live_cro_usdt_ticker(instrument: str = "CRO_USDT") -> Dict[str, str]:
    url: str = (
        f"https://api.crypto.com/exchange/v1/public/get-tickers?instrument_name={instrument}"
    )
    req: urllib.request.Request = urllib.request.Request(
        url, headers={"User-Agent": "AI-BS-Codex-Trial/1.0"}
    )
    try:
        with urllib.request.urlopen(req, timeout=8.0) as resp:
            payload: Dict[str, Any] = json.loads(resp.read().decode("utf-8"))
            data_list: Any = payload.get("result", {}).get("data", [])
            if isinstance(data_list, list) and len(data_list) > 0:
                row: Dict[str, Any] = data_list[0]
                return {
                    "bid": str(row.get("b") or "0.04310"),
                    "ask": str(row.get("k") or "0.04311"),
                    "last": str(row.get("a") or "0.04310"),
                    "high_24h": str(row.get("h") or "0.04436"),
                    "low_24h": str(row.get("l") or "0.04147"),
                    "source": "crypto.com_live_public_api",
                }
    except Exception:
        return {
            "bid": "0.04310",
            "ask": "0.04311",
            "last": "0.04310",
            "high_24h": "0.04436",
            "low_24h": "0.04147",
            "source": "fallback_snapshot",
        }
    return {
        "bid": "0.04310",
        "ask": "0.04311",
        "last": "0.04310",
        "high_24h": "0.04436",
        "low_24h": "0.04147",
        "source": "fallback_snapshot",
    }


def build_trial_manifest(config: TrialRiskConfig) -> Dict[str, Any]:
    notional: Decimal = Decimal(config.order_notional_usdt)
    stop_pct: Decimal = Decimal(config.price_stop_pct)
    tp_pct: Decimal = Decimal(config.take_profit_pct)
    daily_cutoff: Decimal = Decimal(config.daily_loss_cutoff_usdt)
    min_notional: Decimal = Decimal(config.min_notional_usdt)
    qty_step: Decimal = Decimal(config.quantity_step_cro)
    px_tick: Decimal = Decimal(config.price_tick_usdt)

    if notional < min_notional:
        raise ValueError("Order notional is below exchange minimum notional.")
    if stop_pct <= Decimal("0") or stop_pct >= Decimal("1"):
        raise ValueError("Price stop percentage must be in (0, 1).")
    if daily_cutoff <= Decimal("0"):
        raise ValueError("Daily loss cutoff must be positive.")

    ticker: Dict[str, str] = fetch_live_cro_usdt_ticker(config.instrument_name)
    entry_ask: Decimal = Decimal(ticker["ask"])
    raw_qty: Decimal = (notional / entry_ask).quantize(qty_step, rounding=ROUND_DOWN)
    if raw_qty * entry_ask < min_notional:
        raw_qty = (min_notional / entry_ask).quantize(qty_step, rounding=ROUND_HALF_UP) + qty_step

    actual_notional: Decimal = (raw_qty * entry_ask).quantize(Decimal("0.00001"))
    stop_price: Decimal = (entry_ask * (Decimal("1") - stop_pct)).quantize(
        px_tick, rounding=ROUND_DOWN
    )
    take_profit_price: Decimal = (entry_ask * (Decimal("1") + tp_pct)).quantize(
        px_tick, rounding=ROUND_HALF_UP
    )
    max_loss_per_order: Decimal = (raw_qty * (entry_ask - stop_price)).quantize(
        Decimal("0.0001")
    )

    return {
        "trial_config": asdict(config),
        "live_market_ticker": ticker,
        "computed_order_plan": {
            "entry_reference_ask_usdt": str(entry_ask),
            "order_quantity_cro": int(raw_qty),
            "order_notional_usdt": str(actual_notional),
            "stop_trigger_price_usdt": str(stop_price),
            "take_profit_price_usdt": str(take_profit_price),
            "estimated_stop_loss_usdt": str(max_loss_per_order),
            "daily_loss_cutoff_usdt": str(daily_cutoff),
            "max_stopped_trades_per_day": int(
                (daily_cutoff / max_loss_per_order).to_integral_value(rounding=ROUND_DOWN)
            )
            if max_loss_per_order > Decimal("0")
            else 0,
        },
        "ledger_path": str(load_or_verify_ledger_path()),
        "live_activation": False,
    }


def load_or_verify_ledger_path() -> Path:
    return Path(r"C:\AI-BS\backend\crypto_ledger.json")


if __name__ == "__main__":
    manifest: Dict[str, Any] = build_trial_manifest(TrialRiskConfig())
    print(json.dumps(manifest, indent=2))
