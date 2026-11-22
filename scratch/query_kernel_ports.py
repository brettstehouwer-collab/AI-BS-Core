import ctypes
from ctypes import wintypes

# Define Windows API structs and types for GetExtendedTcpTable
class MIB_TCPROW_OWNER_PID(ctypes.Structure):
    _fields_ = [
        ("dwState", wintypes.DWORD),
        ("dwLocalAddr", wintypes.DWORD),
        ("dwLocalPort", wintypes.DWORD),
        ("dwRemoteAddr", wintypes.DWORD),
        ("dwRemotePort", wintypes.DWORD),
        ("dwOwningPid", wintypes.DWORD),
    ]

def decode_port(port_bytes):
    return ((port_bytes & 0xFF) << 8) | ((port_bytes >> 8) & 0xFF)

def decode_ip(ip_int):
    return f"{ip_int & 0xFF}.{(ip_int >> 8) & 0xFF}.{(ip_int >> 16) & 0xFF}.{(ip_int >> 24) & 0xFF}"

iphlpapi = ctypes.WinDLL("iphlpapi.dll")
TCP_TABLE_OWNER_PID_ALL = 5
AF_INET = 2

size = wintypes.DWORD(0)
res = iphlpapi.GetExtendedTcpTable(None, ctypes.byref(size), True, AF_INET, TCP_TABLE_OWNER_PID_ALL, 0)
buf = ctypes.create_string_buffer(size.value)
res = iphlpapi.GetExtendedTcpTable(buf, ctypes.byref(size), True, AF_INET, TCP_TABLE_OWNER_PID_ALL, 0)

num_entries = ctypes.cast(buf, ctypes.POINTER(wintypes.DWORD)).contents.value
print(f"Total TCP table entries: {num_entries}")

p_table = ctypes.cast(ctypes.byref(buf, 4), ctypes.POINTER(MIB_TCPROW_OWNER_PID))
for i in range(num_entries):
    row = p_table[i]
    port = decode_port(row.dwLocalPort)
    if port in [47984, 47989, 47990, 48010]:
        ip = decode_ip(row.dwLocalAddr)
        print(f"MATCH: {ip}:{port} owned by PID {row.dwOwningPid}")

