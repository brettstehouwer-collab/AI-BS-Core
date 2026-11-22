# test_bash_pip_bs_chat.py
import sys
import os
from pathlib import Path
import pytest

sys.path.insert(0, r"C:\AI-BS")
sys.path.insert(0, r"C:\AI-BS\backend")

from backend.executive_runtime_router import execute_multi_runtime
from backend.tools.tool_registry import ToolRegistry
from backend.core.hybrid_reasoning_engine import detect_tool_intent


def test_execute_multi_runtime_pip():
    res = execute_multi_runtime("pip", "--version")
    assert res.get("status") == "success"
    assert res.get("returncode") == 0
    assert "pip" in (res.get("stdout") or "").lower()


def test_execute_multi_runtime_bash():
    res = execute_multi_runtime("bash", "pip --version")
    assert res.get("status") == "success"
    assert res.get("returncode") == 0
    assert "pip" in (res.get("stdout") or "").lower()


def test_execute_multi_runtime_kwargs():
    res = execute_multi_runtime(command="pip --version", runtime="pip")
    assert res.get("status") == "success"
    assert res.get("returncode") == 0
    assert res.get("runtime_used") == "pip"


def test_tool_registry_execute_bash():
    res = ToolRegistry.execute_tool("execute_bash", {"command": "pip --version"})
    assert res.get("status") == "success"
    assert res.get("returncode") == 0


def test_tool_registry_execute_pip():
    res = ToolRegistry.execute_tool("execute_pip", {"command": "--version"})
    assert res.get("status") == "success"
    assert res.get("returncode") == 0


def test_detect_tool_intent_bash():
    tool_name, tool_args = detect_tool_intent("/bash pip install requests")
    assert tool_name == "execute_bash"
    assert tool_args.get("command") == "pip install requests"


def test_detect_tool_intent_pip():
    tool_name, tool_args = detect_tool_intent("/pip install requests")
    assert tool_name == "execute_pip"
    assert tool_args.get("command") == "install requests"


def test_detect_tool_intent_cli_tokens():
    b_name, b_args = detect_tool_intent("bash pip --version")
    assert b_name == "execute_bash"
    assert b_args.get("command") == "pip --version"

    p_name, p_args = detect_tool_intent("pip install httpx")
    assert p_name == "execute_pip"
    assert p_args.get("command") == "install httpx"
