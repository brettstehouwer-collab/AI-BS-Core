import socket

def test(p):
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        s.bind(("0.0.0.0", p))
        s.close()
        return True
    except:
        s.close()
        return False

# Find lower bound
low = 44000
high = 45000
while low < high:
    mid = (low + high) // 2
    if test(mid):
        low = mid + 1
    else:
        high = mid
start_blocked = low

# Find upper bound
low = 48000
high = 49000
while low < high:
    mid = (low + high) // 2
    if not test(mid):
        low = mid + 1
    else:
        high = mid
end_blocked = low - 1

print(f"EXACT BLOCKED PORT RANGE: {start_blocked} to {end_blocked}")
