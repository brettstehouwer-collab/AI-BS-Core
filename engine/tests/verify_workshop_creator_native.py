"""Actual offscreen Creator/Host authoring proof; never starts a renderer."""
import argparse
import datetime
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time
from unittest.mock import patch

os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
sys.dont_write_bytecode=True
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))
from PyQt6.QtWidgets import QApplication
from native_studio.game_engine.content_view import ContentView,ChapterProjectDefinition
from native_studio.game_engine.content_commands import SetField,decode_scoped_edit,CreateFixture
from native_studio.game_engine.creator_payload import _Reader
from native_studio.game_engine.workshop_fields import workshop_bindings_from_rows,workshop_default_centers

def digest(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def inventory(root):return {p.relative_to(root).as_posix():{'bytes':p.stat().st_size,'sha256':digest(p)}for p in sorted(root.rglob('*'))if p.is_file()}

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--build',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args();build=args.build.resolve(strict=True);work=args.output.absolute()
    if work.exists():raise RuntimeError('Preserve previous proof outputs; use a fresh directory')
    work.resolve().relative_to(Path('D:/AI-BS-Game-Resources').resolve())
    work.mkdir(parents=True);tools=work/'Tools';tools.mkdir();temp=work/'Temp';temp.mkdir()
    environment=os.environ.copy();environment.update(TEMP=str(temp),TMP=str(temp),QT_QPA_PLATFORM='offscreen',PYTHONDONTWRITEBYTECODE='1')
    os.environ.update(TEMP=str(temp),TMP=str(temp));__import__('tempfile').tempdir=str(temp)
    copied=[]
    for source,name in ((build/'Release/aibs_content_host.exe','aibs_content_host.exe'),
                        (build/'Release/aibs_warm_opening_project.exe','aibs_warm_opening_project.exe'),
                        (build/'aibs_capabilities.json','aibs_capabilities.json')):
        before=digest(source);shutil.copyfile(source,tools/name)
        if digest(source)!=before or digest(tools/name)!=before:raise RuntimeError('Fresh native tool changed during exact copy')
        copied.append({'source':str(source),'staged':str(tools/name),'sha256':before})
    project=work/'LegacyWarmProject'
    command=[str(tools/'aibs_warm_opening_project.exe'),'--output',str(project)]
    process=subprocess.run(command,env=environment,stdin=subprocess.DEVNULL,capture_output=True,timeout=60,creationflags=subprocess.CREATE_NO_WINDOW)
    (work/'factory.stdout.log').write_bytes(process.stdout);(work/'factory.stderr.log').write_bytes(process.stderr)
    if process.returncode:raise RuntimeError('Actual legacy factory failed; inspect preserved stderr')
    legacy_meta=(project/'.aibs-chapter-project.json').read_bytes()
    if json.loads(legacy_meta)['version']!=2:raise RuntimeError('No-flag factory unexpectedly opted in')
    app=QApplication.instance()or QApplication([]);view=ContentView(tools/'aibs_content_host.exe')
    messages=[];responses=[];owners=[];checks=[];error=None;status='failed'
    original_status=view.status.setText
    def record_status(value):messages.append(str(value));original_status(value)
    view.status.setText=record_status
    view.client.response.connect(lambda identity,reply:responses.append({'request':identity,'status':int(reply.status),'revision':reply.head_revision,'message':reply.message}))
    def check(value,label):
        checks.append({'check':label,'passed':bool(value)})
        if not value:raise RuntimeError(label)
    def spin(predicate,label,seconds=45):
        deadline=time.monotonic()+seconds
        while not predicate()and time.monotonic()<deadline:app.processEvents();time.sleep(.002)
        check(predicate(),label+'; '+view.status.text())
    def idle():spin(lambda:view.loaded and not view.busy and view.client.pending_count==0,'native owner idle')
    try:
        # These guards reject any accidental view launch; actual Host remains real.
        with patch.object(view.viewport,'start_content',side_effect=RuntimeError('Renderer launch prohibited'))as viewport_launch,patch.object(view.play,'start',side_effect=RuntimeError('Player launch prohibited'))as player_launch:
            view.open_project(project);idle();owners.append({'generation':view.client.generation,'pid':view.client.process_id,'epoch':view.client.epoch.hex()})
            initial=view.description.fingerprint
            expected=workshop_default_centers(view.rows)
            check(not workshop_bindings_from_rows(view.rows,'warm-beginning'),'legacy no-flag project starts without Workshop')
            view.preview_workshop_create();spin(lambda:not view.busy and view.client.pending_count==0,'grouped native Preview returned')
            check(bool(view._token),'actual native Preview accepts factory-relative five-fixture group')
            check(view.description.fingerprint==initial,'Preview leaves published fingerprint unchanged')
            # Decode the real prepared request retained by the managed client.
            original=view.client._prepared[view._token]
            reader=_Reader(original);reader.number('H');[reader.text()for _ in range(4)]
            packet=reader.read(reader.number('I'));created=tuple(e for e in decode_scoped_edit(packet).edits if isinstance(e,CreateFixture))
            check(len(created)==5,'actual prepared group contains five exact17-field creates')
            check(tuple(e.center for e in created)==expected,'prepared coordinates derive from current native anchors')
            check(all(abs(v-.16)<1e-6 for e in created for v in e.half_extent),'native prepared proxies use .16m half extents')
            check(all(abs(e.emission-.02)<1e-6 for e in created),'native prepared emission uses .02')
            view.apply_preview();idle();applied=view.description.fingerprint
            binding=workshop_bindings_from_rows(view.rows,'warm-beginning')
            check(binding==tuple(e.uuid for e in created),'Apply preserves exact closed five-action ownership')
            check(all(len(row.fields)==21 for row in view.rows if row.uuid in binding),'actual native Workshop observations have21fields')
            view._travel(False);idle()
            check(view.description.fingerprint==initial and not workshop_bindings_from_rows(view.rows,'warm-beginning'),'Undo restores exact legacy content and removes current requirement')
            view._travel(True);idle()
            check(view.description.fingerprint==applied and workshop_bindings_from_rows(view.rows,'warm-beginning')==binding,'Redo restores exact placement and binding fingerprint')
            view.save_world();idle()
            check(ChapterProjectDefinition.load(project).opening_workshop,'Save writes sticky typed-v3 Workshop history declaration')
            saved_journal=digest(project/'chapter.aiba');generation=view.client.generation
            view.close_project();spin(lambda:view.client.state=='closed','first native Host joined')
            stderr_first=view.client.stderr_tail
            view.open_project(project);idle();owners.append({'generation':view.client.generation,'pid':view.client.process_id,'epoch':view.client.epoch.hex()})
            check(view.client.generation>generation,'restart uses a new native owner generation')
            check(view.description.fingerprint==applied and workshop_bindings_from_rows(view.rows,'warm-beginning')==binding,'fresh native owner restores identical placement and binding fingerprint')
            # A structurally valid relocation into the wrong region must be
            # rejected by native route checks, rather than assumed safe by Python.
            probe=created[0].center;bench=binding[4]
            packet=view._encode_edits((SetField(bench,'x',probe[0]),SetField(bench,'z',probe[2])),'Invalid bench region proof')
            view._submit_packet(packet,apply_after_preview=False);spin(lambda:not view.busy and view.client.pending_count==0,'invalid region Preview returned')
            check(view._token is None and view.description.fingerprint==applied,'native Preview rejects a bench moved into Jenison without publication')
            check(digest(project/'chapter.aiba')==saved_journal,'rejected replacement preserves exact saved journal bytes')
            check(any(r['status']==100 for r in responses),'actual native rejection response is recorded')
            viewport_launch.assert_not_called();player_launch.assert_not_called()
            view.close_project();spin(lambda:view.client.state=='closed','second native Host joined')
            (work/'owner-first.stderr.log').write_text(stderr_first,encoding='utf-8')
            (work/'owner-second.stderr.log').write_text(view.client.stderr_tail,encoding='utf-8')
            check(view.client.process_id==0 and view.play.process_id==0 and view.viewport.process_id==0,'all native process handles terminal; no renderer/Player process')
            observations={'initial_fingerprint':initial,'applied_and_reopened_fingerprint':applied,'binding':binding,'centers':expected,
                'saved_journal_sha256':saved_journal,'metadata':json.loads((project/'.aibs-chapter-project.json').read_bytes()),'owners':owners}
            status='passed_actual_offscreen_creator_workshop_placement'
    except Exception as exc:error=str(exc);observations={'owners':owners}
    finally:
        if view.client.state!='closed':
            view.client.stop();deadline=time.monotonic()+10
            while view.client.state!='closed'and time.monotonic()<deadline:app.processEvents();time.sleep(.002)
        terminal=view.client.process_id==0
        if not terminal:status='failed_owner_not_joined';error='Native Host failed to join'
        (work/'status-messages.json').write_text(json.dumps(messages,indent=2)+'\n')
        (work/'response-statuses.json').write_text(json.dumps(responses,indent=2)+'\n')
        receipt={'status':status,'error':error,'utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'goal_complete':False,
            'checks':checks,'checks_passed':sum(c['passed']for c in checks),'actual_factory_command':command,'actual_tools':copied,
            'tool_stage_exact_before_after':all(digest(Path(row['staged']))==row['sha256']for row in copied),
            'observations':observations,'project_files':inventory(project),'native_owner_terminal':terminal,
            'GPU_Player_Viewport_window_focus_audio_inference_used':False,'QApplication_mode':'offscreen, widget never shown'}
        (work/'verification.json').write_text(json.dumps(receipt,indent=2)+'\n')
        view.definition=None;view.busy=False;view.close();view.deleteLater();app.processEvents()
        print(json.dumps({'status':status,'error':error,'checks':receipt['checks_passed'],'receipt':str(work/'verification.json'),'sha256':digest(work/'verification.json')}))
    return 0 if status=='passed_actual_offscreen_creator_workshop_placement'else 1

if __name__=='__main__':raise SystemExit(main())
