import socket

blocked = []
allowed = []
for p in range(47970, 48030):
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        s.bind(("0.0.0.0", p))
        allowed.append(p)
    except Exception as e:
        blocked.append((p, str(e)))
    finally:
        s.close()

print(f"Total tested: 60 | Allowed: {len(allowed)} | Blocked: {len(blocked)}")
if blocked:
    print(f"Blocked range: {blocked[0][0]} to {blocked[-1][0]}")
    print(f"Sample error on {blocked[0][0]}: {blocked[0][1]}")
