import socket

s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
try:
    s.bind(("0.0.0.0", 47989))
    print("[+] SO_REUSEADDR bind to 47989: SUCCESS")
    s.close()
except Exception as e:
    print(f"[-] SO_REUSEADDR bind to 47989: FAILED -> {e}")

s2 = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s2.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
try:
    s2.bind(("0.0.0.0", 48010))
    print("[+] SO_REUSEADDR bind to 48010: SUCCESS")
    s2.close()
except Exception as e:
    print(f"[-] SO_REUSEADDR bind to 48010: FAILED -> {e}")
