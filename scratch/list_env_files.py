import os, re
root = r"C:\AI-BS"
skip = {"node_modules", ".git", "__pycache__", "site-packages", ".venv", "venv", "Lib", "_internal", ".tmp"}
hits = []
for d, dirs, files in os.walk(root):
    dirs[:] = [x for x in dirs if x not in skip and not x.startswith("frozen")]
    for f in files:
        fl = f.lower()
        if fl == ".env" or fl.startswith(".env.") or fl.endswith(".env"):
            hits.append(os.path.join(d, f))
crypto_re = re.compile(r"CRYPTO|CRO|EXCHANGE|API_KEY|SECRET|TRADE", re.I)
for p in sorted(hits):
    try:
        keys = []
        for line in open(p, encoding="utf-8", errors="ignore"):
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                keys.append((k.strip(), bool(v.strip())))
        flag = " [CRYPTO-RELATED]" if any(crypto_re.search(k) for k, _ in keys) else ""
        print(f"\n{p}  ({len(keys)} vars){flag}")
        for k, has in keys:
            print(f"   {k} = {'<set>' if has else '<empty>'}")
    except Exception as e:
        print(f"\n{p}  (unreadable: {e})")
print(f"\nTOTAL: {len(hits)}")
