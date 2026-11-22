import os
import sys
import json
import ast
import sqlite3

sys.path.insert(0, r"C:\AI-BS\backend")

print("=== AUDITING TOOL REGISTRY ===")
from tools.tool_registry import ToolRegistry

decls = ToolRegistry.get_tool_declarations()
decl_names = [d["name"] for d in decls]
print(f"Total declared tools: {len(decl_names)}")

# Parse tool_registry.py AST to find execute_tool
with open(r"C:\AI-BS\backend\tools\tool_registry.py", "r", encoding="utf-8") as f:
    tree = ast.parse(f.read(), filename="tool_registry.py")

handled_tools = []
for node in ast.walk(tree):
    if isinstance(node, ast.FunctionDef) and node.name == "execute_tool":
        # Traverse statements inside execute_tool
        for sub in ast.walk(node):
            if isinstance(sub, ast.Compare):
                # check if tool_name == "something"
                if isinstance(sub.left, ast.Name) and sub.left.id == "tool_name":
                    for comp in sub.comparators:
                        if isinstance(comp, ast.Constant) and isinstance(comp.value, str):
                            handled_tools.append(comp.value)
                elif len(sub.comparators) == 1 and isinstance(sub.comparators[0], ast.Name) and sub.comparators[0].id == "tool_name":
                    if isinstance(sub.left, ast.Constant) and isinstance(sub.left.value, str):
                        handled_tools.append(sub.left.value)

print(f"Total handled tool branches: {len(handled_tools)}")

declared_set = set(decl_names)
handled_set = set(handled_tools)

missing_in_execute = declared_set - handled_set
missing_in_decls = handled_set - declared_set

print(f"Declared tools count: {len(declared_set)}")
print(f"Handled tools count: {len(handled_set)}")
print(f"Tools declared but missing execution branch: {missing_in_execute}")
print(f"Tools handled in execute_tool but missing in declarations: {missing_in_decls}")

print("\n=== AUDITING ALL TOOL DECLARATIONS DETAILS ===")
for d in decls:
    name = d["name"]
    desc = d.get("description", "")[:60]
    is_handled = name in handled_set
    print(f"- {name}: handled={is_handled} | {desc}...")

print("\n=== AUDITING MONETARY TOOLS & ACTIONS ===")
monetary_keywords = ["crypto", "accounting", "money", "wallet", "stripe", "invoice", "payment", "tax", "ledger", "balance", "transfer", "financial"]

monetary_tools = [name for name in handled_set | declared_set if any(k in name.lower() for k in monetary_keywords)]
print(f"Monetary tools in ToolRegistry: {monetary_tools}")

print("\n=== AUDITING ROUTERS FOR MONETARY ENDPOINTS ===")
routers_dir = r"C:\AI-BS\backend\routers"
monetary_routers = []
for f_name in os.listdir(routers_dir):
    if f_name.endswith(".py"):
        f_path = os.path.join(routers_dir, f_name)
        with open(f_path, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read()
            if any(k in f_name.lower() or k in content.lower() for k in monetary_keywords):
                monetary_routers.append(f_name)

print(f"Routers touching monetary/financial/crypto domains: {monetary_routers}")
