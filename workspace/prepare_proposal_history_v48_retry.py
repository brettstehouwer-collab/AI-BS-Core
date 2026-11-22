from pathlib import Path
import json
root=Path(r'C:\AI-BS');cp=Path((root/'workspace/proposal_history_v48_checkpoint.txt').read_text(encoding='utf-8').strip())
failure=json.loads((cp/'runtime/process.json').read_text(encoding='utf-8'))
assert failure['status']=='inspection_needed' and failure['controlled_stop']=={} and failure['reason']=='Inbound API connection is active; preserve it'
source=(root/'workspace/restart_proposal_history_v48.py').read_text(encoding='utf-8')
assert source.count("runtime = cp / 'runtime'")==1
source=source.replace("runtime = cp / 'runtime'","runtime = cp / 'runtime_after_connection_closed'")
with (root/'workspace/restart_proposal_history_v48_after_connection_closed.py').open('x',encoding='utf-8') as out:out.write(source)
print('Prepared one new observer attempt preserving the original failure and all restart guards')
