import os

project_root = r"C:\AI-BS"
target_dirs = ["", "backend", "scripts"]

legacy_patterns = [
    r"C:\Workspaces\Stehouwer_Server",
    r"G:\Stehouwer_Server",
    r"S:\AI-BS",
    r"F:\AI-BS",
    r"S:\Heuristics",
    r"F:\Local_Vault",
    r"C:\Users\footb\AI-BS_Matrix"
]

results = []

for td in target_dirs:
    dir_path = os.path.join(project_root, td)
    if not os.path.exists(dir_path):
        continue
    for f in os.listdir(dir_path):
        if f.endswith(".py"):
            fp = os.path.join(dir_path, f)
            with open(fp, "r", encoding="utf-8", errors="ignore") as file_obj:
                lines = file_obj.readlines()
            for idx, line in enumerate(lines, 1):
                for pat in legacy_patterns:
                    if pat.lower() in line.lower():
                        results.append({
                            "file": os.path.relpath(fp, project_root),
                            "line": idx,
                            "pat": pat,
                            "content": line.strip()
                        })

print(f"=== PROJECT PATH FIX CANDIDATES ({len(results)}) ===")
for r in results:
    print(f"File: {r['file']}:{r['line']} [{r['pat']}]\n  Line: {r['content']}")
