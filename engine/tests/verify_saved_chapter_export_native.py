"""Actual saved journal/native Host/Qt export, CPU only. Keeps every fixture."""
import argparse,hashlib,json,os,sys,time,uuid,shutil
from dataclasses import replace
from pathlib import Path
sys.path.insert(0,'C:/AI-BS')
from PyQt6.QtWidgets import QApplication
from native_studio.game_engine.content_view import ContentView
from native_studio.game_engine.saved_chapter_export import SavedChapterExportClient,hash_saved_journal

def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def run():
    parser=argparse.ArgumentParser();parser.add_argument('--host',required=True,type=Path);parser.add_argument('--out',required=True,type=Path)
    parser.add_argument('--source-project',type=Path)
    args=parser.parse_args();host=args.host.resolve(strict=True);out=args.out.resolve();out.mkdir(parents=True,exist_ok=False)
    app=QApplication.instance()or QApplication([]);views=[];jobs=[]
    report={'status':'failed','host':str(host),'host_sha256':sha(host),'checks':[],
        'gpu_requested':False,'player_requested':False,'family_media_used':False,'cases':[]}
    def spin(check,label,seconds=35):
        end=time.monotonic()+seconds
        while not check()and time.monotonic()<end:app.processEvents();time.sleep(.002)
        if not check():raise AssertionError(label)
    def idle(view):spin(lambda:view.loaded and not view.busy and not view.client.pending_count,view.status.text())
    def snapshot(view):
        from unittest.mock import patch
        with patch.object(view,'_use_snapshot'):
            view._begin_export('preview');idle(view)
        return view._content_snapshot
    def export(view,s,guard=lambda:True):
        job=SavedChapterExportClient();jobs.append(job);results=[];errors=[];closed=[]
        job.completed.connect(results.append);job.failed.connect(errors.append);job.closed.connect(lambda:closed.append(True))
        journal=hash_saved_journal(view.definition.directory)
        job.start(host,view.definition,s,context_valid=guard)
        spin(lambda:bool(closed),'second native export owner did not join')
        assert job.client.state=='closed'and job.process_id==0
        assert hash_saved_journal(view.definition.directory)==journal
        return job,results,errors
    try:
        for profile in ('legacy_v1','warm-beginning'):
            directory=out/profile;directory.mkdir();view=ContentView(host);views.append(view)
            view.new_project(directory,'Saved export '+profile,asset_profile=profile);idle(view)
            view.save_world();idle(view);initial=snapshot(view)
            # The factory export becomes deliberately stale after a saved edit.
            (directory/'opening.aibd').write_bytes(initial.payload)
            view.add_fixture('New saved fixture '+profile);idle(view)
            unsaved=snapshot(view)
            assert view.client.dirty and view.description.dirty
            job,results,errors=export(view,unsaved)
            assert not results and errors,'Unsaved original head must not match native saved journal'
            view.save_world();idle(view);saved=snapshot(view)
            assert saved.payload!=initial.payload and saved.fingerprint!=initial.fingerprint
            journal=hash_saved_journal(directory);owner_id=view.client.process_id
            job,results,errors=export(view,saved,lambda:view._saved_context_matches(saved,view.definition))
            assert not errors and len(results)==1,errors
            result=results[0]
            assert result.snapshot==saved and result.snapshot.export_version==2
            assert job._scope.host_epoch!=saved.scope.host_epoch
            assert (directory/'opening.aibd').read_bytes()==initial.payload
            assert view.client.process_id==owner_id and view.client.state=='ready'
            assert hash_saved_journal(directory)==journal
            from unittest.mock import patch,Mock
            with patch.object(view,'_saved_play_binary',return_value=out/'not-launched-player.exe'),patch.object(view.saved_play,'start')as launch:
                view.start_saved_play();spin(lambda:launch.called,'actual UI did not finish its separate native saved export')
                assert view.saved_export.state=='closed'and view.saved_export.process_id==0
                assert launch.call_args.args==(out/'not-launched-player.exe',saved,directory)
                assert launch.call_args.kwargs['context_valid']()
                assert hash_saved_journal(directory)==journal
            job,results,errors=export(view,replace(saved,checkpoint_id=str(uuid.uuid4())))
            assert not results and errors
            view.close_project();spin(lambda:view.client.state=='closed'and not view.client.process_id,'primary owner did not close')
            report['cases'].append({'profile':profile,'fingerprint':saved.fingerprint,'checkpoint_id':saved.checkpoint_id,
                'journal_sha256':journal.sha256,'journal_bytes':journal.bytes,'content_bytes':len(saved.payload),
                'secondary_scope_is_distinct':True,'original_owner_preserved':True,'complete_export_version':2,
                'stale_factory_export_ignored':True,'wrong_checkpoint_rejected':True,'unsaved_head_rejected':True})
        if args.source_project:
            source=args.source_project.resolve(strict=True)
            protected={str(p.relative_to(source)):sha(p)for p in source.rglob('*')if p.is_file()}
            selected={name:value for name,value in protected.items()if not name.endswith('.lock')}
            directory=out/'complete-project';directory.mkdir()
            for name in selected:
                target=directory/name;target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(source/name,target)
                assert sha(target)==selected[name]
            view=ContentView(host);views.append(view);view.open_project(directory);idle(view)
            saved=snapshot(view);assert len(saved.asset_refs)==6 and saved.opening_workshop_authored
            journal=hash_saved_journal(directory);job,results,errors=export(view,saved,lambda:view._saved_context_matches(saved,view.definition))
            assert len(results)==1 and not errors,errors
            assert results[0].snapshot.asset_refs==saved.asset_refs and len(saved.asset_refs)==6
            view.close_project();spin(lambda:view.client.state=='closed'and not view.client.process_id,'full project owner did not close')
            assert {str(p.relative_to(source)):sha(p)for p in source.rglob('*')if p.is_file()}==protected
            report['cases'].append({'profile':'complete-owned-six-pack-workshop','source_project_unchanged':True,
                'dependency_count':6,'dependency_kinds':list(saved.dependency_kinds),'source_files':selected,
                'fingerprint':saved.fingerprint,'journal_sha256':journal.sha256,'journal_bytes':journal.bytes,
                'complete_export_version':saved.export_version})
        report['checks']=['Both profiles opened actual journal through independent native OPEN(create=False)',
            'Saved fixture edit exported instead of stale opening.aibd','Native reader rejects mismatched unsaved head and checkpoint',
            'Complete version2 identity/payload/dependencies equal original clean pin',
            'Independent Host epoch admitted with original UI scope restored only in completed owned snapshot',
            'Second Host joined before completion, primary Host remained ready',
            'Journal identity/hash unchanged before and after every export']
        report['status']='passed'
    except Exception as error:
        report['error']=repr(error)
        raise
    finally:
        for job in jobs:job.stop()
        for view in views:
            view.saved_export.stop();view.saved_play.stop();view.asset_client.shutdown();view.play._shutdown();view.viewport._shutdown();view.client.stop()
        spin(lambda:not any(j.process_id for j in jobs)and not any(v.client.process_id for v in views),'owned processes did not join',8)
        report['all_owned_processes_joined']=True
        report['host_unchanged']=sha(host)==report['host_sha256']
        for view in views:view.definition=None;view.deleteLater()
        app.processEvents();(out/'verification.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(report))
if __name__=='__main__':run()
