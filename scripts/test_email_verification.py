import socket
import re

print("Testing DNS resolution and email verification capabilities...")

# Test domains from the dataset
test_emails = [
    "shalonsmith86@gmail.com",
    "joshuacoryjenkins@gmail.com",
    "pureperfectiondayspa@gmail.com",
    "asaph.akouete@sjhsknights.com",
    "adrakeford@parentchildplus.org",
    "nonexistentuser1238491823@gmail.com",
    "fakeuser@definitelyinvaliddomain12398471.com"
]

for email in test_emails:
    domain = email.split('@')[1]
    try:
        # Check domain existence via socket gethostbyname
        ip = socket.gethostbyname(domain)
        print(f"[OK] {domain} -> {ip}")
    except socket.gaierror as e:
        print(f"[FAIL] {domain} does NOT exist (DNS Error: {e})")

# Test outbound port 25 connectivity to Gmail MX
print("\nTesting Port 25 connectivity to gmail-smtp-in.l.google.com...")
try:
    s = socket.create_connection(("gmail-smtp-in.l.google.com", 25), timeout=5)
    banner = s.recv(1024)
    print(f"[PORT 25 OPEN] Received banner: {banner.decode('utf-8', errors='ignore').strip()}")
    s.close()
except Exception as e:
    print(f"[PORT 25 BLOCKED/FILTERED] {e}")
