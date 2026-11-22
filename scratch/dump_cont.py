import os

cont_path = r"C:\Users\footb\AppData\Local\Packages\38985CA0.MW4Beta_5bkah9njm3e9g\SystemAppData\wgs\00090000057C2E28_0000000000000000000000006422D247\33D3A32EAAF14607AF18DFFBE2CE5398\container.2"

with open(cont_path, "rb") as f:
    data = f.read()

print(f"container.2 size: {len(data)} bytes")
for i in range(0, min(168, len(data)), 16):
    chunk = data[i:i+16]
    h = " ".join(f"{b:02x}" for b in chunk)
    a = "".join(chr(b) if 32 <= b <= 126 else "." for b in chunk)
    print(f"{i:04x}  {h:<48}  {a}")
