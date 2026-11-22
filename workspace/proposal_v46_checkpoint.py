"""Scoped source checkpoint; no private stores or environment capture."""
from pathlib import Path
from datetime import datetime, timezone
import hashlib, json, subprocess

ROOT = Path('C:/AI-BS')
checkpoint = ROOT / 'backups' / ('retained_proposal_5_329_46_' + datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ'))
checkpoint.mkdir()
paths = ['docs/CODEX_HANDOFF.md', 'docs/AI_BS_Autonomy_Implementation_Plan.md',
         'docs/engineering_ledger/2026-10-24_Codex_Engineering_Ledger.md',
         'docs/engineering_ledger/cloud_index.json', 'backend/routers/coding_preparation_router.py',
         'backend/core/coding_preparation.py', 'backend/core/coding_preparation_planning.py',
         'backend/core/coding_chat.py', 'backend/core/coding_workflow.py',
         'backend/core/coding_review.py', 'frontend/src/utils/projectPreparation.js',
         'frontend/src/components/CodingPreparationPanel.jsx', 'frontend/vite.config.js']
manifest = {}
for name in paths:
    data = (ROOT/name).read_bytes()
    target = checkpoint/'before'/name
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(data)
    manifest[name] = hashlib.sha256(data).hexdigest()
manifest['git_head'] = subprocess.check_output(['git','rev-parse','HEAD'], cwd=ROOT, text=True).strip()
manifest['tracked_changes'] = len(subprocess.check_output(['git','status','--porcelain=v1','-uno'], cwd=ROOT, text=True).splitlines())
(checkpoint/'before_manifest.json').write_text(json.dumps(manifest, indent=2), encoding='utf-8')
(ROOT/'workspace/proposal_v46_checkpoint.txt').write_text(str(checkpoint), encoding='utf-8')
ledger = ROOT/'docs/engineering_ledger/2026-10-24_Codex_Engineering_Ledger.md'
with ledger.open('a', encoding='utf-8') as out:
    out.write('\n\n## Record 29 - Resume retained multi-file proposal milestone (in progress)\n\n'
        'Request: continue the project plan in the handoff. Reviewed latest plan1.57/source45 and current code. '
        'Current OS inspection confirms only the existing loopback frontend; backend/gateway/model are stopped. '
        'Next bounded implementation: independently authenticated, owner-scoped reviewed-plan to retained exact-hunk proposal/diff. '
        'Require complete retained source within explicit bounds, reject incomplete/ambiguous/overlapping edits, preserve selected checks/dependencies and all attempts. '
        'No generated code execution, original promotion, VM retry, browser-policy workaround or publication. '
        'Read-only runtime audit and isolated test authoring are delegated; source changes remain one bounded milestone. '
        f'Before-images: {checkpoint.relative_to(ROOT).as_posix()}. Cloud sync pending this new content.\n')
print(str(checkpoint))
