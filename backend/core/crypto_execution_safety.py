"""Fail-closed containment of unreconciled legacy trading implementations.

No credentials, exchange clients, database initialization, or network on import.
This module deliberately provides no live activation or resume mechanism.
"""
import json
import os
import tempfile
from pathlib import Path


HALT_FILE = Path(__file__).resolve().parents[2] / "state" / "crypto_trading_halt.json"
HOLD_REASON = "Reconciliation required: fills, fees, slippage and shared risk limits are unverified."


class CryptoDispatchBlocked(RuntimeError):
    pass


def execution_status():
    return {"dispatch_enabled": False, "reconciliation_required": True,
            "halt_marker_present": HALT_FILE.exists(), "reason": HOLD_REASON}


def halt_trading():
    """Persist an operator halt without storing free-form text or secrets."""
    HALT_FILE.parent.mkdir(parents=True, exist_ok=True)
    # Unique temporary file and fsync: a failed write must propagate to the caller.
    with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=HALT_FILE.parent,
                                     prefix="crypto_halt_", suffix=".tmp", delete=False) as f:
        json.dump({"halted": True, "reason": "operator_halt"}, f)
        f.flush()
        os.fsync(f.fileno())
        temporary = f.name
    os.replace(temporary, HALT_FILE)
    return execution_status()


def require_reconciled_execution():
    """Hard circuit breaker; missing/corrupt state and credentials cannot open it."""
    raise CryptoDispatchBlocked(HOLD_REASON)


async def execute_trade_protocol(exchange, symbol, side, amount, price=None):
    """Reject before any network request or optimistic monetary state mutation.

    The legacy callers cannot safely consume partial fills. A retrying wrapper
    would risk duplicate orders. Keep this closed until fill-based accounting,
    durable order intent/recovery, and exchange-backed reconciliation exist.
    """
    require_reconciled_execution()
