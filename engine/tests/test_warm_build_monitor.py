import os
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
import copy,json,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from native_studio.game_build_monitor import read_build_progress

def fixture():
    entry={'status':'passed','summary':'Recorded synthetic scope only.','evidence_paths':['engine/out/warm_beginning/proof.json']}
    return {'schema_version':1,'updated_at':'2026-11-02T12:00:00+00:00','goal_complete':False,
        'native_source':{'sdk_version':'0.14.0',**entry},
        'packaged_candidate':{'studio_version':'5.329.99',**entry},
        'deployed':{'studio_version':'5.329.98',**entry},
        'remaining':[{'id':key,'title':title,'status':'needs_review','detail':'Pending human or final package acceptance.'}
            for key,title in [('likeness','Naturalistic likeness'),('checked_captions','Checked captions'),
                              ('human_pacing','Human 8–12 minute pacing'),('final_package','Final package')]],
        'next_step':'Review the remaining work before declaring the full goal complete.'}

class WarmMonitorTests(unittest.TestCase):
    def setUp(self):
        self.directory=tempfile.TemporaryDirectory();self.addCleanup(self.directory.cleanup)
        self.root=Path(self.directory.name);self.path=self.root/'engine/out/warm_beginning/monitor_summary.json'
        self.path.parent.mkdir(parents=True)
    def write(self,data):self.path.write_text(json.dumps(data,ensure_ascii=False),encoding='utf-8')
    def read(self):return read_build_progress(self.root)['warm_beginning_summary']
    def test_missing_summary_never_claims_pass_or_completion(self):
        result=self.read();self.assertEqual(result['status'],'not_run');self.assertFalse(result['goal_complete'])
    def test_valid_recorded_native_candidate_and_deployed_are_distinct(self):
        self.write(fixture());r=self.read();self.assertEqual(r['status'],'available')
        self.assertEqual(r['native_source']['sdk_version'],'0.14.0');self.assertEqual(r['packaged_candidate']['studio_version'],'5.329.99')
        self.assertEqual(r['deployed']['studio_version'],'5.329.98');self.assertFalse(r['goal_complete'])
    def test_all_subsystem_passes_do_not_complete_goal(self):
        value=fixture()
        for item in value['remaining']:item['status']='completed'
        self.write(value);self.assertFalse(self.read()['goal_complete'])
    def test_failed_evidence_is_shown_without_pass_reinterpretation(self):
        value=fixture();value['native_source']['status']='failed';self.write(value)
        r=self.read();self.assertEqual(r['native_source']['status'],'failed');self.assertFalse(r['goal_complete'])
    def test_unknown_statuses_and_bool_schema_or_goal_are_rejected(self):
        values=[]
        for key in ['native_source','packaged_candidate','deployed']:
            v=fixture();v[key]['status']='verified';values.append(v)
        v=fixture();v['remaining'][0]['status']='approved';values.append(v)
        for key,value in [('schema_version',True),('goal_complete',1),('updated_at','not a date')]:
            v=fixture();v[key]=value;values.append(v)
        for value in values:
            with self.subTest(value=value):self.write(value);r=self.read();self.assertEqual(r['status'],'unreadable');self.assertFalse(r['goal_complete'])
    def test_complete_claim_requires_explicit_true_and_consistent_remaining(self):
        value=fixture();value['goal_complete']=True;self.write(value);self.assertEqual(self.read()['status'],'unreadable')
        for item in value['remaining']:item['status']='completed'
        self.write(value);self.assertTrue(self.read()['goal_complete'])
        value['packaged_candidate']['status']='failed';self.write(value);self.assertEqual(self.read()['status'],'unreadable')
    def test_unknown_missing_duplicate_or_partial_fields_rejected(self):
        variants=[]
        v=fixture();v['secret']='extra';variants.append(v)
        v=fixture();del v['native_source']['evidence_paths'];variants.append(v)
        v=fixture();v['native_source']['extra']='unexpected';variants.append(v)
        v=fixture();v['remaining']=v['remaining'][:-1];variants.append(v)
        v=fixture();v['remaining'].append(copy.deepcopy(v['remaining'][0]));variants.append(v)
        for value in variants:
            with self.subTest(value=value):self.write(value);self.assertEqual(self.read()['status'],'unreadable')
        self.path.write_text(json.dumps(fixture())[:-1]+',"goal_complete":true}',encoding='utf-8')
        self.assertEqual(self.read()['status'],'unreadable')
    def test_invalid_utf8_nonfinite_and_overlarge_summary_are_rejected(self):
        for raw in (b'\xff',b'{"schema_version":NaN}',b' '* (1024*1024+1)):
            with self.subTest(size=len(raw)):self.path.write_bytes(raw);self.assertEqual(self.read()['status'],'unreadable')
    def test_nonempty_bounded_strictly_typed_fields(self):
        variants=[]
        for field,value in [('summary',' '),('summary','\0bad'),('summary','x'*4097),('evidence_paths','one'),('evidence_paths',[]),('evidence_paths',[123])]:
            v=fixture();v['native_source'][field]=value;variants.append(v)
        v=fixture();v['packaged_candidate']['studio_version']='latest';variants.append(v)
        v=fixture();v['remaining'][0]['detail']=False;variants.append(v)
        v=fixture();v['remaining'][0]['id']='../likeness';variants.append(v)
        for value in variants:
            with self.subTest(value=value):self.write(value);self.assertEqual(self.read()['status'],'unreadable')
    def test_log_decodes_utf16le_and_be_with_nonascii(self):
        log=self.root/'engine/out/verification.log'
        expected='Adam — mémoire 你好 🎮\nPASS finished\n'
        for codec,bom in [('utf-16-le',b'\xff\xfe'),('utf-16-be',b'\xfe\xff'),('utf-8',b'\xef\xbb\xbf')]:
            with self.subTest(codec=codec):
                log.write_bytes(bom+expected.encode(codec));self.assertEqual(read_build_progress(self.root)['log'],expected)
    def test_log_tail_has_safe_utf8_and_utf16_character_boundaries(self):
        log=self.root/'engine/out/verification.log'
        for codec,bom in [('utf-16-le',b'\xff\xfe'),('utf-16-be',b'\xfe\xff'),('utf-8',b'')]:
            for padding in range(4):
                with self.subTest(codec=codec,padding=padding):
                    text='prefix\n'+('🎮é漢'*9000)+('x'*padding)+'\nPASS dernière ligne\n'
                    log.write_bytes(bom+text.encode(codec));tail=read_build_progress(self.root)['log']
                    self.assertTrue(tail.endswith('PASS dernière ligne\n'));self.assertTrue('\ufffd'not in tail,'Split character at tail boundary');self.assertTrue('\0'not in tail,'UTF16 decoded as UTF8')
                    self.assertLessEqual(len(tail.encode(codec)),32768)
    def test_log_tail_handles_incomplete_live_utf8_and_utf16_write(self):
        log=self.root/'engine/out/verification.log'
        for raw in [b'PASS stable\n\xf0\x9f',b'\xff\xfe'+('PASS stable\n').encode('utf-16-le')+b'\x3d\xd8',
                    b'\xfe\xff'+('PASS stable\n').encode('utf-16-be')+b'\xd8\x3d']:
            with self.subTest(raw=raw):log.write_bytes(raw);self.assertEqual(read_build_progress(self.root)['log'],'PASS stable\n')

class WarmMonitorQtTests(unittest.TestCase):
    write=WarmMonitorTests.write
    def setUp(self):
        WarmMonitorTests.setUp(self)
        from PyQt6.QtWidgets import QApplication
        from PyQt6.QtGui import QFont,QFontDatabase
        from native_studio.theme import STYLESHEET
        self.app=QApplication.instance()or QApplication([])
        font=Path('C:/Windows/Fonts/segoeui.ttf')
        if font.is_file():
            QFontDatabase.addApplicationFont(str(font));self.app.setFont(QFont('Segoe UI',10))
        self.app.setStyleSheet(STYLESHEET)
    def test_unreadable_or_failed_refresh_clears_near_top_positive_summary(self):
        from native_studio.engine import EngineBus
        from native_studio.game_build_view import GameBuildNativeView
        bus=EngineBus(max_threads=1);view=GameBuildNativeView(bus,root=self.root)
        try:
            self.write(fixture());view._render(read_build_progress(self.root))
            self.assertIn('SDK 0.14.0 | passed',view.warm_summary.text())
            self.path.write_text('{malformed',encoding='utf-8')
            view._render(read_build_progress(self.root))
            self.assertIn('unreadable',view.warm_summary.text());self.assertNotIn('| passed',view.warm_summary.text())
            self.assertIn('Goal complete: no',view.details.toPlainText())
            self.write(fixture());view._render(read_build_progress(self.root));view._error('Synthetic failed refresh')
            self.assertIn('unavailable',view.warm_summary.text());self.assertNotIn('| passed',view.warm_summary.text())
        finally:view.close();bus.shutdown();self.app.processEvents()
    def test_current_and_failed_summary_render_on_actual_read_only_Qt_widget(self):
        from PyQt6.QtGui import QImage
        from native_studio.engine import EngineBus
        from native_studio.game_build_view import GameBuildNativeView
        bus=EngineBus(max_threads=1);view=GameBuildNativeView(bus,root=self.root)
        try:
            view.resize(1280,1000);view.ensurePolished()
            for state in ['passed','failed']:
                value=fixture();value['packaged_candidate']['status']=state;self.write(value)
                view._render(read_build_progress(self.root));text=view.details.toPlainText()
                self.assertTrue(text.startswith('WARM BEGINNING'))
                for label in ['SDK 0.14.0','Packaged candidate: Studio 5.329.99','Deployed launcher: Studio 5.329.98',
                              'Naturalistic likeness','Checked captions','Human 8–12 minute pacing','Final package','Goal complete: no',
                              'HISTORICAL RECORDED EVIDENCE']:
                    self.assertIn(label,text)
                self.assertIn(f'Packaged candidate: Studio 5.329.99 | {state}',text)
                self.assertIn('WARM BEGINNING',view.warm_summary.text());self.assertIn('Goal complete: no',view.warm_summary.text())
                self.assertTrue(view.details.isReadOnly())
                image=QImage(view.size(),QImage.Format.Format_ARGB32);image.fill(0);view.render(image)
                self.assertFalse(image.isNull())
                if os.environ.get('AIBS_WARM_MONITOR_EVIDENCE'):
                    self.assertTrue(image.save(str(Path(os.environ['AIBS_WARM_MONITOR_EVIDENCE'])/f'qt-monitor-{state}.png')))
        finally:view.close();bus.shutdown();self.app.processEvents()

if __name__=='__main__':unittest.main()
