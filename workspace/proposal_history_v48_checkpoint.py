from datetime import datetime,timezone
from pathlib import Path
import hashlib,json
root=Path(r'C:\AI-BS');cp=root/'backups'/('proposal_history_5_329_48_'+datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ'))
cp.mkdir();(root/'workspace/proposal_history_v48_checkpoint.txt').write_text(str(cp),encoding='utf-8')
paths=['backend/core/coding_preparation_proposals.py','backend/routers/coding_preparation_router.py','frontend/src/utils/projectPreparation.js',
       'docs/CODEX_HANDOFF.md','docs/AI_BS_Autonomy_Implementation_Plan.md','docs/engineering_ledger/2026-10-24_Codex_Engineering_Ledger.md','docs/engineering_ledger/cloud_index.json']
paths += [base+'/CodingPreparationPanel.jsx' for base in ['frontend/src/components','frontend/components','frontend/src/components/components','frontend/components/components']]
manifest={}
for name in paths:
    raw=(root/name).read_bytes();p=cp/'before'/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(raw);manifest[name]=hashlib.sha256(raw).hexdigest()
(cp/'before_manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8');print(str(cp))
