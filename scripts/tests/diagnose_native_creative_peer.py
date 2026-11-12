"""One-shot test-only peer-table diagnostics; no production retries or changes.

Frame tracing observes only the resolver's existing ownership-table sample. It
does not collect the full network table, exception messages or account context.
"""
from __future__ import annotations
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import sys
import threading
import time
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "backend"))

MODULES = [
    "scripts.tests.test_native_creative_disconnect_recovery",
    "scripts.tests.test_native_creative_peer",
    "scripts.tests.test_native_creative_pipe",
    "scripts.tests.test_native_creative_session",
    "scripts.tests.test_native_creative_project_preflight",
    "scripts.tests.test_creative_verified_context",
    "scripts.tests.test_native_creative_handoff",
    "scripts.tests.test_native_screenplay_workflow",
]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--evidence-root", required=True, type=Path)
    parser.add_argument("--expected-tests", required=True, type=int)
    args = parser.parse_args()
    destination = args.evidence_root.resolve()
    allowed = (ROOT / "backups").resolve()
    if not destination.is_relative_to(allowed) or destination.exists():
        raise SystemExit("Evidence root must be a fresh directory inside project backups")
    if sys.gettrace() is not None or threading.gettrace() is not None:
        raise SystemExit("Existing trace hooks cannot be replaced")

    import psutil
    from security.native_creative_peer import NativePeerResolver
    target_code = NativePeerResolver._owner.__code__
    baseline_reader = psutil.net_connections
    monotonic = time.monotonic
    events = []
    samples = {}
    sample_sequence = [0]
    active = {"test": None}
    trace_errors = []

    def shape(value):
        result = {"type": type(value).__name__}
        if type(value) in (tuple, list, str, bytes) or isinstance(value, tuple):
            result["length"] = len(value)
        return result

    def snapshot(frame, event, argument):
        values = frame.f_locals
        row = values.get("row")
        sample = samples[id(frame)]
        result = {
            "event": event, "test": sample["test"], "sample": sample["number"],
            "thread": threading.get_ident(), "line": frame.f_lineno,
            "seconds_since_call": monotonic() - sample["started"],
            "row_count": len(values["rows"]) if type(values.get("rows")) in (list, tuple) else None,
            "clients": sorted(values.get("clients", []), key=lambda item: (type(item).__name__, str(item))),
            "servers": sorted(values.get("servers", []), key=lambda item: (type(item).__name__, str(item))),
            "current_backend_pid": os.getpid(),
            "reader_is_original": psutil.net_connections is baseline_reader,
            "reader_type": type(psutil.net_connections).__name__,
        }
        # Only type/length information for a current row, never its addresses.
        if row is not None:
            result["current_row"] = {"type": type(row).__name__}
            for name in ("laddr", "raddr", "pid", "family", "type", "status"):
                result["current_row"][name] = shape(getattr(row, name, None))
        if event == "exception":
            exception_type = argument[0]
            result["exception_class"] = exception_type.__name__
            result["exception_module"] = exception_type.__module__
        elif event == "return":
            result["returned_owner_pid"] = argument if type(argument) is int else None
        return result

    def trace(frame, event, argument):
        if frame.f_code is not target_code:
            return None
        try:
            if event == "call":
                sample_sequence[0] += 1
                samples[id(frame)] = {"number": sample_sequence[0],
                                      "test": active["test"], "started": monotonic()}
            elif event in ("exception", "return"):
                if len(events) < 256:
                    events.append(snapshot(frame, event, argument))
                if event == "return":
                    samples.pop(id(frame), None)
        except BaseException as error:
            # Diagnostics must not change test/authorization control flow.
            if len(trace_errors) < 16:
                trace_errors.append({"class": type(error).__name__, "event": event})
        return trace

    class Result(unittest.TextTestResult):
        def startTest(self, test):
            active["test"] = test.id()
            super().startTest(test)

        def stopTest(self, test):
            super().stopTest(test)
            active["test"] = None

    suite = unittest.defaultTestLoader.loadTestsFromNames(MODULES)
    count = suite.countTestCases()
    if count != args.expected_tests:
        raise SystemExit(f"Test count changed before execution: expected{args.expected_tests}, actual{count}")
    paths = [ROOT / (module.replace(".", "/") + ".py") for module in MODULES]
    paths += [ROOT / relative for relative in (
        "backend/security/native_creative_peer.py", "backend/core/opencode_worker.py",
        "backend/security/native_creative_handoff.py", "native_studio/creative_session.py",
        "native_studio/screenplay_client.py", "scripts/tests/diagnose_native_creative_peer.py")]
    if not all(path.is_file() for path in paths):
        raise SystemExit("An intended source pin is unavailable")

    def pins():
        return {path.relative_to(ROOT).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
                for path in paths}

    before = pins()
    destination.mkdir()
    started = datetime.now(timezone.utc).isoformat()
    try:
        sys.settrace(trace)
        threading.settrace(trace)
        with (destination / "instrumented-regressions.log").open("x", encoding="utf-8") as stream:
            result = unittest.TextTestRunner(stream=stream, verbosity=2, resultclass=Result).run(suite)
    finally:
        sys.settrace(None)
        threading.settrace(None)
    after = pins()
    receipt = {
        "schema": "aibs.native-peer.diagnostic-run.v1", "started_utc": started,
        "finished_utc": datetime.now(timezone.utc).isoformat(),
        "status": "INSTRUMENTED_SUITE_PASS_ORIGINAL_FLAKE_UNEXPLAINED" if result.wasSuccessful()
                  else "INSTRUMENTED_SUITE_FAILED_DIAGNOSTICS_RETAINED",
        "python": sys.executable, "base_executable": sys._base_executable,
        "psutil_version": psutil.__version__, "modules_in_order": MODULES,
        "expected_tests": args.expected_tests, "tests_run": result.testsRun,
        "errors": len(result.errors), "failures": len(result.failures),
        "failed_test_ids": [test.id() for test, _ in result.errors + result.failures],
        "source_pins_before": before, "source_pins_after": after,
        "sources_unchanged_during_run": before == after,
        "ownership_samples": events, "trace_diagnostic_errors": trace_errors,
        "trace_event_limit": 256,
        "trace_overhead_limit": "Function frame tracing perturbs timing; a passing run does not establish the original failure cause",
        "original_58_test_failure_preserved": True,
        "production_source_changed": False, "ownership_retries_added": False,
        "extra_os_table_samples": 0, "entire_network_table_or_exception_text_recorded": False,
        "model_game_or_production_service_launched": False,
        "scope": "One existing synthetic test suite, including its owned child jobs/loopback ASGI fixtures only",
    }
    with (destination / "result.json").open("x", encoding="utf-8") as stream:
        json.dump(receipt, stream, indent=2)
    print(json.dumps({key: receipt[key] for key in (
        "status", "tests_run", "errors", "failures", "failed_test_ids",
        "sources_unchanged_during_run", "trace_diagnostic_errors")}))
    print("Evidence: " + str(destination / "result.json"))
    return 0 if result.wasSuccessful() and before == after and not trace_errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
