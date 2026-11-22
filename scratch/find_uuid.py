import os

target = "fa40a308-4870-47ae-8b16-54c160158d20"
roots = [r"C:\Users\footb\.gemini", r"C:\Users\footb\AppData\Local\Antigravity", r"C:\Users\footb\AppData\Roaming\Antigravity"]

for r in roots:
    if not os.path.exists(r):
        continue
    for root, dirs, files in os.walk(r):
        for f in files:
            p = os.path.join(root, f)
            if target in f:
                print("MATCH IN FILENAME:", p)
            try:
                if os.path.getsize(p) < 20 * 1024 * 1024:
                    with open(p, 'rb') as fp:
                        c = fp.read()
                        if target.encode('utf-8') in c:
                            print("MATCH IN CONTENT:", p)
            except Exception:
                pass
