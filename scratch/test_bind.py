import socket

def test_bind(proto, port, host):
    sock_type = socket.SOCK_STREAM if proto == "TCP" else socket.SOCK_DGRAM
    s = socket.socket(socket.AF_INET, sock_type)
    try:
        s.bind((host, port))
        print(f"[+] {proto} {host}:{port} bind: SUCCESS")
    except Exception as e:
        print(f"[-] {proto} {host}:{port} bind: FAILED -> {e}")
    finally:
        s.close()

for host in ["127.0.0.1"]:
    for port in [55555, 47989]:
        test_bind("TCP", port, host)


