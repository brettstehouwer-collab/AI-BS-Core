import os

target = "AI-BS Ecosystem Status Check"
search_roots = [
    r"C:\Users\footb\.gemini",
    r"C:\Users\footb\AppData\Roaming\Antigravity",
    r"C:\Users\footb\AppData\Local\Antigravity"
]

for sroot in search_roots:
    if not os.path.exists(sroot):
        continue
    print("Searching in:", sroot)
    for root, dirs, files in os.walk(sroot):
        for f in files:
            p = os.path.join(root, f)
            try:
                # skip giant files over 50MB
                if os.path.getsize(p) > 50 * 1024 * 1024:
                    continue
                with open(p, "rb") as fp:
                    content = fp.read()
                    if target.encode("utf-8") in content or target.encode("utf-16le") in content:
                        print("FOUND IN:", p)
            except Exception:
                pass
