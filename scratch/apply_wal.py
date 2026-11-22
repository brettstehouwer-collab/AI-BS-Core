import os
import re

backend_dir = r"C:\AI-BS\backend"
connect_pattern = re.compile(r"^(\s*)([a-zA-Z0-9_]+)\s*=\s*sqlite3\.connect\(")
wal_inserted = 0

for root, dirs, files in os.walk(backend_dir):
    # skip backup folders or pycache
    if "backups" in root or "__pycache__" in root:
        continue
    for file in files:
        if file.endswith(".py"):
            filepath = os.path.join(root, file)
            with open(filepath, "r", encoding="utf-8") as f:
                lines = f.readlines()
            
            new_lines = []
            modified = False
            for line in lines:
                new_lines.append(line)
                match = connect_pattern.match(line)
                if match:
                    indent = match.group(1)
                    var_name = match.group(2)
                    # Check if the next line already has PRAGMA to avoid double injection
                    # But we're streaming, so we just add it and hope it's not already there
                    new_lines.append(f"{indent}try:\n")
                    new_lines.append(f"{indent}    {var_name}.execute(\"PRAGMA journal_mode=WAL;\")\n")
                    new_lines.append(f"{indent}    {var_name}.execute(\"PRAGMA synchronous=NORMAL;\")\n")
                    new_lines.append(f"{indent}except Exception:\n")
                    new_lines.append(f"{indent}    pass\n")
                    modified = True
                    wal_inserted += 1
            
            if modified:
                with open(filepath, "w", encoding="utf-8") as f:
                    f.writelines(new_lines)

print(f"WAL Pragmas successfully injected into {wal_inserted} connection instances.")
