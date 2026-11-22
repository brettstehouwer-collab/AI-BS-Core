"""
AI-BS Sovereign Intelligence Ecosystem - Kraken Exchange Integration Service
Provides unified CCXT-based execution for trading (spot buy/sell), balance auditing,
inter-account transfers, and real-time market data directly against Kraken.
Adheres strictly to the AI-BS Zero-Mock Real Money standard.
"""

import os
import sys
import logging
from typing import Dict, Any, List, Optional
from pathlib import Path
from dotenv import load_dotenv
import ccxt

logger = logging.getLogger("KrakenService")

# Load environment credentials
ENV_PATHS = [
    Path(r"C:\AI-BS\.env"),
    Path(r"C:\AI-BS\Crypto-Swarm\.env")
]
for p in ENV_PATHS:
    if p.exists():
        load_dotenv(p, override=False)

KRAKEN_API_KEY = os.environ.get("KRAKEN_API_KEY", "")
KRAKEN_SECRET_KEY = os.environ.get("KRAKEN_SECRET_KEY", "") or os.environ.get("KRAKEN_PRIVATE_KEY", "")


class KrakenService:
    _instance = None

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def __init__(self, api_key: Optional[str] = None, secret: Optional[str] = None):
        self.api_key = api_key or KRAKEN_API_KEY
        self.secret = secret or KRAKEN_SECRET_KEY
        self._exchange = None

        if self.api_key and self.secret:
            try:
                self._exchange = ccxt.kraken({
                    "apiKey": self.api_key,
                    "secret": self.secret,
                    "enableRateLimit": True,
                    "timeout": 30000,
                })
                logger.info("[KrakenService] Initialized CCXT Kraken client.")
            except Exception as e:
                logger.error(f"[KrakenService] Failed to initialize Kraken client: {e}")

    def is_configured(self) -> bool:
        return bool(self._exchange and self.api_key and self.secret)

    def get_status(self) -> Dict[str, Any]:
        configured = self.is_configured()
        return {
            "status": "online" if configured else "unconfigured",
            "exchange": "Kraken",
            "api_key_configured": bool(self.api_key),
            "secret_configured": bool(self.secret),
            "zero_mock_enforced": True,
            "rate_limit_enabled": True
        }

    def get_balance(self) -> Dict[str, Any]:
        """Fetches real-time non-zero wallet balances directly from Kraken (Strict Zero-Mock)."""
        if not self.is_configured():
            return {"status": "error", "message": "Kraken API credentials not configured."}
        try:
            raw_bal = self._exchange.fetch_balance()
            total_holdings = raw_bal.get("total", {})
            free_holdings = raw_bal.get("free", {})
            used_holdings = raw_bal.get("used", {})

            # Filter non-zero assets
            active_assets = {}
            for asset, total_amt in total_holdings.items():
                if total_amt and float(total_amt) > 0.0:
                    active_assets[asset] = {
                        "asset": asset,
                        "total": float(total_amt),
                        "free": float(free_holdings.get(asset, 0.0)),
                        "used": float(used_holdings.get(asset, 0.0))
                    }

            return {
                "status": "success",
                "exchange": "Kraken",
                "timestamp": raw_bal.get("timestamp"),
                "datetime": raw_bal.get("datetime"),
                "assets_count": len(active_assets),
                "balances": active_assets,
                "zero_mock_verified": True
            }
        except Exception as e:
            logger.error(f"[KrakenService] Error fetching balance: {e}")
            return {"status": "error", "message": str(e)}

    def get_ticker(self, symbol: str) -> Dict[str, Any]:
        """Fetches live ticker quotes (bid, ask, last price) for a pair like 'SOL/USD' or 'BTC/USD'."""
        if not self.is_configured():
            # Public endpoint does not require credentials
            client = ccxt.kraken({"enableRateLimit": True})
        else:
            client = self._exchange

        try:
            formatted_sym = symbol.upper().strip()
            if "/" not in formatted_sym:
                formatted_sym = f"{formatted_sym}/USD"
            ticker = client.fetch_ticker(formatted_sym)
            return {
                "status": "success",
                "symbol": formatted_sym,
                "last": ticker.get("last"),
                "bid": ticker.get("bid"),
                "ask": ticker.get("ask"),
                "high": ticker.get("high"),
                "low": ticker.get("low"),
                "volume": ticker.get("baseVolume"),
                "percentage": ticker.get("percentage")
            }
        except Exception as e:
            logger.error(f"[KrakenService] Error fetching ticker for {symbol}: {e}")
            return {"status": "error", "message": str(e)}

    def create_order(
        self,
        symbol: str,
        side: str,
        amount: float,
        order_type: str = "market",
        price: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        Executes a verified order on Kraken.
        Side: 'buy' or 'sell'.
        Order type: 'market' or 'limit'.
        """
        from core.crypto_execution_safety import require_reconciled_execution
        require_reconciled_execution()
        if not self.is_configured():
            return {"status": "error", "message": "Kraken API credentials missing."}

        side_clean = side.lower().strip()
        if side_clean not in ["buy", "sell"]:
            return {"status": "error", "message": f"Invalid order side: '{side}'. Must be 'buy' or 'sell'."}

        sym_clean = symbol.upper().strip()
        if "/" not in sym_clean:
            sym_clean = f"{sym_clean}/USD"

        try:
            params = {}
            if order_type.lower() == "limit" and price is not None:
                order = self._exchange.create_order(sym_clean, "limit", side_clean, amount, price, params)
            else:
                order = self._exchange.create_order(sym_clean, "market", side_clean, amount, None, params)

            return {
                "status": "success",
                "exchange": "Kraken",
                "order_id": order.get("id"),
                "symbol": sym_clean,
                "side": side_clean,
                "type": order_type,
                "amount": amount,
                "price": order.get("price") or price,
                "filled": order.get("filled", 0.0),
                "remaining": order.get("remaining", amount),
                "order_status": order.get("status"),
                "raw_order": order
            }
        except Exception as e:
            logger.error(f"[KrakenService] Order execution failed: {e}")
            return {"status": "error", "message": str(e)}

    def get_open_orders(self, symbol: Optional[str] = None) -> Dict[str, Any]:
        """Returns all open orders on Kraken."""
        if not self.is_configured():
            return {"status": "error", "message": "Kraken API credentials not configured."}
        try:
            sym = symbol.upper() if symbol and "/" in symbol else None
            orders = self._exchange.fetch_open_orders(sym)
            return {"status": "success", "count": len(orders), "orders": orders}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def get_trade_history(self, symbol: Optional[str] = None, limit: int = 50) -> Dict[str, Any]:
        """Returns trade execution history from Kraken."""
        if not self.is_configured():
            return {"status": "error", "message": "Kraken API credentials not configured."}
        try:
            sym = symbol.upper() if symbol and "/" in symbol else None
            trades = self._exchange.fetch_my_trades(sym, limit=limit)
            return {"status": "success", "count": len(trades), "trades": trades}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def cancel_order(self, order_id: str, symbol: Optional[str] = None) -> Dict[str, Any]:
        """Cancels an open order by ID on Kraken."""
        if not self.is_configured():
            return {"status": "error", "message": "Kraken API credentials not configured."}
        try:
            res = self._exchange.cancel_order(order_id, symbol)
            return {"status": "success", "result": res}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def get_deposit_address(self, code: str) -> Dict[str, Any]:
        """Fetches deposit address for a cryptocurrency (e.g. 'SOL', 'BTC', 'ETH', 'USDT')."""
        if not self.is_configured():
            return {"status": "error", "message": "Kraken API credentials not configured."}
        try:
            addr_info = self._exchange.fetch_deposit_address(code.upper())
            return {"status": "success", "asset": code.upper(), "address_info": addr_info}
        except Exception as e:
            return {"status": "error", "message": str(e)}


# Global singleton instance
kraken_service = KrakenService.get_instance()
