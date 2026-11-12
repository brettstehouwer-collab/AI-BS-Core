from security.host_control_access import AdminHostControlRoute
import os
import sys
import logging
import json
import time
import asyncio
from pathlib import Path
from typing import Dict, Any, List, Optional
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, ConfigDict
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


class SpotPreviewRequest(BaseModel):
    model_config = ConfigDict(extra='forbid', strict=True)
    budget_usdt: str
    bid: str
    ask: str
    quantity_step: str
    price_tick: str
    minimum_notional_usd: str
    usdt_usd_index: str
    entry_fee_bps: str
    exit_fee_bps: str
    target_price: Optional[str] = None
    stop_price: Optional[str] = None
    max_exposure_usdt: Optional[str] = None
    daily_loss_budget_usdt: Optional[str] = None


@router.post("/preview")
async def preview_spot_arithmetic(request: SpotPreviewRequest):
    """Private stateless arithmetic only; no account fetch or order submission."""
    from core.crypto_spot_preview import preview_cro_spot
    from core.crypto_execution_controls import ControlError
    try:
        return preview_cro_spot(**request.model_dump())
    except ControlError as error:
        raise HTTPException(status_code=422, detail=str(error)) from None


@router.get('/public-preview')
async def get_public_spot_preview(request: Request, budget_usdt: str = '2',
        stop_percent: str = '2', target_percent: Optional[str] = None,
        max_exposure_usdt: Optional[str] = None, daily_loss_budget_usdt: str = '1',
        entry_fee_bps: str = '25', exit_fee_bps: str = '50', stop_type: str = 'STOP_LOSS',
        trigger_reference_type: str = 'LAST_PRICE', stop_limit_price: Optional[str] = None):
    """Explicit public-data calculation, independently of account/order holds."""
    from core.crypto_preview_chat import FIELDS
    keys = [key for key, _ in request.query_params.multi_items()]
    if len(keys) != len(set(keys)) or not set(keys).issubset(FIELDS):
        raise HTTPException(422, 'Unexpected or duplicate preview parameter.')
    from security.host_control_access import require_host_admin
    from core.personal_memory_scope import bind_memory_principal, reset_memory_principal
    from tools.bs_chat_tool_bridge import bs_chat_bridge
    principal = await require_host_admin(request)
    token = bind_memory_principal(principal)
    try:
        arguments = {'budget_usdt': budget_usdt, 'stop_percent': stop_percent,
            'daily_loss_budget_usdt': daily_loss_budget_usdt, 'entry_fee_bps': entry_fee_bps,
            'exit_fee_bps': exit_fee_bps, 'stop_type': stop_type,
            'trigger_reference_type': trigger_reference_type}
        if target_percent is not None: arguments['target_percent'] = target_percent
        if max_exposure_usdt is not None: arguments['max_exposure_usdt'] = max_exposure_usdt
        if stop_limit_price is not None: arguments['stop_limit_price'] = stop_limit_price
        result = await asyncio.to_thread(bs_chat_bridge.execute_tool, 'preview_crypto_spot', arguments)
    finally:
        reset_memory_principal(token)
    if result.get('status') != 'preview':
        raise HTTPException(503, 'Public arithmetic preview unavailable. No account was accessed or order sent.')
    return result


@router.get('/trial-status')
async def get_crypto_trial_status(request: Request):
    """Read server-selected trial metadata; no account access or dispatch."""
    from security.host_control_access import require_host_admin
    from core.personal_memory_scope import bind_memory_principal, reset_memory_principal
    from core.crypto_trial_status_contract import validate_trial_status
    from tools.bs_chat_tool_bridge import bs_chat_bridge
    principal = await require_host_admin(request)
    if request.query_params:
        raise HTTPException(422, 'This endpoint has no parameters.')
    token = bind_memory_principal(principal)
    try:
        try:
            result = await asyncio.to_thread(bs_chat_bridge.execute_tool, 'get_crypto_trial_status', {})
        except Exception:
            raise HTTPException(503, 'Trial status unavailable.') from None
    finally:
        reset_memory_principal(token)
    if type(result) is dict and result.get('status') == 'denied':
        raise HTTPException(403, 'Trial status access denied.')
    try:
        result = validate_trial_status(result)
    except (TypeError, ValueError):
        raise HTTPException(503, 'Trial status unavailable.') from None
    if result['status'] not in ('not_registered', 'qualification', 'held'):
        raise HTTPException(503, 'Trial status unavailable.')
    return result

@router.get('/protective-review')
async def get_crypto_protective_review(request: Request):
    """Read server-selected protective metadata; no preparation or dispatch."""
    from security.host_control_access import require_host_admin
    from core.personal_memory_scope import bind_memory_principal, reset_memory_principal
    from core.crypto_protective_review_contract import validate_protective_review
    from tools.bs_chat_tool_bridge import bs_chat_bridge
    principal = await require_host_admin(request)
    if request.query_params:
        raise HTTPException(422, 'This endpoint has no parameters.')
    token = bind_memory_principal(principal)
    try:
        try:
            result = await asyncio.to_thread(bs_chat_bridge.execute_tool, 'get_crypto_protective_review', {})
        except Exception:
            raise HTTPException(503, 'Protective review unavailable.') from None
    finally:
        reset_memory_principal(token)
    if type(result) is dict and result.get('status') == 'denied':
        raise HTTPException(403, 'Protective review access denied.')
    try:
        result = validate_protective_review(result)
    except (TypeError, ValueError):
        raise HTTPException(503, 'Protective review unavailable.') from None
    if result['status'] not in ('not_registered', 'not_prepared', 'qualification', 'held'):
        raise HTTPException(503, 'Protective review unavailable.')
    return result

@router.get('/public-book')
async def get_public_spot_book(request: Request):
    """Fixed CRO_USDT public depth; no bot/account/credential initialization."""
    if request.query_params:
        raise HTTPException(422, 'This endpoint has no parameters.')
    from datetime import datetime, timezone
    import httpx
    from core.crypto_com_acknowledgements import _json
    from core.crypto_execution_controls import number
    try:
        raw = bytearray()
        async with httpx.AsyncClient(timeout=5, trust_env=False, follow_redirects=False) as client:
            async with client.stream('GET', 'https://api.crypto.com/exchange/v1/public/get-book',
                    params={'instrument_name': 'CRO_USDT', 'depth': 10}) as response:
                if response.status_code != 200: raise ValueError('Public source unavailable')
                async for chunk in response.aiter_bytes():
                    raw.extend(chunk)
                    if len(raw) > 1024 * 1024: raise ValueError('Public response bound exceeded')
        data = _json(bytes(raw))
        if type(data.get('code')) is not int or data['code'] != 0: raise ValueError('Public source refused')
        rows = data['result']['data']
        if type(rows) is not list or len(rows) != 1: raise ValueError('Public snapshot unavailable')
        levels = {}
        for side in ('bids', 'asks'):
            source = rows[0][side]
            if type(source) is not list or not 0 < len(source) <= 10: raise ValueError('Depth unavailable')
            levels[side] = []
            for level in source:
                if (type(level) is not list or len(level) < 2 or type(level[0]) is not str
                        or type(level[1]) is not str or number(level[0]) <= 0 or number(level[1]) < 0):
                    raise ValueError('Depth contains invalid numbers')
                levels[side].append(level[:2])
        if number(levels['bids'][0][0]) >= number(levels['asks'][0][0]): raise ValueError('Crossed quote')
        return {'symbol': 'CRO_USDT', **levels, 'observed_at_utc': datetime.now(timezone.utc).isoformat(),
                'account_data_included': False, 'orders_sent': 0}
    except Exception:
        raise HTTPException(503, 'Public CRO/USDT depth unavailable. Account/trading state is unverified.') from None


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


