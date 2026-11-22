import struct

idx_path = r"C:\Users\footb\AppData\Local\Packages\38985CA0.MW4Beta_5bkah9njm3e9g\SystemAppData\wgs\00090000057C2E28_0000000000000000000000006422D247\containers.index"

with open(idx_path, "rb") as f:
    data = f.read()

print("Hex dump of first 128 bytes:")
for i in range(0, min(128, len(data)), 16):
    chunk = data[i:i+16]
    h = " ".join(f"{b:02x}" for b in chunk)
    a = "".join(chr(b) if 32 <= b <= 126 else "." for b in chunk)
    print(f"{i:04x}  {h:<48}  {a}")
