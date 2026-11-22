"""Bounded in-memory LZNT1 sample estimate; never sets compression or writes E:."""
import ctypes, json, math, os
from pathlib import Path
from datetime import datetime, timezone
OUT = Path(r"C:\AI-BS\backups\e_drive_assessment_20261027")
candidates = json.loads((OUT/"sample_candidates.json").read_text(encoding="utf-8"))
inventory = json.loads((OUT/"inventory.json").read_text(encoding="utf-8"))
nt = ctypes.WinDLL("ntdll")
getws = nt.RtlGetCompressionWorkSpaceSize
getws.argtypes = [ctypes.c_ushort,ctypes.POINTER(ctypes.c_ulong),ctypes.POINTER(ctypes.c_ulong)]
getws.restype = ctypes.c_long
compress = nt.RtlCompressBuffer
compress.argtypes = [ctypes.c_ushort,ctypes.c_void_p,ctypes.c_ulong,ctypes.c_void_p,ctypes.c_ulong,ctypes.c_ulong,ctypes.POINTER(ctypes.c_ulong),ctypes.c_void_p]
compress.restype = ctypes.c_long
ws_size, frag_size = ctypes.c_ulong(), ctypes.c_ulong()
if getws(2,ctypes.byref(ws_size),ctypes.byref(frag_size)) != 0: raise RuntimeError("LZNT1 workspace query failed")
workspace = ctypes.create_string_buffer(ws_size.value)
def estimate(data):
 src = ctypes.create_string_buffer(data)
 dst = ctypes.create_string_buffer(len(data)*2+4096)
 written = ctypes.c_ulong()
 status = compress(2,src,len(data),dst,len(dst),4096,ctypes.byref(written),workspace)
 if status == 279: return 0  # STATUS_BUFFER_ALL_ZEROS, informational success.
 if status < 0: raise RuntimeError("LZNT1 compression status " + str(status))
 return min(len(data),math.ceil(written.value/4096)*4096)
# API sanity checks against compressible and random buffers, no disk write.
zero_alloc = estimate(bytes(65536))
random_alloc = estimate(os.urandom(65536))
if not (zero_alloc < 65536 and random_alloc == 65536): raise RuntimeError("Compression sanity check failed")
extensions = [".wav",".aif",".aiff",".flac",".mp3",".ogg",".mp4",".jpg",".png",".zip",".7z",".rar",".tar",".txt",".log",".json",".dll",".exe",".pdb",".pak",".ucas",".bin",".gguf",".safetensors"]
results = []
total_read = 0
for ext in extensions:
 files = candidates.get(ext,[])
 ext_results = []
 for f in files:
  path = Path(f["path"])
  try:
   st = path.stat(follow_symlinks=False)
   attrs = getattr(st,"st_file_attributes",0)
   if attrs & (0x400 | 0x1000 | 0x4000 | 0x200): continue
   size = st.st_size
   units = size//65536
   offsets = sorted(set([0,max(0,units//2)*65536,max(0,units-1)*65536]))
   raw = compressed = 0
   with path.open("rb") as h:
    for offset in offsets:
     h.seek(offset)
     data = h.read(65536)
     if len(data) != 65536: continue
     raw += len(data); compressed += estimate(data)
   if not raw: continue
   changed = path.stat(follow_symlinks=False).st_mtime_ns != st.st_mtime_ns
   total_read += raw
   ext_results.append({"path":str(path),"top_folder":f["top_folder"],"logical_bytes":size,
    "existing_allocated_bytes":f["allocated_bytes"],"existing_ntfs_compressed":bool(attrs&0x800),
    "sample_bytes":raw,"estimated_sample_allocated_bytes":compressed,
    "estimated_saving_fraction":1-compressed/raw,"changed_during_read":changed})
  except OSError as exc:
   ext_results.append({"path":str(path),"error_type":type(exc).__name__,"winerror":getattr(exc,"winerror",None)})
 valid = [f for f in ext_results if "sample_bytes" in f and not f["changed_during_read"] and not f["existing_ntfs_compressed"]]
 sampled = sum(f["sample_bytes"] for f in valid)
 comp = sum(f["estimated_sample_allocated_bytes"] for f in valid)
 summary = {"extension":ext,"files_sampled":len(valid),"sample_bytes":sampled,
   "mean_saving_fraction":1-comp/sampled if sampled else None,"files":ext_results,
   "drive_logical_bytes_for_extension":inventory["extensions"].get(ext,{}).get("logical_bytes",0)}
 if sampled:
  summary["file_saving_fraction_range"]=[min(f["estimated_saving_fraction"] for f in valid),max(f["estimated_saving_fraction"] for f in valid)]
 results.append(summary)
receipt = {"timestamp_utc":datetime.now(timezone.utc).isoformat(),"bytes_read_from_e":total_read,
 "writes_to_e":False,"compression_applied":False,"algorithm":"In-memory RtlCompressBuffer LZNT1, 64KiB units, 4KiB allocation rounding",
 "sanity":{"zero_unit_estimated_allocated":zero_alloc,"random_unit_estimated_allocated":random_alloc},
 "limits":["Illustrative bounded samples, not a whole-file/drive compact dry run or guaranteed savings.",
 "At most 12 deterministic path-hash sampled files per extension and three 64KiB units per file.",
 "Not byte-weighted random sampling across all E data; per-extension projection can be biased.",
 "NTFS metadata, full-file variation, sparse handling, already-compressed WOF files and live changes can affect actual saving.",
 "Reads can affect access timestamps/cache state; no contents, names, attributes or compression settings were changed."],
 "results":results}
(OUT/"compression_samples.json").write_text(json.dumps(receipt,indent=2)+"\n",encoding="utf-8")
print(json.dumps({"bytes_read":total_read,"compression_applied":False,"results":[{k:v for k,v in r.items() if k!="files"} for r in results]},indent=2))
