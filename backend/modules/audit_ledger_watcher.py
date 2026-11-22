"""
AI-BS CDZ Active Source Polling Watcher Daemon
Continuously monitors source directories (C:/AI-BS, Desktop/PenitsCradle)
for new or modified cryptographic audit ledger JSON files every 5 seconds.
Idempotently ingests blocks into C:/AI-BS/database/aibs_master.db.
"""

import os
import glob
import time
import threading
import logging
from contextlib import contextmanager
from typing import Dict, List, Any, Optional

from database.cdz_audit_db import ingest_ledger_file, get_cdz_summary

logger = logging.getLogger("ai_bs.audit_ledger_watcher")


class CDZScanDraining(RuntimeError):
    """Explicit host drain has closed new scan admission."""

WATCH_DIRS = [
    r"C:\AI-BS",
    os.path.join(os.path.expanduser("~"), "Desktop", "PenitsCradle")
]


class CDZAuditLedgerWatcher:
    def __init__(self, poll_interval: float = 5.0, *, store=None, watch_dirs=None):
        if store is not None and getattr(store, "name", None) != "cdz_audit":
            raise ValueError("CDZ watcher requires the named cdz_audit store")
        if isinstance(watch_dirs, (str, bytes)):
            raise ValueError("watch_dirs must be a sequence of directory paths")
        self.poll_interval = poll_interval
        self._store = store
        # None intentionally re-reads WATCH_DIRS on each scan/status, preserving
        # legacy discovery when directories appear after construction.
        self._watch_dirs = None if watch_dirs is None else tuple(os.fspath(d) for d in watch_dirs)
        self.watch_dirs = self._current_watch_dirs()
        self._scan_lock = threading.Lock()
        self._seen_files: Dict[str, float] = {}  # filepath -> mtime
        self._stop_waiters = 0
        self._stop_event = threading.Event()
        self._thread: Optional[threading.Thread] = None
        self._lock = threading.Lock()
        self._drain_condition = threading.Condition(self._lock)
        self._scan_owners = {}
        self._accepting_scans = True
        self._drain_waiters = 0
        self._host_owner = None
        self._host_join_pending = False
        self.last_scan_time: Optional[float] = None
        self.total_scans = 0
        self.files_tracked = 0
        self.new_blocks_ingested = 0

    @property
    def store(self):
        """Host identity check; binding cannot be changed through this API."""
        return self._store

    def _current_watch_dirs(self):
        candidates = WATCH_DIRS if self._watch_dirs is None else self._watch_dirs
        return [d for d in candidates if os.path.exists(d)]

    def start(self) -> bool:
        """Start one worker; a live/draining worker or stop waiter refuses overlap."""
        with self._lock:
            if not self._accepting_scans or self._stop_waiters or (self._thread is not None and self._thread.is_alive()):
                return False
            self._stop_event = threading.Event()
            worker = threading.Thread(target=self._run_loop, args=(self._stop_event,),
                                      daemon=True, name="CDZAuditWatcherThread")
            self._thread = worker
            try:
                worker.start()
            except BaseException:
                self._thread = None
                raise
            logger.info("CDZ Audit Ledger Watcher daemon started.")
            return True

    def stop(self, timeout: float = 2.0) -> bool:
        """Signal and join the captured worker; timeout never permits replacement."""
        if timeout < 0:
            raise ValueError("Nonnegative stop timeout required")
        with self._lock:
            worker = self._thread
            if worker is None or not worker.is_alive():
                return True
            self._stop_event.set()
            self._stop_waiters += 1
        try:
            # A callback may request its own stop. It remains alive/draining
            # until it returns, so self-stop must not join or report completion.
            if worker is threading.current_thread():
                return False
            worker.join(timeout=timeout)
            drained = not worker.is_alive()
            if drained:
                logger.info("CDZ Audit Ledger Watcher daemon stopped.")
            return drained
        finally:
            with self._lock:
                self._stop_waiters -= 1

    def _run_loop(self, stop_event: threading.Event) -> None:
        while not stop_event.is_set():
            try:
                self.scan_now()
            except CDZScanDraining:
                break
            except Exception:
                logger.exception("CDZ source polling scan failed; next poll may retry")
            stop_event.wait(self.poll_interval)

    def scan_now(self) -> Dict[str, Any]:
        """Serialize source discovery, ingestion and seen-state on this watcher."""
        with self._scan_admission():
            with self._scan_lock:
                return self._scan_now_locked()

    def scan_and_summarize(self, *, client_id="stehouwer_publishing"):
        """One admitted host request, including its final database reader.

        Synchronous: callers run it off the ASGI event loop. Cancellation of an
        awaiting request cannot retire this lease while its worker still runs.
        """
        with self._scan_admission():
            with self._scan_lock:
                result = self._scan_now_locked()
            summary = get_cdz_summary(client_id=client_id, store=self.store)
            return result, summary

    @contextmanager
    def _scan_admission(self):
        owner = threading.get_ident()
        with self._lock:
            if not self._accepting_scans:
                raise CDZScanDraining("CDZ source scanning is draining.")
            self._scan_owners[owner] = self._scan_owners.get(owner, 0) + 1
        try:
            yield
        finally:
            with self._drain_condition:
                self._scan_owners[owner] -= 1
                if not self._scan_owners[owner]:
                    del self._scan_owners[owner]
                self._drain_condition.notify_all()

    def begin_drain(self, *, owner=None):
        """Close admission before a host waits or closes its selected store."""
        with self._lock:
            if owner is not None:
                if self._host_owner is not owner:
                    raise ValueError("CDZ drain owner does not match")
                self._host_join_pending = True
            self._accepting_scans = False
            self._stop_event.set()

    def finish_host_drain(self, owner):
        """Retire the host join reservation only after its owned task terminates."""
        with self._lock:
            if self._host_owner is not owner:
                raise ValueError("CDZ drain owner does not match")
            self._host_join_pending = False

    def drain(self, timeout=2.0):
        """Wait for admitted manual/poll work, including request summary reads.

        False means the host must keep the store open. This never cancels a
        transaction, discards a worker handle, or closes a host-owned store.
        """
        if timeout < 0:
            raise ValueError("Nonnegative drain timeout required")
        deadline = time.monotonic() + timeout
        with self._lock:
            self._accepting_scans = False
            self._stop_event.set()
            self._drain_waiters += 1
        try:
            with self._drain_condition:
                if threading.get_ident() in self._scan_owners:
                    return False
                while self._scan_owners:
                    remaining = deadline - time.monotonic()
                    if remaining <= 0:
                        return False
                    self._drain_condition.wait(remaining)
            return self.stop(timeout=max(0, deadline - time.monotonic()))
        finally:
            with self._lock:
                self._drain_waiters -= 1

    def bind_host(self, owner):
        """One trusted host owns subsequent epochs, including the close gap."""
        if owner is None:
            raise ValueError("Explicit CDZ host owner required")
        with self._lock:
            if self._host_owner is owner:
                return True
            if self._host_owner is not None or self._scan_owners or self._drain_waiters or (self._thread is not None and self._thread.is_alive()):
                return False
            self._host_owner = owner
            return True

    def resume_scans(self, *, owner=None):
        """Explicit next host epoch; never resumes while prior work is alive."""
        with self._lock:
            if self._host_owner is not None and owner is not self._host_owner:
                return False
            if self._host_join_pending or self._scan_owners or self._drain_waiters or self._stop_waiters or (self._thread is not None and self._thread.is_alive()):
                return False
            self._accepting_scans = True
            return True

    def _scan_now_locked(self) -> Dict[str, Any]:
        scanned_count = 0
        ingested_count = 0
        files_evaluated = []
        scan_failed = False

        # Patterns to check
        patterns = [
            "*audit_ledger*.json",
            "penitscradle*.json",
            "*cdz*.json"
        ]

        found_files = []
        for watch_dir in self._current_watch_dirs():
            if not os.path.exists(watch_dir):
                continue
            for pat in patterns:
                found_files.extend(glob.glob(os.path.join(watch_dir, pat)))

        found_files = list(set(found_files))
        scanned_count = len(found_files)

        for fpath in found_files:
            try:
                mtime = os.path.getmtime(fpath)
                last_mtime = self._seen_files.get(fpath)
                if last_mtime is None or mtime > last_mtime:
                    # New or modified file
                    if self.store is None:
                        new_b, total_b, valid = ingest_ledger_file(fpath)
                    else:
                        new_b, total_b, valid = ingest_ledger_file(
                            fpath, store=self.store, raise_on_read_error=True
                        )
                    self._seen_files[fpath] = mtime
                    ingested_count += new_b
                    files_evaluated.append({
                        "path": fpath,
                        "new_blocks": new_b,
                        "total_blocks": total_b,
                        "valid": valid
                    })
            except Exception as e:
                scan_failed = True
                logger.error(f"Error evaluating ledger file {fpath}: {e}")

        with self._lock:
            self.last_scan_time = time.time()
            self.total_scans += 1
            self.files_tracked = len(self._seen_files)
            self.new_blocks_ingested += ingested_count

        if scan_failed and self.store is not None:
            # No local paths/details cross the public host error boundary. Failed
            # paths remain unseen so a recovered store can retry next time.
            raise RuntimeError("Shared-store source scan failed")

        return {
            "status": "success",
            "timestamp": self.last_scan_time,
            "scanned_files_count": scanned_count,
            "new_blocks_ingested": ingested_count,
            "files_evaluated": files_evaluated
        }

    def get_status(self) -> Dict[str, Any]:
        with self._lock:
            running = self._thread is not None and self._thread.is_alive()
            return {
                "running": running,
                "stopping": running and self._stop_event.is_set(),
                "accepting_scans": self._accepting_scans,
                "draining": not self._accepting_scans,
                "active_scans": sum(self._scan_owners.values()),
                "host_bound": self._host_owner is not None,
                "host_join_pending": self._host_join_pending,
                "poll_interval_seconds": self.poll_interval,
                "watch_dirs": self._current_watch_dirs(),
                "last_scan_time": self.last_scan_time,
                "total_scans": self.total_scans,
                "files_tracked": self.files_tracked,
                "new_blocks_ingested_session": self.new_blocks_ingested
            }


cdz_watcher = CDZAuditLedgerWatcher(poll_interval=5.0)
