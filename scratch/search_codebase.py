import os
from pathlib import Path

def search_files(root_dir, pattern):
    results = []
    root = Path(root_dir)
    exclude_dirs = {"node_modules", "dist", "build", ".git", ".firebase", "release-build", "desktop-build", "build-output"}
    for p in root.rglob("*"):
        if any(ex in p.parts for ex in exclude_dirs):
            continue
        if p.is_file() and p.suffix in {".js", ".jsx", ".ts", ".tsx", ".html", ".json", ".py"}:
            try:
                content = p.read_text(encoding="utf-8", errors="ignore")
                if pattern in content:
                    results.append(str(p))
            except Exception:
                pass
    return results

if __name__ == "__main__":
    matches = search_files(r"C:\AI-BS\frontend", "brettstehouwer")
    print(f"Found {len(matches)} matches:")
    for m in matches:
        print(m)
