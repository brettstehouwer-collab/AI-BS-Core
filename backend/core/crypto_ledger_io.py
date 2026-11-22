"""Strict legacy JSON I/O. This does not certify historical fills or balances."""
import json
import math
import os
import tempfile
from pathlib import Path


class LedgerIntegrityError(RuntimeError):
    pass


def validate_ledger(ledger):
    if not isinstance(ledger, dict) or not isinstance(ledger.get("positions"), dict):
        raise LedgerIntegrityError("Ledger positions are missing or malformed")
    for position in ledger["positions"].values():
        if not isinstance(position, dict):
            raise LedgerIntegrityError("Malformed position")
        for key in ("amount", "avg_buy_price", "long_term_vault"):
            value = position.get(key, 0)
            try:
                valid = not isinstance(value, bool) and isinstance(value, (int, float)) and math.isfinite(value) and value >= 0
            except OverflowError:
                valid = False
            if not valid:
                raise LedgerIntegrityError("Invalid monetary value in position")
    # Reject NaN/Infinity anywhere, including risk/TWAP fields.
    try:
        json.dumps(ledger, allow_nan=False)
    except (ValueError, TypeError) as exc:
        raise LedgerIntegrityError("Ledger contains non-JSON or non-finite values") from exc
    return ledger


def read_ledger(path):
    try:
        with Path(path).open(encoding="utf-8") as f:
            return validate_ledger(json.load(f))
    except (OSError, ValueError, TypeError) as exc:
        raise LedgerIntegrityError("Ledger unavailable or corrupt; reconciliation required") from exc


def write_ledger(path, ledger):
    validate_ledger(ledger)
    path = Path(path)
    with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=path.parent,
                                     prefix=path.name + ".", suffix=".tmp", delete=False) as f:
        json.dump(ledger, f, indent=4, allow_nan=False)
        f.flush()
        os.fsync(f.fileno())
        temporary = f.name
    # Propagate failure, preserve original and the diagnostic temporary file.
    os.replace(temporary, path)
