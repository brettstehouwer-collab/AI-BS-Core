import hashlib, importlib.util, os
spec = importlib.util.spec_from_file_location("t", r"C:\AI-BS\scratch\live_cro_usdt_trader.py")
m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
ak, asec = m.load_dpapi_credentials()
fp = lambda v: hashlib.sha256(v.encode()).hexdigest()[:8]
active = {fp(ak): "ACTIVE_KEY", fp(asec): "ACTIVE_SECRET"}
print("Active key fp:", fp(ak), " active secret fp:", fp(asec))
files = [l.split("  (")[0].strip() for l in open(r"C:\Users\Administrator\.gemini\antigravity\brain\bc9227e5-6170-4c83-b098-15ea7550ceae\env_inventory_masked.txt", encoding="utf-8", errors="ignore") if "[CRYPTO-RELATED]" in l]
for p in files:
    out = []
    for line in open(p, encoding="utf-8", errors="ignore"):
        if "=" not in line or line.strip().startswith("#"): continue
        k, v = line.split("=", 1); k = k.strip(); v = v.strip().strip('"').strip("'")
        if k.startswith(("CRYPTO_COM", "CRYPTOCOM", "KRAKEN")) and v:
            out.append(f"{k}={fp(v)}{' <'+active[fp(v)]+'>' if fp(v) in active else ''}")
    print(p, "|", ", ".join(out) or "-")
