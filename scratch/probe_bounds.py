import socket

def probe(p):
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        s.bind(("0.0.0.0", p))
        s.close()
        return True
    except:
        s.close()
        return False

print("45000:", probe(45000))
print("46000:", probe(46000))
print("47000:", probe(47000))
print("47500:", probe(47500))
print("47900:", probe(47900))
print("48050:", probe(48050))
print("48500:", probe(48500))
print("49000:", probe(49000))
