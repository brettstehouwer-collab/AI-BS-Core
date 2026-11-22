import socket

for p in [40000, 42000, 44000, 45000, 48000, 48999, 49000]:
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        s.bind(("0.0.0.0", p))
        print(f"{p}: OK")
    except Exception as e:
        print(f"{p}: FAILED -> {e}")
    finally:
        s.close()
