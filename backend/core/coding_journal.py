"""Flush and atomically promote caller-owned coding metadata, preserving failures.

Callers own path authorization and task/repository locks. This retries only the
same Windows file promotion, never a task, command, inference or application.
It does not grant filesystem isolation or universal power-loss guarantees.
"""
from __future__ import annotations

import json
import math
import os
from pathlib import Path
import time
import uuid


def write_json_record(path, record, *, retry_seconds=0.5, exclusive=False):
    """Preserve the previous record and staged bytes if replacement cannot finish."""
    if (type(retry_seconds) not in (int, float) or not math.isfinite(retry_seconds)
            or not 0 <= retry_seconds <= 1):
        raise ValueError('Journal replacement retry budget must be between zero and one second')
    if type(exclusive) is not bool:
        raise ValueError('Exclusive journal creation must be a boolean')
    # Serialization/encoding failures must occur before creating any file.
    encoded = json.dumps(record, indent=2, allow_nan=False).encode('utf-8')
    path = Path(path)
    if exclusive:
        # Immutable entries need no rename. Partial/unsynced bytes remain on
        # failure; callers must verify evidence and never overwrite or replay.
        with path.open('xb') as file:
            file.write(encoded)
            file.flush()
            os.fsync(file.fileno())
        return
    staged = path.with_name(path.stem + '.' + uuid.uuid4().hex + '.tmp')
    with staged.open('xb') as file:
        file.write(encoded)
        file.flush()
        os.fsync(file.fileno())
    deadline = time.monotonic() + retry_seconds
    delay = .01
    while True:
        try:
            os.replace(staged, path)
            return
        except OSError as error:
            if os.name != 'nt' or getattr(error, 'winerror', None) not in {5, 32, 33}:
                raise
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise
            time.sleep(min(delay, remaining))
            delay = min(delay * 2, .05)
