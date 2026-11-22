"""Stratified WAV-only read sampling; no writes/attribute changes on E:."""
import os, json, random, ctypes, math, statistics
from pathlib import Path
from collections import defaultdict
from datetime import datetime, timezone
OUT = Path(r"C:\AI-BS\backups\e_drive_assessment_20261027")
# Reuse already verified in-memory codec definitions without rerunning old sampling.
namespace = {}
source = Path(r"C:\AI-BS\scratch\sample_e_compression_readonly_20261027.py").read_text()
exec(source.split("# API sanity checks",1)[0],namespace)
estimate = namespace["estimate"]
buckets = defaultdict(list)
errors = []
stack = ["E:/"]
while stack:
 p = stack.pop()
 try:
  with os.scandir(p) as entries:
   for ent in entries:
    try:
     if ent.is_dir(follow_symlinks=False):
      st = ent.stat(follow_symlinks=False)
      if not getattr(st,"st_file_attributes",0)&0x400: stack.append(ent.path)
     elif ent.name.lower().endswith(".wav") and ent.is_file(follow_symlinks=False):
      st = ent.stat(follow_symlinks=False)
      if getattr(st,"st_file_attributes",0)&(0x400|0x1000|0x4000|0x200): continue
      size = st.st_size
      if size < 65536: continue
      key = "64KiB-1MiB" if size<2**20 else "1-10MiB" if size<10*2**20 else "10MiB+"
      buckets[key].append((ent.path,size,st.st_mtime_ns))
    except OSError as e:
     if len(errors)<10: errors.append({"path":ent.path,"type":type(e).__name__})
 except OSError: pass
rng = random.Random(20261027)
groups, details = [], []
for key, files in sorted(buckets.items()):
 selected = rng.sample(files,min(64,len(files)))
 measurements = []
 for path,size,mtime in selected:
  try:
   units = size//65536
   offsets = rng.sample(range(units),min(4,units))
   total=packed=0
   with open(path,"rb") as h:
    for idx in offsets:
     h.seek(idx*65536)
     data=h.read(65536)
     if len(data)==65536:
      total+=65536
      packed+=estimate(data)
   if not total or os.stat(path).st_mtime_ns!=mtime: continue
   frac=1-packed/total
   measurements.append((size,size*frac,total,frac))
   details.append({"path":path,"bucket":key,"logical_bytes":size,"sample_bytes":total,"estimated_saving_fraction":frac})
  except OSError as e:
   errors.append({"path":path,"type":type(e).__name__})
 sampled_bytes=sum(s for s,_,_,_ in measurements)
 # Sample size-weighted ratio within narrow file-size strata, projected to stratum bytes.
 ratio=sum(saving for _,saving,_,_ in measurements)/sampled_bytes if sampled_bytes else 0
 stratum_bytes=sum(s for _,s,_ in files)
 groups.append({"bucket":key,"population_files":len(files),"population_bytes":stratum_bytes,
  "sampled_files":len(measurements),"content_bytes_read":sum(n for _,_,n,_ in measurements),
  "sample_size_weighted_saving_fraction":ratio,"projected_saving_bytes":stratum_bytes*ratio})
result={"timestamp_utc":datetime.now(timezone.utc).isoformat(),"writes_to_e":False,"compression_applied":False,
 "method":"Up to64 uniformly selected WAV files per size stratum, up to4 uniformly random64KiB units per file, in-memory LZNT1 with4KiB rounding; within-stratum size-weighted ratio.",
 "groups":groups,"sampled_files":details,"errors":errors,
 "projected_saving_bytes":sum(g["projected_saving_bytes"] for g in groups),
 "content_bytes_read":sum(g["content_bytes_read"] for g in groups),
 "limits":["Rough sample-based extrapolation, not a guaranteed/recoverable byte count or confidence interval.",
 "Excludes WAV files smaller than64KiB, inaccessible/reparse/offline/encrypted/sparse files.",
 "A compressible file is not automatically safe for latency-sensitive DAW use; active library eligibility remains unverified."]}
(OUT/"wav_stratified_samples.json").write_text(json.dumps(result,indent=2)+"\n",encoding="utf-8")
print(json.dumps({k:v for k,v in result.items() if k!="sampled_files"},indent=2))
