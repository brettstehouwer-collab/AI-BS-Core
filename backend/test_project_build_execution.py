# test_project_build_execution.py - Unit and Integration Tests for AI-BS Project Build System
import os
import sys
import json
import shutil
import tempfile
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from backend.core.program_builder_engine import AutonomousProgramBuilder, PROGRAMS_DIR
from backend.tools.tool_registry import ToolRegistry
from backend.core.hybrid_reasoning_engine import detect_tool_intent


def test_detect_build_command():
    temp_dir = tempfile.mkdtemp(prefix="aibs_test_build_")
    try:
        # 1. No manifest -> None
        assert AutonomousProgramBuilder.detect_build_command(temp_dir) is None

        # 2. package.json
        pkg_json = os.path.join(temp_dir, "package.json")
        with open(pkg_json, "w") as f:
            f.write('{"scripts": {"build": "vite build"}}')
        cmd = AutonomousProgramBuilder.detect_build_command(temp_dir)
        assert "npm" in cmd and "build" in cmd

        # 3. build.ps1 takes priority
        ps1_script = os.path.join(temp_dir, "build.ps1")
        with open(ps1_script, "w") as f:
            f.write('Write-Output "Building..."')
        cmd2 = AutonomousProgramBuilder.detect_build_command(temp_dir)
        assert "powershell" in cmd2.lower() and "build.ps1" in cmd2

    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


def test_detect_build_command_cargo_and_requirements():
    temp_dir = tempfile.mkdtemp(prefix="aibs_test_cargo_")
    try:
        cargo_toml = os.path.join(temp_dir, "Cargo.toml")
        with open(cargo_toml, "w") as f:
            f.write('[package]\nname = "test_cargo"\nversion = "0.1.0"\n')
        assert AutonomousProgramBuilder.detect_build_command(temp_dir) == "cargo build"

        os.remove(cargo_toml)
        req_txt = os.path.join(temp_dir, "requirements.txt")
        with open(req_txt, "w") as f:
            f.write("pytest>=8.0.0\n")
        req_cmd = AutonomousProgramBuilder.detect_build_command(temp_dir)
        assert "pip install -r requirements.txt" in req_cmd
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


def test_build_program_with_build_step():
    proj_name = "test_build_runner_app"
    files = [
        {
            "path": "main.py",
            "content": "print('HELLO FROM BUILT APP')\n"
        },
        {
            "path": "build.bat",
            "content": "@echo OFF\necho ARTIFACT COMPILED\nexit /b 0\n"
        }
    ]

    manifest = AutonomousProgramBuilder.build_program(
        project_name=proj_name,
        language="python",
        description="Test Application with Custom Build Step",
        files=files,
        entrypoint="main.py",
        run_immediately=True,
        execute_build=True
    )

    assert manifest["project_name"] == proj_name
    assert "build" in manifest
    assert manifest["build"]["executed"] is True
    assert manifest["build"]["exit_code"] == 0
    assert manifest["execution"]["executed"] is True
    assert "HELLO FROM BUILT APP" in manifest["execution"]["stdout"]


def test_build_program_blocks_on_build_failure():
    proj_name = "test_failing_build_app"
    files = [
        {
            "path": "main.py",
            "content": "print('SHOULD NEVER RUN IF BUILD FAILS')\n"
        },
        {
            "path": "build.bat",
            "content": "@echo OFF\necho FATAL COMPILATION ERROR 1>&2\nexit /b 42\n"
        }
    ]

    manifest = AutonomousProgramBuilder.build_program(
        project_name=proj_name,
        language="python",
        description="Failing Build Test Application",
        files=files,
        entrypoint="main.py",
        run_immediately=True,
        execute_build=True
    )

    assert manifest["build"]["executed"] is True
    assert manifest["build"]["exit_code"] != 0
    # Execution must be blocked
    assert manifest["execution"]["executed"] is False
    assert manifest["execution"]["status"] == "blocked_by_build_failure"
    assert "Execution halted" in manifest["execution"]["stderr"]


def test_build_project_standalone():
    temp_dir = tempfile.mkdtemp(prefix="aibs_test_standalone_proj_")
    try:
        # Create a project with build.bat
        b_bat = os.path.join(temp_dir, "build.bat")
        with open(b_bat, "w") as f:
            f.write("@echo OFF\necho STANDALONE BUILD OK\nexit /b 0\n")

        res = AutonomousProgramBuilder.build_project(
            project_name_or_dir=temp_dir
        )
        assert res["status"] == "success"
        assert res["exit_code"] == 0
        assert "STANDALONE BUILD OK" in res["stdout"]
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


def test_tool_registry_build_project():
    temp_dir = tempfile.mkdtemp(prefix="aibs_tool_build_")
    try:
        b_bat = os.path.join(temp_dir, "build.bat")
        with open(b_bat, "w") as f:
            f.write("@echo OFF\necho TOOL REGISTRY BUILD SUCCESS\nexit /b 0\n")

        res = ToolRegistry.execute_tool("build_project", {
            "project_name_or_dir": temp_dir
        })
        assert res["status"] == "success"
        assert res["exit_code"] == 0
        assert "TOOL REGISTRY BUILD SUCCESS" in res["stdout"]
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


def test_hybrid_reasoning_intent_detection():
    # Slash commands
    t1, a1 = detect_tool_intent("/build frontend npm run build")
    assert t1 == "build_project"
    assert a1["project_name_or_dir"] == "frontend"
    assert a1["build_command"] == "npm run build"

    t2, a2 = detect_tool_intent("/program build my_app")
    assert t2 == "build_project"
    assert a2["project_name_or_dir"] == "my_app"
    assert a2["build_command"] is None

    t3, a3 = detect_tool_intent("/program list")
    assert t3 == "list_programs"

    # Natural language
    t4, a4 = detect_tool_intent("Please build project test_app with command cargo build")
    assert t4 == "build_project"
    assert a4["project_name_or_dir"] == "test_app"
    assert a4["build_command"] == "cargo build"
