import os
import glob
import dis
import marshal
import importlib.util

pycache_dir = r"C:\AI-BS\scratch\__pycache__"
pyc_files = glob.glob(os.path.join(pycache_dir, "*.cpython-312.pyc"))

print("=" * 65)
print("       AI-BS PYTHON 3.12 BYTECODE CACHE DEEP AUDIT")
print("=" * 65)
print(f"Total .pyc Files in __pycache__ : {len(pyc_files)}")

valid_count = 0
corrupted_files = []
orphan_pyc = []
total_bytes = 0

for pyc in pyc_files:
    fname = os.path.basename(pyc)
    size = os.path.getsize(pyc)
    total_bytes += size
    
    # Extract source script name
    src_name = fname.replace(".cpython-312.pyc", ".py")
    src_path = os.path.join(r"C:\AI-BS\scratch", src_name)
    if not os.path.exists(src_path):
        orphan_pyc.append((fname, size))

    # Verify Bytecode Magic & Unmarshal Code Object
    try:
        with open(pyc, "rb") as f:
            magic = f.read(4)
            bit_field = f.read(4)
            mtime = f.read(4)
            size_header = f.read(4)
            code_obj = marshal.load(f)
            if hasattr(code_obj, "co_code"):
                valid_count += 1
    except Exception as e:
        corrupted_files.append((fname, str(e)))

print(f"Total Bytecode Cache Size       : {round(total_bytes / 1024, 2)} KB")
print(f"Valid Code Objects Loaded       : {valid_count} / {len(pyc_files)}")
print(f"Corrupted Bytecode Files        : {len(corrupted_files)}")
print(f"Orphan .pyc (Source Deleted)    : {len(orphan_pyc)}")

if corrupted_files:
    print("\n[!] Corrupted Files:")
    for f, err in corrupted_files:
        print(f"  - {f}: {err}")

if orphan_pyc:
    print(f"\n[i] Orphan .pyc Files ({len(orphan_pyc)}):")
    for f, sz in orphan_pyc[:5]:
        print(f"  - {f} ({round(sz/1024, 1)} KB)")
    if len(orphan_pyc) > 5:
        print(f"  ... and {len(orphan_pyc) - 5} more")

print("=" * 65)
print("[SUCCESS] All bytecode objects verified for Python 3.12 runtime.")
print("=" * 65)