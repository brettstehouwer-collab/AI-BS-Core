"""Unit & Integration Tests for AI-BS Self-Healing Sentinel."""

import os
import sys
import tempfile
import pytest
from pathlib import Path
from unittest.mock import AsyncMock, patch

from backend.core.self_healing_sentinel import SelfHealingSentinel, IncidentReport


@pytest.fixture
def temp_sentinel(tmp_path):
    db_file = tmp_path / "test_incidents.db"
    backup_folder = tmp_path / "backups"
    sentinel = SelfHealingSentinel(db_path=db_file, backup_dir=backup_folder)
    return sentinel


def test_parse_traceback(temp_sentinel):
    sample_traceback = """Traceback (most recent call last):
  File "C:\\AI-BS\\backend\\routers\\sample_router.py", line 42, in get_status
    result = compute_metrics(target_id)
ZeroDivisionError: division by zero
"""
    diag = temp_sentinel.parse_traceback(sample_traceback)
    assert diag is not None
    assert "sample_router.py" in diag["file_path"]
    assert diag["line_number"] == 42
    assert diag["error_type"] == "ZeroDivisionError"
    assert "division by zero" in diag["error_message"]
    assert len(diag["error_signature"]) == 12


def test_parse_pytest_failure(temp_sentinel):
    sample_pytest = "FAILED tests/test_sample.py::test_calculation - AssertionError: Expected 10 but got 0"
    diag = temp_sentinel.parse_test_failure(sample_pytest)
    assert diag is not None
    assert "test_sample.py" in diag["file_path"]
    assert diag["error_type"] == "AssertionError"
    assert "Expected 10 but got 0" in diag["error_message"]


def test_backup_and_restore(temp_sentinel, tmp_path):
    dummy_file = tmp_path / "test_script.py"
    dummy_file.write_text("a = 1\nb = 2\n", encoding="utf-8")

    # Create backup
    backup = temp_sentinel.create_backup(dummy_file)
    assert backup.exists()

    # Corrupt target
    dummy_file.write_text("CORRUPTED CONTENT", encoding="utf-8")
    assert dummy_file.read_text(encoding="utf-8") == "CORRUPTED CONTENT"

    # Restore
    restored = temp_sentinel.restore_backup(backup, dummy_file)
    assert restored is True
    assert dummy_file.read_text(encoding="utf-8") == "a = 1\nb = 2\n"


def test_validate_syntax(temp_sentinel, tmp_path):
    valid_file = tmp_path / "valid.py"
    valid_file.write_text("def hello():\n    return 'world'\n", encoding="utf-8")
    ok, msg = temp_sentinel.validate_syntax(valid_file)
    assert ok is True

    invalid_file = tmp_path / "invalid.py"
    invalid_file.write_text("def broken(:\n    syntax error\n", encoding="utf-8")
    ok, msg = temp_sentinel.validate_syntax(invalid_file)
    assert ok is False
    assert "SyntaxError" in msg


def test_circuit_breaker(temp_sentinel):
    sig = "sig_test_123"
    assert temp_sentinel.is_circuit_broken(sig) is False

    # Attempt 1
    temp_sentinel.record_attempt(sig)
    assert temp_sentinel.is_circuit_broken(sig) is False

    # Attempt 2 (reaches max_retries = 2)
    temp_sentinel.record_attempt(sig)
    assert temp_sentinel.is_circuit_broken(sig) is True


def test_full_healing_loop_simulation(temp_sentinel, tmp_path):
    import asyncio
    buggy_file = tmp_path / "buggy_calc.py"
    buggy_file.write_text(
        "def divide(a, b):\n    return a / b\n",
        encoding="utf-8",
    )

    error_trace = f"""Traceback (most recent call last):
  File "{buggy_file}", line 2, in divide
    return a / b
ZeroDivisionError: division by zero
"""

    mock_patch = {
        "analysis": "Add zero-divisor guard",
        "target_content": "    return a / b",
        "replacement_content": "    return a / b if b != 0 else 0.0",
    }

    with patch.object(temp_sentinel, "generate_surgical_patch", new=AsyncMock(return_value=mock_patch)):
        with patch.object(temp_sentinel, "run_verification_tests", return_value=(True, "1 passed")):
            report = asyncio.run(temp_sentinel.heal_incident(error_trace))
            assert report["status"] == "VERIFIED"
            assert "b != 0" in buggy_file.read_text(encoding="utf-8")

            # Check DB recorded
            incidents = temp_sentinel.get_recent_incidents(1)
            assert len(incidents) == 1
            assert incidents[0]["status"] == "VERIFIED"
