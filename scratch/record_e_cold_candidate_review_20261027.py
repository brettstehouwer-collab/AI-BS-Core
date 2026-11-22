from pathlib import Path
from datetime import datetime, timezone
import hashlib
import json

root = Path(r"C:\AI-BS")
out = root / "backups/e_drive_assessment_20261027"
backup = out / "cold_candidate_review_originals"
backup.mkdir(exist_ok=False)
sample = json.loads((out / "cold_candidate_samples.json").read_text())
stamp = datetime.now(timezone.utc).isoformat()
log = next(item for item in sample["results"] if item["path"] == r"E:\move_log.txt")
archives = [item for item in sample["results"] if item["path"].lower().endswith(".zip")]
summary = (
    "User asks what can be compressed and the next step. Active sample/loop libraries remain protected. "
    "Expanded read-only assessment sampled 64 randomly selected 64KiB units per root photo ZIP/installer "
    "and read the entire old move_log.txt in memory. The 22.42MiB log, last written 2026-07-13, has "
    f"an estimated LZNT1 saving of {log['projected_saved_bytes']/2**20:.2f}MiB; this is a projection, not measured reclaimed space. "
    "Most ZIP archives and both root installers sampled at zero saving; the earlier 16-19% endpoint-only "
    "New Folder ZIP samples were unrepresentative (expanded random samples: 0% and about0.49%). "
    "No worthwhile large inactive compression target has been established. SteamLibrary occupies241.61GiB "
    "in the retained inventory; identifying unused games for operator-selected relocation/uninstall is a "
    "separate possible space-reclamation path, with no deletion or move authorized/applied. "
    "No E: content, path, attributes or compression settings changed; no process/service/VM/disk changes. "
    "Evidence: backups/e_drive_assessment_20261027/cold_candidate_samples.json. "
    "Preserve prior samples as historical evidence; cloud synchronization remains pending.\n"
)
paths = ["docs/E_DRIVE_COMPRESSION_ASSESSMENT_2026-10-27.md", "docs/CODEX_HANDOFF.md",
         "docs/CODEX_JOURNAL.md", "docs/CODEX_TASKS.md",
         "docs/engineering_ledger/2026-10-24_Codex_Engineering_Ledger.md"]
receipt = {"timestamp_utc": stamp, "record": 152, "compression_applied": False,
           "reclaimed_bytes_confirmed": 0, "documents": [], "evidence": []}
for rel in paths:
    path = root / rel
    before = path.read_bytes()
    (backup / path.name).write_bytes(before)
    addition = "\n\n### Record152 follow-up - Cold candidate review - " + stamp + "\n" + summary
    if rel.endswith("CODEX_TASKS.md"):
        addition += ("\n- [x] Assess root installers, photo ZIPs and move_log.txt using bounded reads.\n"
                     "- [ ] Larger safe compression target remains unestablished; active sample, database/model and VM/WSL exclusions remain.\n")
    with path.open("ab") as stream:
        stream.write(addition.encode())
    after = path.read_bytes()
    assert after.startswith(before)
    receipt["documents"].append({"path": rel, "before_sha256": hashlib.sha256(before).hexdigest(),
                                 "after_sha256": hashlib.sha256(after).hexdigest(), "prior_byte_prefix_preserved": True})
script = root / "scratch/sample_e_cold_candidates_20261027.py"
(out / script.name).write_bytes(script.read_bytes())
for path in [out / "cold_candidate_samples.json", out / script.name]:
    receipt["evidence"].append({"path": str(path), "sha256": hashlib.sha256(path.read_bytes()).hexdigest()})
(out / "cold_candidate_review.json").write_text(json.dumps(receipt, indent=2) + "\n")
print(json.dumps({"record": 152, "documents_appended": len(receipt["documents"]),
                  "prior_bytes_preserved": True, "estimated_log_saving_MiB": log["projected_saved_bytes"]/2**20,
                  "sampled_archive_count": len(archives), "compression_applied": False}))
