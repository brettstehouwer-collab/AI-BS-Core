import importlib.util, time, datetime as dt
spec = importlib.util.spec_from_file_location("t", r"C:\AI-BS\scratch\live_cro_usdt_trader.py")
m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
c = m.CryptoComClient(*m.load_dpapi_credentials())
end = int(time.time() * 1000); start = end - 4 * 86400 * 1000
f = lambda ms: dt.datetime.fromtimestamp(int(ms) / 1000).strftime("%m-%d %H:%M:%S")
for meth in ["private/get-order-history", "private/get-trades"]:
    try:
        rows = c.private_post(meth, {"start_time": start, "end_time": end, "limit": 100})["result"]["data"]
    except Exception as e:
        print(meth, "ERROR", e); continue
    print(f"\n== {meth}: {len(rows)} rows (last 4 days, all instruments) ==")
    for r in sorted(rows, key=lambda r: int(r.get("create_time") or r.get("update_time") or 0)):
        t = r.get("create_time") or r.get("update_time")
        print(f, ) if False else None
        print(f"{f(t)} {r.get('instrument_name')} {r.get('side')} qty={r.get('quantity') or r.get('traded_quantity')} "
              f"px={r.get('limit_price') or r.get('traded_price')} status={r.get('status','FILL')} "
              f"type={r.get('order_type','')} oid={str(r.get('client_oid',''))[:28]}")
