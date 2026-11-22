"""Bounded, persistent Ollama visibility diagnostics for AI-BS.

Importing this module performs no I/O. A run only reads Ollama/process/model
state and writes its own additive audit tables in the existing master database.
It never generates text, edits models, launches processes, or restarts services.
Repair and general-purpose autonomous execution are deliberately deferred.
"""

from __future__ import annotations

import argparse
import hashlib
import ipaddress
import json
import ntpath
import os
from pathlib import Path
import re
import sqlite3
import subprocess
import sys
import time
from datetime import datetime, timezone
from typing import Any
import urllib.error
import urllib.request
import uuid


MASTER_DB_PATH = Path(r"C:\AI-BS\backend\aibs_master.db")
MODEL_STORE = Path(r"C:\AI-BS\models\ollama")
MODEL_TAG = "stehouwer_llm:latest"
PORTS = (11434, 11435)
MAX_ATTEMPTS = 2  # Total attempts, including attempts interrupted by a crash.
LEASE_SECONDS = 120.0
HTTP_TIMEOUT_SECONDS = 5.0
MAX_JSON_BYTES = 1024 * 1024
TERMINAL_STATES = frozenset(("COMPLETED", "FAILED"))


class DiagnosticFailure(Exception):
    """A fixed, safe diagnostic error suitable for the local audit log."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


class LeaseLost(DiagnosticFailure):
    def __init__(self) -> None:
        super().__init__("LEASE_LOST", "Run ownership expired or changed; no further action was taken.")


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def _utc(timestamp: float) -> str:
    return datetime.fromtimestamp(timestamp, timezone.utc).isoformat()


def _json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=True, separators=(",", ":"), sort_keys=True)


def _windows_path(value: str | Path) -> str:
    return ntpath.normcase(ntpath.normpath(str(value)))


class AIBSTaskController:
    """One fixed diagnostic with persisted attempts and exclusive run ownership.

    Keyword paths exist for isolated verification. The CLI uses fixed production
    paths and accepts no arbitrary executable, database, port, or HTTP target.
    """

    def __init__(
        self,
        task_id: str,
        goal: str,
        *,
        db_path: Path | str = MASTER_DB_PATH,
        model_store: Path | str = MODEL_STORE,
        expected_executable: Path | str | None = None,
    ) -> None:
        if not re.fullmatch(r"[A-Za-z0-9_.:-]{1,128}", task_id):
            raise ValueError("task_id must contain 1-128 letters, digits, dots, underscores, colons, or hyphens.")
        if not isinstance(goal, str) or not goal.strip() or len(goal) > 2000:
            raise ValueError("goal must contain 1-2000 characters.")
        self.task_id = task_id
        self.goal = goal.strip()
        self.max_retries = MAX_ATTEMPTS  # Compatibility with the proposed class.
        self.db_path = Path(db_path)
        self.model_store = Path(model_store)
        local_app_data = Path(os.environ.get("LOCALAPPDATA", str(Path.home() / "AppData" / "Local")))
        self.expected_executable = Path(expected_executable or local_app_data / "Programs" / "Ollama" / "ollama.exe")
        self.manifest_path = self.model_store / "manifests" / "registry.ollama.ai" / "library" / "stehouwer_llm" / "latest"
        self.last_result: dict[str, Any] | None = None
        self._clock = time.time
        self._sleep = time.sleep

    def _connect(self) -> sqlite3.Connection:
        if not self.db_path.is_file():
            raise DiagnosticFailure("MASTER_DB_MISSING", "The existing AI-BS master database was not found; no database was created.")
        conn = sqlite3.connect(self.db_path.resolve().as_uri() + "?mode=rw", uri=True, timeout=5, isolation_level=None)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys=ON")
        conn.execute("PRAGMA busy_timeout=5000")
        return conn

    def _initialize(self) -> None:
        conn = self._connect()
        try:
            names = {row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
            if not {"client_profiles", "vault_data"}.issubset(names):
                raise DiagnosticFailure("MASTER_DB_IDENTITY", "Database does not match the AI-BS master schema; no diagnostic tables were created.")
            conn.execute("BEGIN IMMEDIATE")
            conn.execute("""CREATE TABLE IF NOT EXISTS aibs_task_runs (
                task_id TEXT PRIMARY KEY,
                goal TEXT NOT NULL,
                state TEXT NOT NULL,
                attempts INTEGER NOT NULL DEFAULT 0 CHECK(attempts BETWEEN 0 AND 2),
                lease_owner TEXT,
                lease_expires_at REAL,
                expected_manifest_digest TEXT,
                result_json TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )""")
            conn.execute("""CREATE TABLE IF NOT EXISTS aibs_task_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                task_id TEXT NOT NULL REFERENCES aibs_task_runs(task_id),
                attempt INTEGER NOT NULL,
                event TEXT NOT NULL,
                details_json TEXT NOT NULL,
                created_at TEXT NOT NULL
            )""")
            required = {
                "aibs_task_runs": {"task_id", "goal", "state", "attempts", "lease_owner", "lease_expires_at", "expected_manifest_digest", "result_json", "created_at", "updated_at"},
                "aibs_task_events": {"id", "task_id", "attempt", "event", "details_json", "created_at"},
            }
            for table, expected in required.items():
                actual = {row[1] for row in conn.execute(f"PRAGMA table_info({table})")}
                if not expected.issubset(actual):
                    raise DiagnosticFailure("TASK_SCHEMA_MISMATCH", "Existing task audit tables have an incompatible schema.")
            conn.commit()
        except BaseException:
            if conn.in_transaction:
                conn.rollback()
            raise
        finally:
            conn.close()

    def _event(self, conn: sqlite3.Connection, attempt: int, event: str, details: dict[str, Any]) -> None:
        conn.execute(
            "INSERT INTO aibs_task_events(task_id,attempt,event,details_json,created_at) VALUES(?,?,?,?,?)",
            (self.task_id, attempt, event, _json(details), _utc(self._clock())),
        )

    def _report(self, state: str, attempts: int, verification: dict[str, Any], *, cached: bool = False) -> dict[str, Any]:
        return {
            "task_id": self.task_id, "goal": self.goal, "state": state,
            "attempts": attempts, "max_attempts": MAX_ATTEMPTS, "cached": cached,
            "checked_at": _utc(self._clock()), "diagnostic": "ollama_model_visibility",
            "repair_supported": False, "repair_performed": False,
            "verification": verification,
            "limits": ["No inference, model blob integrity, GPU offload, or end-to-end BS-Chat test was performed."],
        }

    def _claim(self, owner: str) -> dict[str, Any] | None:
        conn = self._connect()
        try:
            conn.execute("BEGIN IMMEDIATE")
            now = self._clock()
            row = conn.execute("SELECT * FROM aibs_task_runs WHERE task_id=?", (self.task_id,)).fetchone()
            if row is not None and row["goal"] != self.goal:
                raise DiagnosticFailure("TASK_ID_CONFLICT", "This task_id belongs to a different goal; use a new task_id.")
            if row is not None and row["state"] in TERMINAL_STATES:
                result = json.loads(row["result_json"])
                result["cached"] = True
                conn.commit()
                return result
            if row is not None and row["lease_owner"] and (row["lease_expires_at"] or 0) > now:
                result = self._report("BUSY", row["attempts"], {"passed": False, "error": {"code": "ACTIVE_LEASE", "message": "Another diagnostic owns this task; no attempt was consumed."}})
                conn.commit()
                return result
            if row is None:
                conn.execute("INSERT INTO aibs_task_runs(task_id,goal,state,created_at,updated_at) VALUES(?,?,'QUEUED',?,?)", (self.task_id, self.goal, _utc(now), _utc(now)))
                self._event(conn, 0, "CREATED", {"max_attempts": MAX_ATTEMPTS, "repair_supported": False})
                attempts = 0
            else:
                attempts = row["attempts"]
                if row["lease_owner"]:
                    self._event(conn, attempts, "EXPIRED_LEASE_RECOVERED", {"interrupted_attempt_counted": True})
            if attempts >= MAX_ATTEMPTS:
                result = self._report("FAILED", attempts, {"passed": False, "error": {"code": "ATTEMPTS_EXHAUSTED", "message": "Both attempts were already consumed, including interrupted work."}})
                conn.execute("UPDATE aibs_task_runs SET state='FAILED',lease_owner=NULL,lease_expires_at=NULL,result_json=?,updated_at=? WHERE task_id=?", (_json(result), _utc(now), self.task_id))
                self._event(conn, attempts, "FAILED", result["verification"])
                conn.commit()
                return result
            conn.execute("UPDATE aibs_task_runs SET state='INSPECTING',lease_owner=?,lease_expires_at=?,updated_at=? WHERE task_id=?", (owner, now + LEASE_SECONDS, _utc(now), self.task_id))
            self._event(conn, attempts, "CLAIMED", {"lease_seconds": LEASE_SECONDS})
            conn.commit()
            return None
        except BaseException:
            if conn.in_transaction:
                conn.rollback()
            raise
        finally:
            conn.close()

    def _owned_row(self, conn: sqlite3.Connection, owner: str) -> sqlite3.Row:
        row = conn.execute("SELECT * FROM aibs_task_runs WHERE task_id=?", (self.task_id,)).fetchone()
        if row is None or row["lease_owner"] != owner or (row["lease_expires_at"] or 0) <= self._clock() or row["state"] in TERMINAL_STATES:
            raise LeaseLost()
        return row

    def _begin_attempt(self, owner: str) -> int:
        conn = self._connect()
        try:
            conn.execute("BEGIN IMMEDIATE")
            row = self._owned_row(conn, owner)
            if row["attempts"] >= MAX_ATTEMPTS:
                raise DiagnosticFailure("ATTEMPTS_EXHAUSTED", "Both attempts have been consumed.")
            attempt = row["attempts"] + 1
            now = self._clock()
            conn.execute("UPDATE aibs_task_runs SET attempts=?,state='INSPECTING',lease_expires_at=?,updated_at=? WHERE task_id=? AND lease_owner=?", (attempt, now + LEASE_SECONDS, _utc(now), self.task_id, owner))
            self._event(conn, attempt, "ATTEMPT_STARTED", {})
            conn.commit()
            return attempt
        except BaseException:
            if conn.in_transaction:
                conn.rollback()
            raise
        finally:
            conn.close()

    def _pin_manifest(self, owner: str, digest: str) -> None:
        conn = self._connect()
        try:
            conn.execute("BEGIN IMMEDIATE")
            row = self._owned_row(conn, owner)
            if row["expected_manifest_digest"] is not None and row["expected_manifest_digest"] != digest:
                raise DiagnosticFailure("MANIFEST_CHANGED", "The registered model manifest changed since this task began.")
            conn.execute("UPDATE aibs_task_runs SET expected_manifest_digest=?,state='VERIFYING',updated_at=? WHERE task_id=? AND lease_owner=?", (digest, _utc(self._clock()), self.task_id, owner))
            conn.commit()
        except BaseException:
            if conn.in_transaction:
                conn.rollback()
            raise
        finally:
            conn.close()

    def _finish_attempt(self, owner: str, verification: dict[str, Any]) -> dict[str, Any]:
        conn = self._connect()
        try:
            conn.execute("BEGIN IMMEDIATE")
            row = self._owned_row(conn, owner)
            passed = verification.get("passed") is True
            state = "COMPLETED" if passed else ("FAILED" if row["attempts"] >= MAX_ATTEMPTS else "RETRYING")
            result = self._report(state, row["attempts"], verification)
            final = state in TERMINAL_STATES
            conn.execute("UPDATE aibs_task_runs SET state=?,lease_owner=?,lease_expires_at=?,result_json=?,updated_at=? WHERE task_id=? AND lease_owner=?", (state, None if final else owner, None if final else self._clock() + LEASE_SECONDS, _json(result), _utc(self._clock()), self.task_id, owner))
            self._event(conn, row["attempts"], state, verification)
            conn.commit()
            return result
        except BaseException:
            if conn.in_transaction:
                conn.rollback()
            raise
        finally:
            conn.close()

    def _read_manifest(self) -> str:
        try:
            resolved = self.manifest_path.resolve(strict=True)
            if not resolved.is_relative_to(self.model_store.resolve(strict=True)) or not resolved.is_file():
                raise DiagnosticFailure("MANIFEST_PATH", "Model manifest is outside the configured model store.")
            with resolved.open("rb") as source:
                raw = source.read(MAX_JSON_BYTES + 1)
            if len(raw) > MAX_JSON_BYTES:
                raise DiagnosticFailure("MANIFEST_TOO_LARGE", "Model manifest exceeds the diagnostic size limit.")
            parsed = json.loads(raw)
            if not isinstance(parsed, dict) or parsed.get("schemaVersion") != 2 or not isinstance(parsed.get("config"), dict) or not isinstance(parsed.get("layers"), list):
                raise DiagnosticFailure("MANIFEST_INVALID", "Model manifest has an unexpected structure.")
            return hashlib.sha256(raw).hexdigest()
        except DiagnosticFailure:
            raise
        except (OSError, ValueError, UnicodeError) as exc:
            raise DiagnosticFailure("MANIFEST_UNAVAILABLE", "The existing model manifest could not be read and parsed.") from exc

    def _read_listeners(self) -> list[dict[str, Any]]:
        # The fixed script contains no user input and never includes CommandLine
        # or environment values. Query all Listen addresses to catch broad binds.
        script = r"""$ErrorActionPreference = 'Stop'
$selectedPorts = @(11434, 11435)
$listeners = @(Get-NetTCPConnection -State Listen -ErrorAction Stop | Where-Object { $_.LocalPort -in $selectedPorts })
$records = @($listeners | ForEach-Object {
    $listenerRecord = $_
    $ownerProcess = Get-CimInstance Win32_Process -Filter ('ProcessId=' + [string]$listenerRecord.OwningProcess) -ErrorAction Stop
    if ($null -eq $ownerProcess) { throw 'Listener process disappeared.' }
    [PSCustomObject]@{
        address = [string]$listenerRecord.LocalAddress
        port = [int]$listenerRecord.LocalPort
        pid = [int]$listenerRecord.OwningProcess
        name = [string]$ownerProcess.Name
        executable_path = [string]$ownerProcess.ExecutablePath
        creation_time = $ownerProcess.CreationDate.ToUniversalTime().ToString('o')
    }
})
ConvertTo-Json -InputObject @{ listeners = $records } -Depth 5 -Compress
"""
        try:
            result = subprocess.run(
                ["powershell.exe", "-NoProfile", "-NonInteractive", "-Command", script],
                capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=10,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
            )
        except (OSError, subprocess.SubprocessError) as exc:
            raise DiagnosticFailure("LISTENER_QUERY_FAILED", "Windows listener ownership could not be inspected.") from exc
        if result.returncode != 0 or len(result.stdout.encode("utf-8")) > MAX_JSON_BYTES:
            raise DiagnosticFailure("LISTENER_QUERY_FAILED", "Windows listener ownership query did not complete successfully.")
        try:
            payload = json.loads(result.stdout)
            records = payload["listeners"]
            if not isinstance(records, list) or len(records) > 64 or not all(isinstance(item, dict) for item in records):
                raise ValueError("Unexpected listener records")
            return records
        except (ValueError, KeyError, TypeError) as exc:
            raise DiagnosticFailure("LISTENER_RESPONSE_INVALID", "Windows listener ownership response was invalid.") from exc

    def _listener_identity(self, records: list[dict[str, Any]], port: int) -> dict[str, Any]:
        selected = [item for item in records if item.get("port") == port]
        if not selected:
            raise DiagnosticFailure("LISTENER_ABSENT", f"No listening process was found on port {port}; repair is deferred.")
        identities = set()
        addresses = set()
        for item in selected:
            try:
                address = ipaddress.ip_address(item["address"])
                if not address.is_loopback:
                    raise DiagnosticFailure("NON_LOOPBACK_LISTENER", f"Port {port} has a listener outside loopback.")
                pid = item["pid"]
                if isinstance(pid, bool) or not isinstance(pid, int) or pid <= 0:
                    raise ValueError("Invalid PID")
                exe = item["executable_path"]
                created = item["creation_time"]
                if not isinstance(exe, str) or not exe or not isinstance(created, str) or not created:
                    raise ValueError("Missing process identity")
                if str(item.get("name", "")).casefold() != "ollama.exe" or _windows_path(exe) != _windows_path(self.expected_executable.resolve()):
                    raise DiagnosticFailure("FOREIGN_LISTENER", f"Port {port} is not owned by the expected Ollama executable.")
                identities.add((pid, _windows_path(exe), created))
                addresses.add(str(address))
            except DiagnosticFailure:
                raise
            except (KeyError, TypeError, ValueError) as exc:
                raise DiagnosticFailure("LISTENER_IDENTITY_INVALID", f"Port {port} has incomplete process identity information.") from exc
        if len(identities) != 1:
            raise DiagnosticFailure("AMBIGUOUS_LISTENER", f"Port {port} has multiple distinct listening process identities.")
        if "127.0.0.1" not in addresses:
            raise DiagnosticFailure("IPV4_LISTENER_ABSENT", f"Port {port} is not listening on the required IPv4 loopback address.")
        pid, exe, created = next(iter(identities))
        return {"pid": pid, "executable_path": exe, "creation_time": created, "addresses": sorted(addresses)}

    def _http_json(self, port: int, endpoint: str) -> dict[str, Any]:
        if port not in PORTS or endpoint not in ("version", "tags", "ps"):
            raise DiagnosticFailure("UNSUPPORTED_PROBE", "Only the fixed local Ollama diagnostic endpoints are allowed.")
        url = f"http://127.0.0.1:{port}/api/{endpoint}"
        opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), _NoRedirect())
        request = urllib.request.Request(url, headers={"Accept": "application/json"}, method="GET")
        try:
            with opener.open(request, timeout=HTTP_TIMEOUT_SECONDS) as response:
                if response.status != 200:
                    raise DiagnosticFailure("HTTP_STATUS", f"Port {port} did not return HTTP 200 for {endpoint}.")
                raw = response.read(MAX_JSON_BYTES + 1)
            if len(raw) > MAX_JSON_BYTES:
                raise DiagnosticFailure("HTTP_RESPONSE_TOO_LARGE", f"Port {port} returned too much diagnostic data.")
            parsed = json.loads(raw)
            if not isinstance(parsed, dict):
                raise DiagnosticFailure("HTTP_JSON_INVALID", f"Port {port} returned an unexpected JSON structure.")
            return parsed
        except DiagnosticFailure:
            raise
        except urllib.error.HTTPError as exc:
            raise DiagnosticFailure("HTTP_STATUS", f"Port {port} returned HTTP {exc.code} for {endpoint}; redirects were not followed.") from exc
        except (urllib.error.URLError, OSError, TimeoutError) as exc:
            raise DiagnosticFailure("HTTP_UNAVAILABLE", f"Port {port} did not complete the local {endpoint} request.") from exc
        except (ValueError, UnicodeError) as exc:
            raise DiagnosticFailure("HTTP_JSON_INVALID", f"Port {port} returned invalid JSON for {endpoint}.") from exc

    def _probe_once(self, expected_digest: str) -> dict[str, Any]:
        if not self.expected_executable.is_file():
            raise DiagnosticFailure("OLLAMA_EXECUTABLE_MISSING", "The pinned local Ollama executable was not found.")
        before = self._read_listeners()
        checks = []
        for port in PORTS:
            try:
                identity = self._listener_identity(before, port)
                version = self._http_json(port, "version").get("version")
                if not isinstance(version, str) or not re.fullmatch(r"[0-9]+(?:\.[0-9]+){1,3}(?:[-+][A-Za-z0-9.-]+)?", version) or len(version) > 64:
                    raise DiagnosticFailure("VERSION_INVALID", f"Port {port} returned an invalid Ollama version.")
                tags = self._http_json(port, "tags").get("models")
                if not isinstance(tags, list) or len(tags) > 4096 or not all(isinstance(model, dict) for model in tags):
                    raise DiagnosticFailure("TAGS_INVALID", f"Port {port} returned an invalid model registry.")
                matching = [model for model in tags if model.get("name", model.get("model")) == MODEL_TAG]
                if len(matching) != 1:
                    raise DiagnosticFailure("MODEL_NOT_VISIBLE", f"Port {port} does not expose exactly one {MODEL_TAG} registration.")
                digest = matching[0].get("digest")
                if not isinstance(digest, str) or digest.removeprefix("sha256:").lower() != expected_digest:
                    raise DiagnosticFailure("MODEL_DIGEST_MISMATCH", f"Port {port} exposes a different model manifest digest.")
                loaded = self._http_json(port, "ps").get("models")
                if not isinstance(loaded, list) or len(loaded) > 4096 or not all(isinstance(model, dict) for model in loaded):
                    raise DiagnosticFailure("PS_INVALID", f"Port {port} returned an invalid loaded-model list.")
                checks.append({"port": port, "passed": True, "owner": identity, "ollama_version": version, "model_count": len(tags), "registered_model": MODEL_TAG, "manifest_digest": expected_digest, "loaded_model_count": len(loaded), "target_loaded": any(model.get("name", model.get("model")) == MODEL_TAG for model in loaded)})
            except DiagnosticFailure as exc:
                checks.append({"port": port, "passed": False, "error": {"code": exc.code, "message": str(exc)}})
        # Check ownership again after HTTP, including broad-address listeners.
        after = self._read_listeners()
        for check in checks:
            if check["passed"]:
                try:
                    if self._listener_identity(after, check["port"]) != check["owner"]:
                        raise DiagnosticFailure("LISTENER_CHANGED", f"Port {check['port']} ownership changed during verification.")
                except DiagnosticFailure as exc:
                    check["passed"] = False
                    check["error"] = {"code": exc.code, "message": str(exc)}
        return {"passed": all(check["passed"] for check in checks), "ports": checks, "expected_manifest_digest": expected_digest}

    def run_diagnostic(self) -> dict[str, Any]:
        self._initialize()
        owner = uuid.uuid4().hex
        previous = self._claim(owner)
        if previous is not None:
            self.last_result = previous
            return previous
        attempt = 0
        try:
            while True:
                attempt = self._begin_attempt(owner)
                try:
                    digest = self._read_manifest()
                    self._pin_manifest(owner, digest)
                    verification = self._probe_once(digest)
                    if self._read_manifest() != digest:
                        raise DiagnosticFailure("MANIFEST_CHANGED", "The model manifest changed during verification.")
                except LeaseLost:
                    raise
                except DiagnosticFailure as exc:
                    verification = {"passed": False, "error": {"code": exc.code, "message": str(exc)}}
                except Exception as exc:
                    verification = {"passed": False, "error": {"code": "DIAGNOSTIC_ERROR", "message": f"Diagnostic could not complete ({type(exc).__name__}); no service changes were attempted."}}
                result = self._finish_attempt(owner, verification)
                if result["state"] in TERMINAL_STATES:
                    self.last_result = result
                    return result
                self._sleep(0.25)
        except LeaseLost as exc:
            result = self._report("LEASE_LOST", attempt, {"passed": False, "error": {"code": exc.code, "message": str(exc)}})
            self.last_result = result
            return result

    def run_benchmark_ollama(self) -> bool:
        """Compatibility entry point; this is a visibility check, not a benchmark."""
        return self.run_diagnostic()["state"] == "COMPLETED"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Persist a bounded, read-only Ollama model visibility diagnostic.")
    parser.add_argument("--task-id", default=None, help="Reuse a task ID to retrieve its terminal result or resume its remaining attempt budget.")
    parser.add_argument("--goal", default="Verify existing Stehouwer model visibility on both local Ollama ports.")
    parser.add_argument("--repair", action="store_true", help="Repair is deferred and this option is blocked; no process will be started.")
    args = parser.parse_args(argv)
    if args.repair:
        print(_json({"state": "BLOCKED", "error": "REPAIR_DEFERRED", "message": "Repair is not implemented. Run without --repair for the visibility diagnostic; no service or database changes were made."}))
        return 2
    task_id = args.task_id or f"OLLAMA-{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}-{uuid.uuid4().hex[:8]}"
    try:
        result = AIBSTaskController(task_id, args.goal).run_diagnostic()
    except DiagnosticFailure as exc:
        print(_json({"task_id": task_id, "state": "BLOCKED", "error": {"code": exc.code, "message": str(exc)}}))
        return 2
    except (sqlite3.Error, OSError, ValueError) as exc:
        print(_json({"task_id": task_id, "state": "BLOCKED", "error": {"code": "CONTROLLER_ERROR", "message": f"Controller could not safely continue ({type(exc).__name__})."}}))
        return 2
    print(json.dumps(result, indent=2))
    return 0 if result["state"] == "COMPLETED" else (1 if result["state"] == "FAILED" else 2)


if __name__ == "__main__":
    sys.exit(main())
