from security.host_control_access import AdminHostControlRoute
import os
import sys
import logging
import json
import time
import asyncio
from pathlib import Path
from typing import Dict, Any, List, Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from core.crypto_execution_safety import execution_status
from core.crypto_ledger_io import read_ledger as strict_read_ledger, LedgerIntegrityError

logger = logging.getLogger("TradingRouter")
router = APIRouter(route_class=AdminHostControlRoute, prefix="/api/trading", tags=["Crypto-Swarm & Finance"])

MASTER_DB = "C:/AI-BS/backend/aibs_master.db"
DRIP_LEDGER_PATH = MASTER_DB if os.path.exists(MASTER_DB) else "C:/AI-BS/backend/drip_ledger.db"
LEDGER_FILE = Path("C:/AI-BS/backend/crypto_ledger.json")


class TradeOrderRequest(BaseModel):
    pair: str = "SOL/USDT"
    action: str = "BUY"
    amount_usd: float = 25.0
    strategy: str = "Micro-Drip Momentum"


@router.get("/status")
async def get_trader_status():
    """Returns Crypto-Swarm bot runtime and safety status."""
    return {
        "status": "held",
        "engine": "Crypto-Swarm Micro-Drip Engine",
        "runtime_verified": False,
        "execution": execution_status(),
        "risk_limits_verified": False,
        "max_drawdown_limit_pct": None,
        "daily_trade_cap_usd": None,
    }


@router.get("/ledger")
async def get_trade_ledger(limit: int = 20):
    """Read historical records without initializing or certifying a ledger."""
    raise HTTPException(503, "Trading reads held: account ownership, provider read authorization and ledger reconciliation are required.")
    import sqlite3
    from contextlib import closing
    if not 1 <= limit <= 1000:
        raise HTTPException(status_code=400, detail="Limit must be between 1 and 1000")
    try:
        uri = Path(DRIP_LEDGER_PATH).resolve().as_uri() + "?mode=ro"
        with closing(sqlite3.connect(uri, uri=True)) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute("SELECT * FROM trades ORDER BY timestamp DESC LIMIT ?", (limit,)).fetchall()
            trades = [dict(row) for row in rows]
        return {"status": "historical_unverified", "source": DRIP_LEDGER_PATH,
                "reconciliation_required": True, "count": len(trades), "trades": trades}
    except sqlite3.Error:
        raise HTTPException(status_code=503, detail="Ledger unavailable; reconciliation required")


@router.get("/balances")
async def get_wallet_balances():
    """
    Return local positions as historical records, not verified exchange balances.
    """
    raise HTTPException(503, "Trading reads held: account ownership, provider read authorization and ledger reconciliation are required.")
    try:
        historical = strict_read_ledger(LEDGER_FILE)
    except LedgerIntegrityError:
        raise HTTPException(status_code=503, detail="Ledger unavailable; reconciliation required")
    return {"status": "historical_unverified", "balance_verified": False,
            "portfolio_total_usd": None, "balances": [],
            "historical_positions": historical["positions"],
            "note": "Local holdings are unverified; exchange fill and fee reconciliation is required."}


@router.post("/order")
async def execute_trade_order(order: TradeOrderRequest):
    """
    Executes a trade order against a live exchange.
    Strict Zero-Mock Mandate: Requires verified live exchange credentials and active account collateral.
    Simulated orders and unbacked synthetic fills are strictly prohibited.
    """
    raise HTTPException(status_code=503, detail=execution_status())


# =====================================================================
# Kraken Sovereign Exchange Endpoints
# =====================================================================

class KrakenOrderRequest(BaseModel):
    symbol: str = "SOL/USD"
    side: str = "buy"  # "buy" or "sell"
    amount: float = 0.1
    order_type: str = "market"  # "market" or "limit"
    price: Optional[float] = None


@router.get("/kraken/status")
async def get_kraken_status():
    """Returns Kraken exchange API connection and zero-mock status."""
    raise HTTPException(503, "Trading reads held: account ownership, provider read authorization and ledger reconciliation are required.")
    try:
        from core.kraken_service import kraken_service
        return kraken_service.get_status()
    except Exception as e:
        return {"status": "error", "message": str(e)}


@router.get("/kraken/balance")
async def get_kraken_balance():
    """Fetches real-time non-zero wallet balances from Kraken (Strict Zero-Mock)."""
    raise HTTPException(503, "Trading reads held: account ownership, provider read authorization and ledger reconciliation are required.")
    try:
        from core.kraken_service import kraken_service
        return kraken_service.get_balance()
    except Exception as e:
        return {"status": "error", "message": str(e)}


@router.get("/kraken/ticker")
async def get_kraken_ticker(symbol: str = "SOL/USD"):
    """Fetches real-time ticker data (bid, ask, last price) for a pair on Kraken."""
    raise HTTPException(503, "Trading reads held: account ownership, provider read authorization and ledger reconciliation are required.")
    try:
        from core.kraken_service import kraken_service
        return kraken_service.get_ticker(symbol)
    except Exception as e:
        return {"status": "error", "message": str(e)}


@router.post("/kraken/order")
async def execute_kraken_order(req: KrakenOrderRequest):
    """
    Executes a live spot trade order on Kraken.
    Enforces daily cap safety and strict zero-mock execution.
    """
    raise HTTPException(status_code=503, detail=execution_status())
    # Retained legacy adapter below is unreachable while reconciliation is required.
    try:
        from core.kraken_service import kraken_service
        return kraken_service.create_order(
            symbol=req.symbol,
            side=req.side,
            amount=req.amount,
            order_type=req.order_type,
            price=req.price
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/kraken/orders/open")
async def get_kraken_open_orders(symbol: Optional[str] = None):
    """Returns open orders on Kraken."""
    raise HTTPException(503, "Trading reads held: account ownership, provider read authorization and ledger reconciliation are required.")
    try:
        from core.kraken_service import kraken_service
        return kraken_service.get_open_orders(symbol)
    except Exception as e:
        return {"status": "error", "message": str(e)}


@router.get("/kraken/trades")
async def get_kraken_trade_history(symbol: Optional[str] = None, limit: int = 50):
    """Returns verified trade history from Kraken."""
    raise HTTPException(503, "Trading reads held: account ownership, provider read authorization and ledger reconciliation are required.")
    try:
        from core.kraken_service import kraken_service
        return kraken_service.get_trade_history(symbol, limit=limit)
    except Exception as e:
        return {"status": "error", "message": str(e)}


@router.get("/kraken/deposit_address")
async def get_kraken_deposit_address(asset: str = "SOL"):
    """Returns wallet deposit address for transferring from other accounts to Kraken."""
    raise HTTPException(503, "Trading reads held: account ownership, provider read authorization and ledger reconciliation are required.")
    try:
        from core.kraken_service import kraken_service
        return kraken_service.get_deposit_address(asset)
    except Exception as e:
        return {"status": "error", "message": str(e)}