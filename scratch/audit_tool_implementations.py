import os
import sys
import ast

with open(r"C:\AI-BS\backend\tools\tool_registry.py", "r", encoding="utf-8") as f:
    lines = f.readlines()

tools_info = {}
current_tool = None
tool_lines = []

for idx, line in enumerate(lines):
    line_s = line.strip()
    if line_s.startswith("if tool_name == ") or line_s.startswith("elif tool_name == "):
        if current_tool:
            tools_info[current_tool] = "".join(tool_lines)
        current_tool = line_s.split("==")[1].strip().strip(":").strip('"').strip("'")
        tool_lines = [line]
    elif current_tool:
        if line_s.startswith("else:") and "Unknown tool" in lines[min(idx+1, len(lines)-1)]:
            tools_info[current_tool] = "".join(tool_lines)
            current_tool = None
            tool_lines = []
        else:
            tool_lines.append(line)

if current_tool:
    tools_info[current_tool] = "".join(tool_lines)

print(f"Captured {len(tools_info)} tool implementations in execute_tool.\n")

for name, code in sorted(tools_info.items()):
    has_mock = any(k in code.lower() for k in ["mock", "dummy", "fake", "placeholder", "simulate"])
    calls_real = any(k in code for k in ["requests.", "urllib.", "subprocess.", "sqlite3.", "open(", "queue_comfyui", "discover_databases", "query_database"])
    num_lines = len(code.splitlines())
    print(f"Tool: {name:<30} | Lines: {num_lines:<4} | Real Call: {str(calls_real):<5} | Mock Indicator: {has_mock}")
    if has_mock:
        print(f"   --> Found mock keyword in {name}!")
        for l in code.splitlines():
            if any(k in l.lower() for k in ["mock", "dummy", "fake", "placeholder"]):
                print(f"       {l.strip()[:100]}")
