import os
import json
import logging
from pathlib import Path
from typing import Optional, List
from fastapi import APIRouter, HTTPException, Depends, Body
from pydantic import BaseModel
from core.crypto_execution_safety import execution_status
from core.crypto_ledger_io import read_ledger as strict_read_ledger, LedgerIntegrityError

logger = logging.getLogger("CryptoControlRouter")

router = APIRouter(prefix="/api/crypto", tags=["Crypto Swarm Mobile Controller"])

BACKEND_DIR = Path(__file__).resolve().parent.parent
LEDGER_FILE = BACKEND_DIR / "crypto_ledger.json"
ENV_FILE = BACKEND_DIR.parent / ".env"


class ParameterUpdateRequest(BaseModel):
    buy_dip_pct: Optional[float] = None
    take_profit_pct: Optional[float] = None
    trade_usd_amount: Optional[float] = None
    watcher_symbols: Optional[List[str]] = None


class ForceSwapRequest(BaseModel):
    from_symbol: str
    to_symbol: str


def get_env_params():
    keys = {}
    if ENV_FILE.exists():
        with open(ENV_FILE, "r") as f:
            for line in f:
                if "=" in line and not line.startswith("#"):
                    k, v = line.strip().split("=", 1)
                    keys[k] = v.strip('"')
    return {
        "buy_dip_pct": float(keys.get("BUY_DIP_PCT", "0.015")),
        "take_profit_pct": float(keys.get("TAKE_PROFIT_PCT", "0.02")),
        "trade_usd_amount": float(keys.get("TRADE_USD_AMOUNT", "2.00")),
        "watcher_symbols": [
            s.strip()
            for s in keys.get(
                "WATCHER_SYMBOLS", "BTC/USD,ETH/USD,SOL/USD,DOGE/USD"
            ).split(",")
            if s.strip()
        ],
    }


def read_ledger():
    try:
        return strict_read_ledger(LEDGER_FILE)
    except LedgerIntegrityError:
        raise HTTPException(status_code=503, detail="Ledger unavailable; reconciliation required")


@router.get("/telemetry")
@router.get("/v1/telemetry")
@router.get("/swarm-status")
async def get_swarm_status():
    ledger = read_ledger()
    params = get_env_params()

    positions = ledger.get("positions", {})
    ref_prices = ledger.get("reference_prices", {})
    total_profit = ledger.get("total_profit_usd", 0.0)

    formatted_positions = []
    total_est_value_usd = 0.0

    for symbol, pos in positions.items():
        amount = pos.get("amount", 0.0)
        avg_price = pos.get("avg_buy_price", 0.0)
        last_price = pos.get("last_buy_price", avg_price)
        cur_ref = ref_prices.get(symbol, last_price)
        est_val = amount * cur_ref
        total_est_value_usd += est_val

        profit_pct = (
            ((cur_ref - avg_price) / avg_price * 100.0) if avg_price > 0 else 0.0
        )

        formatted_positions.append(
            {
                "symbol": symbol,
                "amount": amount,
                "avg_buy_price": avg_price,
                "last_buy_price": last_price,
                "current_ref_price": cur_ref,
                "estimated_value_usd": round(est_val, 4),
                "unrealized_profit_pct": round(profit_pct, 2),
            }
        )

    return {
        "status": "held",
        "execution": execution_status(),
        "balance_verified": False,
        "ledger": ledger,
        "usd_balance": None,
        "total_active_positions": len(positions),
        "total_estimated_portfolio_usd": round(total_est_value_usd, 2),
        "total_profit_usd": round(total_profit, 4),
        "parameters": params,
        "positions": formatted_positions,
        "tracked_symbols_count": len(ref_prices),
        "strategy_layer": ledger.get("strategy_layer", "Market Making"),
        "last_action": ledger.get("last_action", "initialized"),
    }


@router.post("/force-swap")
async def force_swap(req: ForceSwapRequest):
    # Never fabricate a swap by changing holdings without exchange fills.
    raise HTTPException(status_code=503, detail="Reconciliation required; swap dispatch is held")


@router.post("/set-parameters")
async def set_parameters(req: ParameterUpdateRequest):
    raise HTTPException(status_code=503, detail="Trading configuration held pending authenticated risk limits")
