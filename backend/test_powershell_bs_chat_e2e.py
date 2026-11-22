import sys
import os

_backend = r"C:\AI-BS\backend"
_root = r"C:\AI-BS"
if _backend not in sys.path:
    sys.path.insert(0, _backend)
if _root not in sys.path:
    sys.path.insert(0, _root)

from tools.tool_registry import ToolRegistry
from core.hybrid_reasoning_engine import detect_tool_intent
from core.program_builder_engine import AutonomousProgramBuilder

print("=== 1. Testing ToolRegistry execute_powershell ===")
ps_res = ToolRegistry.execute_tool("execute_powershell", {"command": "Write-Output 'TEST_POWERSHELL_OK'"})
print("PowerShell status:", ps_res.get("status"))
print("PowerShell stdout:", ps_res.get("stdout", "").strip())
assert ps_res.get("status") == "success"
assert "TEST_POWERSHELL_OK" in ps_res.get("stdout", "")

print("\n=== 2. Testing AutonomousProgramBuilder with PowerShell ===")
build_res = ToolRegistry.execute_tool("build_program", {
    "project_name": "ps_test_microservice",
    "language": "powershell",
    "description": "PowerShell Test Microservice built via AI-BS BS-Chat",
    "files": [
        {
            "path": "run.ps1",
            "content": "Write-Output 'AI-BS POWERSHELL RUNNER ACTIVE'\n$date = Get-Date -Format 'yyyy-MM-dd HH:mm:ss'\nWrite-Output \"Timestamp: $date\"\n"
        },
        {
            "path": "README.md",
            "content": "# PowerShell Test Microservice\nBuilt by AI-BS Program Builder in BS-Chat."
        }
    ],
    "entrypoint": "run.ps1",
    "run_immediately": True
})
print("Build project_name:", build_res.get("project_name"))
print("Execution status:", build_res.get("execution", {}).get("status"))
print("Execution stdout:\n", build_res.get("execution", {}).get("stdout", "").strip())
assert build_res.get("execution", {}).get("status") == "success"
assert "AI-BS POWERSHELL RUNNER ACTIVE" in build_res.get("execution", {}).get("stdout", "")

print("\n=== 3. Testing ToolRegistry run_program with custom powershell_command ===")
run_res = ToolRegistry.execute_tool("run_program", {
    "project_name": "ps_test_microservice",
    "powershell_command": "Get-Content README.md | Select-Object -First 1"
})
print("run_program status:", run_res.get("status"))
print("run_program stdout:", run_res.get("stdout", "").strip())
assert run_res.get("status") == "success"
assert "PowerShell Test Microservice" in run_res.get("stdout", "")

print("\n=== 4. Testing ToolRegistry list_programs ===")
list_res = ToolRegistry.execute_tool("list_programs", {})
print(f"list_programs returned {len(list_res)} programs")
assert any(p.get("project_name") == "ps_test_microservice" for p in list_res)

print("\n=== 5. Testing Intent Detection in Hybrid Reasoning Engine ===")
t1, a1 = detect_tool_intent("/ps Get-Location")
print("/ps intent:", t1, a1)
assert t1 == "execute_powershell"
assert a1["command"] == "Get-Location"

t2, a2 = detect_tool_intent("Get-Process -Name svchost")
print("cmdlet intent:", t2, a2)
assert t2 == "execute_powershell"

t3, a3 = detect_tool_intent("python main.py --verbose")
print("CLI intent:", t3, a3)
assert t3 == "execute_powershell"
assert a3["command"] == "python main.py --verbose"

t4, a4 = detect_tool_intent("npm run build")
print("npm intent:", t4, a4)
assert t4 == "execute_powershell"

print("\n=== 6. Testing BsChatIdeFullView in PyQt6 ===")
from PyQt6.QtWidgets import QApplication
from native_studio.engine import EngineBus
from native_studio.bs_chat_ide_full import BsChatIdeFullView

app = QApplication.instance() or QApplication([])
bus = EngineBus()
view = BsChatIdeFullView(bus)

# Test code block extraction
sample_transcript = """
Here is the PowerShell script to build the program:

```powershell
Write-Output "Building AI-BS Program"
Get-Date
```

Now run the script.
"""
lang, code = view._extract_last_code_block(sample_transcript)
print(f"Extracted code block (language: {lang}):\n{code}")
assert lang == "powershell"
assert 'Write-Output "Building AI-BS Program"' in code

print("\nALL_POWERSHELL_BS_CHAT_INTEGRATION_TESTS_PASSED!")
