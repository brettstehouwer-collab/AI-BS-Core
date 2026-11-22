"""Owned saved-player protocol, cancellation and join semantics without a GPU."""
import os
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
from pathlib import Path
import json
import tempfile
import time
import unittest
from unittest.mock import patch
from PyQt6.QtCore import QObject,QProcess,QCoreApplication,pyqtSignal
from native_studio.game_engine import saved_play as mod
from test_saved_play_storage import snapshot

APP=QCoreApplication.instance() or QCoreApplication([])
REAL_PROCESS=QProcess


class Process(QObject):
    readyReadStandardOutput=pyqtSignal();readyReadStandardError=pyqtSignal()
    finished=pyqtSignal(int,object);errorOccurred=pyqtSignal(object)
    ProcessChannel=REAL_PROCESS.ProcessChannel;ProcessChannelMode=REAL_PROCESS.ProcessChannelMode
    ExitStatus=REAL_PROCESS.ExitStatus;ProcessError=REAL_PROCESS.ProcessError
    def __init__(self,parent):
        super().__init__(parent);self.channel=self.ProcessChannel.StandardOutput
        self.out=bytearray();self.err=bytearray();self.live=False;self.killed=False;self.args=None
    def setWorkingDirectory(self,path):self.directory=path
    def setProcessChannelMode(self,mode):pass
    def setReadChannel(self,channel):self.channel=channel
    def processId(self):return 101 if self.live else 0
    def bytesAvailable(self):return len(self.err if self.channel==self.ProcessChannel.StandardError else self.out)
    def read(self,n):
        source=self.err if self.channel==self.ProcessChannel.StandardError else self.out
        value=bytes(source[:n]);del source[:n];return value
    def start(self,exe,args):self.exe=exe;self.args=args;self.live=True
    def send(self,raw):self.out.extend(raw);self.readyReadStandardOutput.emit()
    def kill(self):self.killed=True  # Exit remains explicit: kill request is not a join.
    def exit(self,code=0,status=REAL_PROCESS.ExitStatus.NormalExit):
        self.live=False;self.finished.emit(code,status)
    def waitForFinished(self,timeout):return not self.live
    def errorString(self):return 'fake failed start'


class Stager(QObject):
    receipt=pyqtSignal(str,object);failed=pyqtSignal(str);closed=pyqtSignal()
    def __init__(self,*args):super().__init__();self.busy=False;self.process_id=0
    def stage_store(self,*args,**kwargs):self.busy=True;self.process_id=202
    def stop(self):self.cancelled=True
    def shutdown(self):self.stop()
    def join(self):self.busy=False;self.process_id=0;self.closed.emit()


class SavedClientTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(prefix='aibs-saved-client-')
        self.root=Path(self.temp.name);self.exe=self.root/'player.exe';self.exe.write_bytes(b'never executed')
        self.snap=snapshot()
        features={x:True for x in ('chapter-saved-play-v1','durable_world','first_boot_chapter',
            'first_boot_content_play','chapter_content_export_v2','chapter_content_v3','chapter_asset_surfaces')}
        (self.root/'aibs_capabilities.json').write_text(json.dumps({'schema_version':1,'sdk_version':'0.16.0','target':'windows-x64','features':features}))
        self.process_patch=patch.object(mod,'QProcess',Process);self.process_patch.start()
        self.stager_patch=patch.object(mod,'ProjectAssetClient',Stager);self.stager_patch.start()
        self.client=mod.SavedChapterPlayClient(start_timeout_ms=1000,stop_timeout_ms=1000)
        self.closed=[];self.client.closed.connect(lambda:self.closed.append(True))
    def tearDown(self):
        if self.client._stager.busy:self.client._stager.join()
        if self.client._process is not None:self.client._process.exit(1,REAL_PROCESS.ExitStatus.CrashExit)
        self.client.stop();self.client.deleteLater();APP.processEvents()
        self.process_patch.stop();self.stager_patch.stop();self.temp.cleanup()
    def spin(self,predicate):
        deadline=time.monotonic()+2
        while not predicate() and time.monotonic()<deadline:APP.processEvents();time.sleep(.001)
        self.assertTrue(predicate())
    def start(self,**kwargs):
        self.client.start(self.exe,self.snap,self.root,**kwargs)
        self.spin(lambda:self.client._process is not None)
        return self.client._process
    def event(self,name='ready',revision=4,sequence=7,**changes):
        c=self.client
        value={'event':'aibs.saved_play.'+name,'schema_version':1,'play_session':c.session_id,
            'project_id':self.snap.scope.project,'branch_id':self.snap.scope.branch,'world_id':self.snap.scope.world_id,
            'timeline_id':c.publication.timeline_id,'context':'player_world','content_fingerprint':self.snap.fingerprint,
            'saved':True,'durable_revision':revision,'durable_sequence':sequence}
        value.update(changes);return value
    def send(self,p,value):p.send(json.dumps(value).encode()+b'\n')

    def test_launch_uses_persistent_scope_and_unique_stop_marker_and_retained_database(self):
        p=self.start();args=p.args
        self.assertIn('--persistent-play',args)
        self.assertEqual(args[args.index('--timeline-id')+1],self.client.publication.timeline_id)
        self.assertEqual(Path(args[args.index('--database')+1]),self.client.publication.database_path)
        marker=Path(args[args.index('--stop-file')+1])
        self.assertEqual(marker.name,'stop.'+self.client.session_id+'.request')
        self.assertEqual(marker.parent,self.client.workspace_path)
        self.assertNotIn('temporary',str(self.client.workspace_path))

    def test_stopped_receipt_is_not_process_exit_or_a_saved_result(self):
        p=self.start();self.send(p,self.event());self.client.publication.database_path.write_bytes(b'committed state')
        self.client.stop();self.send(p,self.event('stopped',5,9))
        self.assertTrue(p.live);self.assertEqual(self.client.state,'stopping')
        self.assertEqual(self.closed,[]);self.assertIsNone(self.client.last_result)
        self.assertTrue(self.client._stop_file.exists())
        p.exit()
        self.assertEqual(self.client.state,'closed');self.assertEqual(self.closed,[True])
        self.assertTrue(self.client.last_result['graceful'] and self.client.last_result['saved'])
        self.assertEqual(self.client.last_result['durable_sequence'],9)
        self.assertEqual(self.client.publication.database_path.read_bytes(),b'committed state')
        self.assertFalse(self.client._stop_file.exists())

    def test_resume_uses_new_invocation_and_same_timeline_without_reset(self):
        p=self.start();self.send(p,self.event());first=(self.client.session_id,self.client.publication.timeline_id)
        db=self.client.publication.database_path;db.write_bytes(b'old progress')
        self.client.stop();self.send(p,self.event('stopped'));p.exit()
        p=self.start();self.send(p,self.event())
        self.assertNotEqual(self.client.session_id,first[0]);self.assertEqual(self.client.publication.timeline_id,first[1])
        self.assertEqual(db.read_bytes(),b'old progress')

    def test_forced_exit_preserves_database_wal_claim_and_never_reports_saved(self):
        p=self.start();self.send(p,self.event());slot=self.client.workspace_path
        files={'world.sqlite':b'db','world.sqlite-wal':b'wal','world.sqlite.initialized':b'claim'}
        for name,data in files.items():(slot/name).write_bytes(data)
        self.client._force('test timeout')
        self.assertTrue(p.killed);self.assertEqual(self.closed,[])
        p.exit(-1,REAL_PROCESS.ExitStatus.CrashExit)
        self.assertFalse(self.client.last_result['saved']);self.assertTrue(self.client.last_result['forced'])
        for name,data in files.items():self.assertEqual((slot/name).read_bytes(),data)

    def test_normal_exit_without_stop_receipt_is_unverified_and_keeps_slot(self):
        p=self.start();self.send(p,self.event());slot=self.client.workspace_path;p.exit()
        self.assertFalse(self.client.last_result['saved']);self.assertTrue((slot/'slot.json').exists())

    def test_wrong_identity_bad_types_duplicate_and_regressing_heads_reject_saved_claim(self):
        variations=[{'play_session':'foreign'},{'timeline_id':'foreign'},{'context':'temporary_play'},
            {'project_id':'foreign'},{'content_fingerprint':'0'*64},{'schema_version':True},
            {'saved':1},{'durable_revision':True},{'durable_sequence':-1},{'extra':True}]
        for change in variations:
            with self.subTest(change=change):
                p=self.start();self.send(p,self.event(**change));self.assertTrue(self.client._protocol_failed)
                p.exit();self.assertFalse(self.client.last_result['saved'])
        p=self.start();self.send(p,self.event());self.send(p,self.event())
        self.assertTrue(self.client._protocol_failed);p.exit()
        p=self.start();self.send(p,self.event());self.client.stop();self.send(p,self.event('stopped',3,6))
        self.assertTrue(self.client._protocol_failed);p.exit();self.assertFalse(self.client.last_result['saved'])

    def test_wrong_protocol_duplicate_json_nonfinite_overflow_and_unterminated_output_reject(self):
        values=[b'{"event":"aibs.play.ready"}\n',b'{"event":"aibs.saved_play.ready","saved":true,"saved":false}\n',
            b'{"x":NaN}\n',b'x'*16385,b'{"unfinished":']
        for raw in values:
            with self.subTest(length=len(raw)):
                p=self.start();self.send(p,self.event());p.send(raw);p.exit()
                self.assertFalse(self.client.last_result['saved'])

    def test_cancel_before_queued_staging_starts_never_launches_or_creates_slot(self):
        self.client.start(self.exe,self.snap,self.root);self.client.stop();APP.processEvents()
        self.assertEqual(self.client.state,'closed');self.assertIsNone(self.client._process)
        self.assertEqual(list((self.root/'.aibs-runtime/content').iterdir()),[])
        self.assertEqual(list((self.root/'.aibs-runtime/saves').iterdir()),[])

    def test_second_start_is_rejected_while_owned_process_alive(self):
        self.start()
        with self.assertRaisesRegex(RuntimeError,'Stop'):self.client.start(self.exe,self.snap,self.root)

    def test_stale_guard_prevents_writes_and_post_queue_change_prevents_launch(self):
        with self.assertRaisesRegex(ValueError,'changed'):
            self.client.start(self.exe,self.snap,self.root,context_valid=lambda:False)
        self.assertFalse((self.root/'.aibs-runtime').exists())
        valid=[True];self.client.start(self.exe,self.snap,self.root,context_valid=lambda:valid[0]);valid[0]=False
        self.spin(lambda:self.client.state=='closed')
        self.assertIsNone(self.client._process);self.assertFalse(self.client.last_result['saved'])

    def test_stop_during_native_dependency_stage_waits_for_stager_join_before_cleanup(self):
        from types import SimpleNamespace as NS
        from dataclasses import replace
        ref=NS(asset_id='a4dff95c-7a83-40b5-9fde-811826ba6d02',asset_sha256='a'*64,pack_sha256='b'*64)
        self.snap.asset_refs=(ref,);self.snap.dependency_kinds=(0,);self.snap.asset_store=self.root/'source'
        value=json.loads((self.root/'aibs_capabilities.json').read_text());value['features']['mesh_asset_v1']=True
        (self.root/'aibs_capabilities.json').write_text(json.dumps(value))
        self.client.start(self.exe,self.snap,self.root)
        self.spin(lambda:self.client._stager.busy);stage=self.client._preparation.staging
        self.client.stop();self.assertEqual(self.client.state,'stopping');self.assertTrue(stage.exists())
        self.assertEqual(self.closed,[]);self.client._stager.join()
        self.assertEqual(self.client.state,'closed');self.assertFalse(stage.exists())

    def test_shutdown_reports_unjoined_process_and_retains_ownership_until_real_exit(self):
        p=self.start();self.send(p,self.event())
        self.assertFalse(self.client.shutdown())
        self.assertTrue(p.killed and p.live)
        self.assertIs(self.client._process,p)
        self.assertEqual(self.closed,[])
        self.assertIsNone(self.client.last_result)
        p.exit(-1,REAL_PROCESS.ExitStatus.CrashExit)
        self.assertFalse(self.client.last_result['saved'])
        self.assertTrue(self.client.shutdown())

    def test_retained_publication_supplies_dependencies_when_original_store_is_offline(self):
        from test_saved_play_storage import synthetic_pack
        import shutil
        source=self.root/'source';source.mkdir()
        ref,pack=synthetic_pack(source)
        self.snap.asset_refs=(ref,);self.snap.dependency_kinds=(0,);self.snap.asset_store=source
        prep=mod.prepare_publication(self.root,self.snap)
        shutil.copytree(pack,prep.staging/'assets/packs'/ref.pack_sha256)
        retained=mod.finish_publication(prep)
        # The native stager still validates this closure on the real path; this
        # CPU contract verifies the correct owned source is selected for it.
        self.snap.asset_store=self.root/'unmounted-original-store'
        caps=self.root/'aibs_capabilities.json';value=json.loads(caps.read_text())
        value['features']['mesh_asset_v1']=True;caps.write_text(json.dumps(value))
        captured=[]
        original=self.client._stager.stage_store
        def record(*args,**kwargs):captured.append(args[0]);original(*args,**kwargs)
        self.client._stager.stage_store=record
        self.client.start(self.exe,self.snap,self.root)
        self.spin(lambda:bool(captured))
        self.assertEqual(captured,[retained.asset_root])
        self.client.stop();self.client._stager.join()
        self.assertEqual(self.client.state,'closed')
        self.assertTrue(retained.content_path.exists())


    def test_native_window_close_arms_join_deadline_without_claiming_process_exit(self):
        p=self.start();self.send(p,self.event())
        self.assertIsNone(self.client._deadline)
        self.send(p,self.event('stopped'))
        self.assertEqual(self.client.state,'stopping')
        self.assertGreater(self.client._deadline,time.monotonic())
        self.assertEqual(self.closed,[]);self.assertIsNone(self.client.last_result)
        self.client._deadline=0;self.client._tick()
        self.assertTrue(p.killed and p.live)
        self.assertEqual(self.closed,[])
        p.exit(-1,REAL_PROCESS.ExitStatus.CrashExit)
        self.assertFalse(self.client.last_result['saved'])



if __name__=='__main__':unittest.main()
