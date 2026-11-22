import os
import sys
import json
import sqlite3
import re

sys.stdout.reconfigure(encoding='utf-8')
print("=== STARTING FULL ECOSYSTEM TOOL & MONETARY AUDIT ===")

base_dir = r"C:\AI-BS"
backend_dir = os.path.join(base_dir, "backend")

# 1. Audit Tool Registry (backend/tools/tool_registry.py)
print("\n--- 1. AUDITING backend/tools/tool_registry.py ---")
tool_reg_path = os.path.join(backend_dir, "tools", "tool_registry.py")
if os.path.exists(tool_reg_path):
    with open(tool_reg_path, "r", encoding="utf-8") as f:
        code = f.read()

    # Find declared tools
    declared_tools = re.findall(r'"name":\s*"([^"]+)"', code)
    print(f"Declared tools in schema ({len(declared_tools)}): {declared_tools}")

    # Find execution handlers
    handled_tools = re.findall(r'elif tool_name == "([^"]+)":|if tool_name == "([^"]+)":', code)
    handled = [t[0] or t[1] for t in handled_tools]
    print(f"Handled tools in execute_tool ({len(handled)}): {handled}")

    missing_handlers = set(declared_tools) - set(handled)
    print(f"Declared but unhandled: {missing_handlers}")
    orphan_handlers = set(handled) - set(declared_tools)
    print(f"Handled but undeclared: {orphan_handlers}")

    # Check for placeholder / stub / mock logic in tool_registry
    stubs = []
    lines = code.split("\n")
    for i, line in enumerate(lines):
        if any(keyword in line.lower() for keyword in ["mock", "dummy", "placeholder", "fake", "todo", "simulate", "hardcoded"]):
            stubs.append((i + 1, line.strip()))
    print(f"\nPotential stubs/placeholders in tool_registry ({len(stubs)} lines):")
    for line_num, line_str in stubs[:15]:
        print(f"  Line {line_num}: {line_str}")

# 2. Audit Other Tool & Action Files in backend
print("\n--- 2. AUDITING OTHER TOOL / ACTION MODULES IN BACKEND ---")
tools_dir = os.path.join(backend_dir, "tools")
for root, dirs, files in os.walk(tools_dir):
    for file in files:
        if file.endswith(".py"):
            filepath = os.path.join(root, file)
            rel = os.path.relpath(filepath, base_dir)
            with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
                c = f.read()
            funcs = re.findall(r'def\s+([a-zA-Z0-9_]+)\s*\(', c)
            print(f"  {rel}: {len(funcs)} functions: {funcs[:6]}")

# 3. Audit Monetary & Financial Routers / Services
print("\n--- 3. AUDITING MONETARY & FINANCIAL ROUTERS & SERVICES ---")
monetary_files = [
    os.path.join(backend_dir, "routers", "trading_router.py"),
    os.path.join(backend_dir, "routers", "accounting_router.py"),
    os.path.join(backend_dir, "commercial_gateway", "billing_provisioner.py"),
    os.path.join(backend_dir, "payout_watcher.py"),
    os.path.join(backend_dir, "pearl_payout_watcher.py"),
    os.path.join(backend_dir, "crypto_trader.py"),
    os.path.join(backend_dir, "aibs_gpu_worker_daemon.py"),
    os.path.join(backend_dir, "clore_service.py"),
    os.path.join(backend_dir, "vastai_service.py"),
]

for mf in monetary_files:
    if os.path.exists(mf):
        rel = os.path.relpath(mf, base_dir)
        with open(mf, "r", encoding="utf-8", errors="ignore") as f:
            c = f.read()
        
        # Check for mock / fake / simulate / hardcoded monetary patterns
        mock_matches = []
        for i, line in enumerate(c.split("\n")):
            lower = line.lower()
            if any(k in lower for k in ["mock", "simulate", "dummy", "fake", "placeholder", "1425", "850.50", "899.99"]):
                # exclude safe words like 'simulation' if clearly labeled or non-monetary
                mock_matches.append((i + 1, line.strip()))
        print(f"  File {rel}: {len(mock_matches)} mock/simulation indicators")
        for ln, ls in mock_matches[:10]:
            print(f"    Line {ln}: {ls}")

# 4. Audit SQLite Databases for Financial Tables & Mock Rows
print("\n--- 4. AUDITING SQLITE DATABASES FOR FINANCIAL INTEGRITY ---")
db_paths = [
    os.path.join(backend_dir, "aibs_master.db"),
    os.path.join(backend_dir, "stehouwer_accounting.db"),
    os.path.join(backend_dir, "commercial_gateway", "commercial_usage.db"),
    os.path.join(backend_dir, "drip_ledger.db"),
    os.path.join(backend_dir, "crypto_accounting.db")
]

for db_path in db_paths:
    if os.path.exists(db_path):
        rel = os.path.relpath(db_path, base_dir)
        conn = sqlite3.connect(db_path)
        cur = conn.cursor()
        tables = cur.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
        table_names = [t[0] for t in tables]
        print(f"Database: {rel} ({len(table_names)} tables)")
        for tname in table_names:
            if any(kw in tname.lower() for kw in ["accounting", "crypto", "trade", "billing", "payout", "transfer", "wallet", "tax", "monet"]):
                count = cur.execute(f"SELECT COUNT(*) FROM {tname}").fetchone()[0]
                rows = cur.execute(f"SELECT * FROM {tname} LIMIT 5").fetchall()
                print(f"  Table '{tname}': {count} rows. Samples: {rows}")
        conn.close()

print("\n=== FULL ECOSYSTEM AUDIT SCAN COMPLETE ===")
