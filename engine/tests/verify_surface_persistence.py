"""Cross-process surface placement/history persistence; no GPU/window launch."""
from pathlib import Path
from datetime import datetime,timezone
import json,sys,subprocess,uuid,hashlib
from verify_surface_showcase import prepare_pack
def verify(cooker,fixture,output):
    output.mkdir(parents=True,exist_ok=True)
    pack,asset_id=prepare_pack(cooker,output/'source')
    project=output/('project-'+str(uuid.uuid4()))
    subprocess.run([str(fixture),str(pack),str(project)],check=True,timeout=90)
    expected=json.loads((project/'expected.json').read_text())
    journal=project/'project/chapter.aiba';original=journal.read_bytes()
    subprocess.run([str(fixture),'--reopen',str(project)],check=True,timeout=90)
    reopened=json.loads((project/'reopened.json').read_text())
    assert original==journal.read_bytes() and expected['asset_kind']=='surface'
    assert expected['placement_content_version']==3 and expected['texture_count']==1
    assert expected['textured_vertices']==940*3 and reopened['fingerprint']==expected['restored']['fingerprint']
    assert reopened['placement_id']==expected['placement_id'] and expected['asset_id']==asset_id
    for label in ['baseline','placed','moved','erased','restored','reopened']:
        blob=(project/(label+'.aibd')).read_bytes()
        assert blob[:6]==b'AIBD\x03\x00'
        assert hashlib.sha256(blob).hexdigest()==(reopened['fingerprint'] if label=='reopened' else expected[label]['fingerprint'])
    r={'schema_version':1,'status':'passed','completed_at':datetime.now(timezone.utc).isoformat(),'gpu_requested':False,'checks':['Actual cooked textured capacitor with owned PNG/license/provenance','Native private Preview, Apply, transform, erase and Undo/Redo','All content stages remain AIBD3','New process restores exact content fingerprint and placement UUID','Saved journal bytes unchanged by reopen','Legacy template bytes retained by fixture'],'project_directory':str(project),'expected':expected,'reopened':reopened}
    (output/'verification.json').write_text(json.dumps(r,indent=2)+'\n')
    print('PASS native cross-process textured placement/history persistence, no GPU requested')
if __name__=='__main__':verify(*(Path(p).resolve() for p in sys.argv[1:]))
