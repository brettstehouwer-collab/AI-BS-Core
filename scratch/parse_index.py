import struct
import os

idx_path = r"C:\Users\footb\AppData\Local\Packages\38985CA0.MW4Beta_5bkah9njm3e9g\SystemAppData\wgs\00090000057C2E28_0000000000000000000000006422D247\containers.index"

with open(idx_path, "rb") as f:
    data = f.read()

version, count = struct.unpack("<II", data[:8])
print(f"Header: Version={version}, Container Count={count}, Total Size={len(data)}")

offset = 8
# Read package name
pkg_len = struct.unpack("<I", data[offset:offset+4])[0]
offset += 4
pkg_name = data[offset:offset+pkg_len*2].decode("utf-16le", errors="replace")
offset += pkg_len * 2
print(f"Package Name in Index: {pkg_name}")

# Read each container
for i in range(count):
    if offset >= len(data):
        break
    cname_len = struct.unpack("<I", data[offset:offset+4])[0]
    offset += 4
    cname = data[offset:offset+cname_len*2].decode("utf-16le", errors="replace")
    offset += cname_len * 2
    
    # Cloud ID / Container UUID string
    uuid_len = struct.unpack("<I", data[offset:offset+4])[0]
    offset += 4
    uuid_str = data[offset:offset+uuid_len*2].decode("utf-16le", errors="replace")
    offset += uuid_len * 2

    # Container ID byte / index
    container_num = data[offset]
    offset += 1
    
    # 4 bytes unknown / flags
    flags = struct.unpack("<I", data[offset:offset+4])[0]
    offset += 4

    # 8 bytes timestamp (FileTime)
    filetime = struct.unpack("<Q", data[offset:offset+8])[0]
    offset += 8

    print(f"  [{i:02d}] Name: {cname:<30} GUID: {uuid_str} (container.{container_num})")
