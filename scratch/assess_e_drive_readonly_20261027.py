"""Read-only E: metadata inventory; writes evidence under C: only."""
import os, json, ctypes, heapq, time, hashlib, shutil
from pathlib import Path
from collections import defaultdict
from datetime import datetime, timezone

ROOT = Path("E:/")
OUT = Path(r"C:\AI-BS\backups\e_drive_assessment_20261027")
OUT.mkdir(exist_ok=False)
started = datetime.now(timezone.utc).isoformat()
kernel = ctypes.WinDLL("kernel32", use_last_error=True)
getsize = kernel.GetCompressedFileSizeW
getsize.argtypes = [ctypes.c_wchar_p, ctypes.POINTER(ctypes.c_uint32)]
getsize.restype = ctypes.c_uint32
groups, exts = {}, {}
largest, samples = [], defaultdict(list)
errors, reparse = [], []
seen_links = set()
total_files = total_dirs = skipped_links = inaccessible = 0
last_notice = time.monotonic()
def newstat():
 return {"files":0,"logical_bytes":0,"allocated_bytes":0,"allocation_query_errors":0,
         "ntfs_compressed_files":0,"sparse_files":0,"encrypted_files":0,"offline_files":0,"hardlink_duplicates":0}
def alloc_size(path):
 high = ctypes.c_uint32()
 ctypes.set_last_error(0)
 low = getsize(path, ctypes.byref(high))
 if low == 0xffffffff and ctypes.get_last_error():
  return None
 return (high.value << 32) | low
def account(dst, st, attrs, allocated, duplicate):
 dst["files"] += 1
 dst["logical_bytes"] += st.st_size
 dst["hardlink_duplicates"] += int(duplicate)
 if allocated is None:
  dst["allocation_query_errors"] += 1
 elif not duplicate:
  dst["allocated_bytes"] += allocated
 dst["ntfs_compressed_files"] += bool(attrs & 0x800)
 dst["sparse_files"] += bool(attrs & 0x200)
 dst["encrypted_files"] += bool(attrs & 0x4000)
 dst["offline_files"] += bool(attrs & 0x1000)
stack = [(str(ROOT), None)]
while stack:
 folder, top = stack.pop()
 try:
  with os.scandir(folder) as entries:
   for ent in entries:
    try:
     st = ent.stat(follow_symlinks=False)
     attrs = getattr(st, "st_file_attributes", 0)
     if attrs & 0x400:
      skipped_links += 1
      if len(reparse) < 100: reparse.append(ent.path)
      continue
     if ent.is_dir(follow_symlinks=False):
      total_dirs += 1
      stack.append((ent.path, top or ent.name))
      continue
     if not ent.is_file(follow_symlinks=False): continue
     total_files += 1
     group = top or "[root files]"
     ext = Path(ent.name).suffix.lower() or "[no extension]"
     ident = (st.st_dev, st.st_ino)
     duplicate = st.st_nlink > 1 and ident in seen_links
     if st.st_nlink > 1: seen_links.add(ident)
     allocated = alloc_size(ent.path)
     account(groups.setdefault(group,newstat()), st, attrs, allocated, duplicate)
     account(exts.setdefault(ext,newstat()), st, attrs, allocated, duplicate)
     item = (st.st_size, ent.path, allocated, attrs)
     if len(largest) < 60: heapq.heappush(largest,item)
     elif item[0] > largest[0][0]: heapq.heapreplace(largest,item)
     # Deterministic bounded sample per extension; no content read in this stage.
     if st.st_size >= 65536 and not attrs & (0x4000 | 0x1000 | 0x400 | 0x200):
      score = int.from_bytes(hashlib.sha256(ent.path.casefold().encode("utf-8")).digest()[:8],"big")
      bucket = samples[ext]
      candidate = (-score, ent.path, st.st_size, allocated, attrs, group)
      if len(bucket) < 12: heapq.heappush(bucket,candidate)
      elif candidate[0] > bucket[0][0]: heapq.heapreplace(bucket,candidate)
    except OSError as exc:
     inaccessible += 1
     if len(errors) < 60: errors.append({"path":ent.path,"error_type":type(exc).__name__,"winerror":getattr(exc,"winerror",None)})
 except OSError as exc:
  inaccessible += 1
  if len(errors) < 60: errors.append({"path":folder,"error_type":type(exc).__name__,"winerror":getattr(exc,"winerror",None)})
 if time.monotonic() - last_notice > 10:
  print(json.dumps({"progress_files":total_files,"pending_directories":len(stack)}),flush=True)
  last_notice = time.monotonic()
usage = shutil.disk_usage(ROOT)
result = {"started_utc":started,"finished_utc":datetime.now(timezone.utc).isoformat(),
 "root":str(ROOT),"read_only_on_e":True,"content_reads":False,"compression_deletion_or_disk_change":False,
 "volume_bytes":{"total":usage.total,"used":usage.used,"free":usage.free},
 "files":total_files,"directories":total_dirs,"skipped_reparse":skipped_links,"inaccessible_count":inaccessible,
 "groups":dict(sorted(groups.items(),key=lambda kv:kv[1]["allocated_bytes"],reverse=True)),
 "extensions":dict(sorted(exts.items(),key=lambda kv:kv[1]["allocated_bytes"],reverse=True)),
 "largest_files":[{"path":p,"logical_bytes":s,"allocated_bytes":a,"attributes":at} for s,p,a,at in sorted(largest,reverse=True)],
 "reparse_examples":reparse,"errors":errors,
 "limits":["Live metadata snapshot; files may change during scan.",
 "Reparse targets not traversed. Inaccessible and system metadata may be uncounted.",
 "Hardlink allocated bytes counted once globally; folder attribution depends on first encounter.",
 "Allocation includes sparse/compressed storage but not all filesystem metadata or alternate streams."]}
(OUT/"inventory.json").write_text(json.dumps(result,indent=2)+"\n",encoding="utf-8")
manifest = {ext:[{"path":p,"logical_bytes":s,"allocated_bytes":a,"attributes":at,"top_folder":g}
 for _,p,s,a,at,g in sorted(items,reverse=True)] for ext,items in samples.items()}
(OUT/"sample_candidates.json").write_text(json.dumps(manifest,indent=2)+"\n",encoding="utf-8")
print(json.dumps({"evidence":str(OUT),"files":total_files,"directories":total_dirs,"skipped_reparse":skipped_links,
 "errors":inaccessible,"volume_gib":{k:round(v/2**30,2) for k,v in result["volume_bytes"].items()},
 "top_folders":[{"folder":k,"logical_gib":round(v["logical_bytes"]/2**30,3),"allocated_gib":round(v["allocated_bytes"]/2**30,3),"files":v["files"]} for k,v in list(result["groups"].items())[:20]],
 "top_extensions":[{"extension":k,"logical_gib":round(v["logical_bytes"]/2**30,3),"allocated_gib":round(v["allocated_bytes"]/2**30,3),"files":v["files"]} for k,v in list(result["extensions"].items())[:18]]}),flush=True)
