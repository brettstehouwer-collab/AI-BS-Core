"""Read-only E: candidate assessment; writes diagnostics only under C:/AI-BS."""
from pathlib import Path
from datetime import datetime, timezone
import hashlib
import json
import random

OUT = Path(r"C:\AI-BS\backups\e_drive_assessment_20261027")
helper = Path(r"C:\AI-BS\scratch\sample_e_compression_readonly_20261027.py").read_text()
scope = {}
exec(compile(helper.split("# API sanity checks", 1)[0], "lznt1_helper", "exec"), scope)
estimate = scope["estimate"]
assert estimate(bytes(65536)) == 0
photos = Path(r"E:\Google phtos download from drive 2013")
paths = sorted(photos.glob("*.zip"))
paths += [Path(r"E:\move_log.txt"), Path(r"E:\BS-Studio Setup 5.151.0.exe"), Path(r"E:\Salad-1.9.27.exe")]
results = []
for path in paths:
    try:
        before = path.stat(follow_symlinks=False)
        if before.st_file_attributes & (0x400 | 0x1000 | 0x4000 | 0x200):
            continue
        units = (before.st_size + 65535) // 65536
        full = path.name == "move_log.txt"
        rng = random.Random(int.from_bytes(hashlib.sha256(str(path).encode()).digest()[:8], "big"))
        picks = range(units) if full else sorted(rng.sample(range(units), min(64, units)))
        raw = allocated = 0
        digest = hashlib.sha256() if full else None
        with path.open("rb") as stream:
            for unit in picks:
                stream.seek(unit * 65536)
                data = stream.read(65536)
                raw += len(data)
                allocated += estimate(data)
                if digest is not None:
                    digest.update(data)
        after = path.stat(follow_symlinks=False)
        stable = (before.st_size, before.st_mtime_ns) == (after.st_size, after.st_mtime_ns)
        fraction = 1 - allocated / raw if raw else 0
        results.append({"path": str(path), "logical_bytes": before.st_size,
                        "last_write_utc": datetime.fromtimestamp(before.st_mtime, timezone.utc).isoformat(),
                        "bytes_read": raw, "whole_file_read": full, "stable_size_and_mtime": stable,
                        "estimated_saving_fraction": fraction,
                        "projected_saved_bytes": round(before.st_size * fraction) if stable else None,
                        "content_sha256": digest.hexdigest() if digest is not None else None})
    except OSError as exc:
        results.append({"path": str(path), "error_type": type(exc).__name__, "winerror": getattr(exc, "winerror", None)})
receipt = {"timestamp_utc": datetime.now(timezone.utc).isoformat(), "read_only_on_e": True,
           "compression_applied": False, "method": "In-memory LZNT1, 64KiB units with 4KiB rounding; 64 path-seeded random units/archive or installer; entire move_log.txt",
           "limits": ["Projection only; no actual filesystem savings measured.", "Archive estimates do not establish inactivity or absence of application dependencies.", "No private contents retained; content reads can affect cache/access timestamps."], "results": results}
(OUT / "cold_candidate_samples.json").write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
for result in results:
    print(json.dumps({key: value for key, value in result.items() if key != "content_sha256"}))
