"""Fixed synthetic v2 client for owned controller tests; no original data."""
from pathlib import Path
import sys
import time

root=Path(sys.argv[1])
sys.path.insert(0,str(root));sys.path.insert(0,str(root/'backend'))
sys.path.insert(0,sys.argv[3])  # Fixed reviewed recovery dependency directory.
from native_studio.creative_session import bootstrap_native_session

session=None
phase=21
try:
    session,packet=bootstrap_native_session([sys.argv[0],'--native-creative-pipe-bootstrap'],sys.stdin.buffer)
    from native_studio.screenplay_client import ScreenplayClient
    client=ScreenplayClient(creative_session=session)
    phase=22
    view=client.read(packet.project)
    phase=23
    if sys.argv[2] in ('save-exit','save-hold'):
        value=client.save(packet.project,view['content']+'\nSynthetic owned pipe edit.\n',view['revision'])
        phase=24
        assert client.read(packet.project)['revision']==value['revision']
    if sys.argv[2] in ('save-hold','read-hold'):
        time.sleep(60)
    if sys.argv[2]=='idle-read-exit':
        time.sleep(31.2)
        phase=25
        assert client.read(packet.project)['revision']==view['revision']
    phase=0
except Exception:
    pass
finally:
    if session is not None:session.close()
raise SystemExit(phase)
