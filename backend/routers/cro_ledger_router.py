from security.host_control_access import AdminHostControlRoute
"""
FastAPI Router for CRO Quantitative Macro Ledger & Predictive Pattern Analytics (v5.154.0)
Mounted under /api/crypto/cro
"""

import os
import sqlite3
import requests
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Query, HTTPException, Body
from core.cro_quantitative_ledger import (
    get_db, log_trade_entry, log_price_snapshot, analyze_patterns_and_predict
)

router = APIRouter(route_class=AdminHostControlRoute, prefix="/api/crypto/cro", tags=["CRO Quantitative Macro Ledger"])

def fetch_latest_crypto_news() -> str:
    """Fetches top current crypto/macro headline for automated trade correlation."""
    raise RuntimeError("External market/news reads held pending explicit provider authorization.")
    try:
        url = "https://feeds.bbci.co.uk/news/technology/rss.xml"
        res = requests.get(url, timeout=3)
        if res.status_code == 200 and "<item>" in res.text:
            import xml.etree.ElementTree as ET
            root = ET.fromstring(res.text)
            item = root.find(".//item/title")
            if item is not None and item.text:
                return item.text.strip()
    except Exception:
        pass
    return "Global Market Macro Baseline"

@router.get("/ledger")
async def get_trade_ledger(limit: int = Query(50, ge=1, le=500), offset: int = Query(0, ge=0)):
    raise HTTPException(503, "CRO ledger held: verified ownership, decimal fill evidence and explicit provider authorization are required.")
    conn = get_db()
    cur = conn.cursor()
    cur.execute("""
        SELECT * FROM cro_trade_ledger
        ORDER BY id DESC
        LIMIT ? OFFSET ?;
    """, (limit, offset))
    rows = [dict(r) for r in cur.fetchall()]
    
    cur.execute("SELECT COUNT(*) as count, SUM(total_usd) as volume, SUM(pnl_usd) as total_pnl FROM cro_trade_ledger")
    summary = dict(cur.fetchone())
    conn.close()
    
    return {
        "symbol": "CRO/USD",
        "total_trades": summary["count"] or 0,
        "total_volume_usd": summary["volume"] or 0.0,
        "total_pnl_usd": summary["total_pnl"] or 0.0,
        "trades": rows
    }

@router.post("/trade")
async def record_trade(
    trade_type: str = Body(..., description="'BUY', 'SELL', 'DCA_IN', 'TAKE_PROFIT'"),
    price: float = Body(..., description="Execution price in USD"),
    amount: float = Body(..., description="Amount of CRO traded"),
    symbol: str = Body("CRO/USD"),
    strategy_trigger: str = Body("MANUAL_ENTRY"),
    headline: Optional[str] = Body(None),
    macro_sentiment: float = Body(0.0),
    notes: str = Body("")
):
    raise HTTPException(503, "CRO ledger held: verified ownership, decimal fill evidence and explicit provider authorization are required.")
    if not headline:
        headline = fetch_latest_crypto_news()
        
    trade_id = log_trade_entry(
        trade_type=trade_type,
        price=price,
        amount=amount,
        symbol=symbol,
        strategy_trigger=strategy_trigger,
        correlated_news=headline,
        macro_sentiment=macro_sentiment,
        notes=notes
    )
    return {
        "status": "success",
        "trade_id": trade_id,
        "symbol": symbol,
        "trade_type": trade_type,
        "price": price,
        "amount": amount,
        "total_usd": round(price * amount, 4),
        "correlated_headline": headline
    }

@router.get("/history")
async def get_price_history(limit: int = Query(100, ge=1, le=1000)):
    raise HTTPException(503, "CRO ledger held: verified ownership, decimal fill evidence and explicit provider authorization are required.")
    conn = get_db()
    cur = conn.cursor()
    cur.execute("""
        SELECT * FROM cro_price_history
        ORDER BY id DESC
        LIMIT ?;
    """, (limit,))
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    return {"symbol": "CRO/USD", "count": len(rows), "history": rows}

@router.get("/predict")
async def get_pattern_prediction(current_price: Optional[float] = Query(None)):
    raise HTTPException(503, "CRO ledger held: verified ownership, decimal fill evidence and explicit provider authorization are required.")
    if current_price is None:
        # Fetch live price from Crypto.com
        try:
            res = requests.get("https://api.crypto.com/exchange/v1/public/get-tickers", timeout=3)
            if res.status_code == 200:
                tickers = res.json().get("result", {}).get("data", [])
                for t in tickers:
                    if t.get("i") in ["CRO_USD", "CRO_USDT"]:
                        current_price = float(t.get("a", 0.056))
                        break
        except Exception:
            current_price = 0.056
            
    current_price = current_price or 0.056
    analysis = analyze_patterns_and_predict(current_price)
    return analysis

@router.post("/snapshot")
async def record_live_snapshot(
    price: float = Body(...),
    bid: float = Body(0.0),
    ask: float = Body(0.0),
    volume_24h: float = Body(0.0),
    headline: Optional[str] = Body(None),
    sentiment: str = Body("NEUTRAL")
):
    raise HTTPException(503, "CRO ledger held: verified ownership, decimal fill evidence and explicit provider authorization are required.")
    if not headline:
        headline = fetch_latest_crypto_news()
    log_price_snapshot(price=price, bid=bid, ask=ask, volume_24h=volume_24h, headline=headline, sentiment=sentiment)
    return {"status": "snapshot_recorded", "price": price, "headline": headline}
