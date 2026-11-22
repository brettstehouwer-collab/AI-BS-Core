import os

blob_path = r"C:\Users\footb\AppData\Local\Packages\38985CA0.MW4Beta_5bkah9njm3e9g\SystemAppData\wgs\00090000057C2E28_0000000000000000000000006422D247\6CA9AA7D330147EA81194F5AA5897C89\E56BDCC41F3C4408A23E7C6903662C5C"

with open(blob_path, "rb") as f:
    data = f.read()

print(f"File size: {len(data)} bytes")
print("First 64 bytes hex:")
print(data[:64].hex())
print("First 64 bytes ascii:")
print("".join(chr(b) if 32 <= b <= 126 else "." for b in data[:64]))

# Check if SQLite
if data.startswith(b"SQLite format 3"):
    print("Format: SQLite Database!")
# Check if GZIP / ZLIB
elif data.startswith(b"\x1f\x8b") or data.startswith(b"\x78\x9c") or data.startswith(b"\x78\x01") or data.startswith(b"\x78\xda"):
    print("Format: Compressed (zlib/gzip)!")
else:
    print("Format: Custom Binary Structure")
