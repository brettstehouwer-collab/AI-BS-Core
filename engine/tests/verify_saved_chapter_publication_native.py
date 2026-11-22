"""Actual six-pack saved export + native stage-store + retained publication.

No capability files are modified, no player or SQLite database is opened, and
no GPU/playthrough is claimed. Existing source projects are read-only inputs.
"""
import argparse,hashlib,json,os,shutil,sys,time
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,'C:/AI-BS')
from PyQt6.QtWidgets import QApplication
from native_studio.game_engine.content_view import ContentView
from native_studio.game_engine.saved_chapter_export import SavedChapterExportClient,hash_saved_journal
from native_studio.game_engine.project_assets import ProjectAssetClient
from native_studio.game_engine.saved_play_storage import (
    prepare_publication,finish_publication,revalidate_publication,discard_staging)

def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def inventory(root):return {p.relative_to(root).as_posix():{'bytes':p.stat().st_size,'sha256':sha(p)}for p in root.rglob('*')if p.is_file()}
def main():
    p=argparse.ArgumentParser();p.add_argument('--host',required=True,type=Path);p.add_argument('--cooker',required=True,type=Path)
    p.add_argument('--source-project',required=True,type=Path);p.add_argument('--project',required=True,type=Path);p.add_argument('--evidence',required=True,type=Path)
    a=p.parse_args();host=a.host.resolve(strict=True);cooker=a.cooker.resolve(strict=True);source=a.source_project.resolve(strict=True)
    project=a.project.resolve();project.mkdir(parents=True,exist_ok=False);out=a.evidence.resolve();out.mkdir(parents=True,exist_ok=False)
    app=QApplication.instance()or QApplication([]);view=None;jobs=[];stagers=[];preparations=[]
    report={'status':'failed','scope':'Actual saved export and native typed six-pack publication only',
        'native_player_launched':False,'native_database_opened':False,'walking_verified':False,'gpu_requested':False,
        'original_family_media_used':False,'source_project':str(source),'project':str(project),
        'host_sha256':sha(host),'cooker_sha256':sha(cooker),'checks':[],'publications':[]}
    protected=inventory(source)
    def check(value,label):
        if not value:raise AssertionError(label)
        report['checks'].append(label)
    def spin(predicate,label,seconds=45):
        end=time.monotonic()+seconds
        while not predicate()and time.monotonic()<end:app.processEvents();time.sleep(.002)
        check(bool(predicate()),label)
    def idle():spin(lambda:view.loaded and not view.busy and not view.client.pending_count,'Primary native owner coherent')
    def saved_export():
        with patch.object(view,'_use_snapshot'):
            view._begin_export('preview');idle()
        original=view._content_snapshot;definition=view.definition;journal=hash_saved_journal(project)
        job=SavedChapterExportClient();jobs.append(job);results=[];failed=[];closed=[]
        job.completed.connect(results.append);job.failed.connect(failed.append);job.closed.connect(lambda:closed.append(True))
        job.start(host,definition,original,context_valid=lambda:view._saved_context_matches(original,definition))
        spin(lambda:bool(closed),'Actual saved-reader child joined')
        check(not failed and len(results)==1,'Actual saved native export accepted')
        check(results[0].snapshot==original and len(original.asset_refs)==6,'Current complete six-pack identity preserved')
        check(hash_saved_journal(project)==journal,'Publication export leaves saved journal unchanged')
        return results[0].snapshot
    def stage(snapshot):
        prep=prepare_publication(project,snapshot);preparations.append(prep)
        client=ProjectAssetClient(cooker);stagers.append(client);receipts=[];failed=[];closed=[]
        client.receipt.connect(lambda mode,value:receipts.append((mode,value)));client.failed.connect(failed.append);client.closed.connect(lambda:closed.append(True))
        client.stage_store(snapshot.asset_store,prep.staging/'assets/packs',snapshot.asset_refs,profile=snapshot.asset_profile)
        spin(lambda:bool(closed),'Actual typed asset-cooker child joined')
        check(not client.busy and not client.process_id and not failed and len(receipts)==1,'Six typed packs validated by native stage-store')
        check(receipts[0][0]=='stage'and len(receipts[0][1]['refs'])==6,'Native stage-store receipt binds all six references')
        publication=finish_publication(prep,context_valid=lambda:view._saved_context_matches(snapshot,view.definition))
        revalidate_publication(publication)
        check(publication.content_path.read_bytes()==snapshot.payload,'Published content equals freshly saved native export')
        expected=inventory(snapshot.asset_store);actual=inventory(publication.asset_root)
        wanted={name:row for name,row in expected.items()if name.split('/')[0]in {r.pack_sha256 for r in snapshot.asset_refs}}
        check(actual==wanted and len(actual)==24,'Every staged pack byte matches complete project-owned six-pack closure')
        report['publications'].append({'fingerprint':snapshot.fingerprint,'checkpoint_id':snapshot.checkpoint_id,
            'timeline_id':publication.timeline_id,'content':str(publication.content_directory),'slot':str(publication.slot_directory),
            'reused_publication':publication.reused_publication,'reused_slot':publication.reused_slot,'pack_files':len(actual),
            'pack_bytes':sum(r['bytes']for r in actual.values()),'record_sha256':publication.record_sha256})
        return publication
    try:
        for name,row in protected.items():
            if name.endswith('.lock'):continue
            target=project/name;target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(source/name,target)
            check(sha(target)==row['sha256'],'Owned source copy '+name)
        view=ContentView(host);view.open_project(project);idle()
        original=saved_export();first=stage(original);retained=inventory(project/'.aibs-runtime'/'content'),inventory(project/'.aibs-runtime'/'saves')
        # A real SAVE can create a new authoring checkpoint without changing the
        # gameplay content fingerprint or its retained player timeline.
        view.save_world();idle();same=saved_export();check(same.fingerprint==original.fingerprint,'Identical actual saved content retains its fingerprint')
        second=stage(same)
        check(second.timeline_id==first.timeline_id and second.reused_publication and second.reused_slot,'Re-export/Save reuses publication and stable timeline')
        check((inventory(project/'.aibs-runtime'/'content'),inventory(project/'.aibs-runtime'/'saves'))==retained,'Identical publication leaves retained bytes unchanged')
        view.add_fixture('Saved publication branch marker');idle();view.save_world();idle();changed=saved_export()
        check(changed.fingerprint!=original.fingerprint,'Actual saved content edit produces a distinct fingerprint')
        third=stage(changed)
        check(third.timeline_id!=first.timeline_id and third.slot_directory!=first.slot_directory,'Changed saved chapter gets a distinct compatible save branch')
        check(first.slot_directory.exists()and first.content_directory.exists(),'Old compatible publication/slot retained after new branch')
        before_cancel=inventory(project/'.aibs-runtime'/'content'),inventory(project/'.aibs-runtime'/'saves')
        prep=prepare_publication(project,changed);preparations.append(prep)
        client=ProjectAssetClient(cooker);stagers.append(client);closed=[];receipts=[];failed=[]
        client.closed.connect(lambda:closed.append(True));client.receipt.connect(lambda *args:receipts.append(args));client.failed.connect(failed.append)
        client.stage_store(changed.asset_store,prep.staging/'assets/packs',changed.asset_refs,profile=changed.asset_profile);client.stop()
        spin(lambda:bool(closed),'Cancelled native staging child actually joined')
        check(not client.process_id and not client.busy and not receipts and bool(failed),'Cancelled stage cannot masquerade as successful admission')
        discard_staging(prep)
        check(not prep.staging.exists(),'Only cancelled invocation staging removed after child join')
        check((inventory(project/'.aibs-runtime'/'content'),inventory(project/'.aibs-runtime'/'saves'))==before_cancel,'Cancellation preserves every retained content/slot byte')
        check(not any((project/'.aibs-runtime').rglob('world.sqlite')),'No native database was created or opened by publication proof')
        check(inventory(source)==protected,'All original project source bytes unchanged')
        report['status']='passed'
    except Exception as error:
        report['error']=repr(error);raise
    finally:
        for client in stagers:client.shutdown()
        for job in jobs:job.stop()
        if view is not None:
            view.saved_export.stop();view.saved_play.stop();view.asset_client.shutdown();view.play._shutdown();view.viewport._shutdown();view.client.stop()
        spin(lambda:not any(j.process_id for j in jobs)and not any(c.process_id for c in stagers)and(view is None or not view.client.process_id),'All owned native children joined',8)
        report['source_project_unchanged']=inventory(source)==protected
        report['host_unchanged']=sha(host)==report['host_sha256'];report['cooker_unchanged']=sha(cooker)==report['cooker_sha256']
        report['all_owned_processes_joined']=True
        if view is not None:view.definition=None;view.deleteLater();app.processEvents()
        (out/'verification.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'status':report['status'],'checks':len(report['checks']),'report':str(out/'verification.json')}))
if __name__=='__main__':main()
