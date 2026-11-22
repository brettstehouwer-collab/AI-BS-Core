import copy,os,time,unittest
from types import SimpleNamespace
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
from PyQt6.QtWidgets import QApplication
from native_studio.chat_recovery import RecoveryLoad
from native_studio.executive_cockpit_full import ExecutiveCockpitFullView


def snapshot():
    ok=lambda data:{'ok':True,'data':data}
    return {'observedAt':time.time(),'observedMonotonic':time.monotonic(),
        'ports':{p:{'listening':p in {8080,8000,5173,11434},'onDemand':p==8888}for p in [8080,8000,5173,8188,8189,4455,8888,8007,11434,11435,8002,8013]},
        'sections':{'backend':ok({'status':'healthy'}),'autonomy':ok({'autonomy_mode':'SAFE'}),
        'pending':ok({'pending_actions':[{'action_id':'fixture-id','pillar':'fixture','action':'inspect','status':'PENDING'}]}),
        'history':ok({'history':[]}),'sentinel':ok({'alerts':[],'engine_status':{'running':False}}),
        'cloud':ok({'gpu_sovereignty':{'current_daily_spend_usd':0,'cloud_burst_enabled':False,'sovereign_local_exclusive':True}}),
        'installed_models':ok({'models':[{'name':'fixture-model'}]}),'loaded_models':ok({'models':[]}),
        'hardware':ok({'gpu':{'detected':True,'temp_c':31,'vram_used_gb':1.2,'vram_total_gb':24,'fan_pct':0},
                       'system':{'cpu_pct':0,'ram_total_gb':64,'ram_used_gb':20,'ram_pct':31.25}})}}


class Bus:
    def __init__(self):self.jobs=[]
    def submit(self,fn,*args,on_result=None,on_error=None):self.jobs.append((fn,args,on_result,on_error))
    def complete(self):
        fn,args,done,fail=self.jobs.pop(0)
        try:result=fn(*args)
        except Exception as e:
            if fail:fail(str(e))
        else:
            if done:done(result)
    def drain(self):
        for _ in range(15):
            if not self.jobs:return
            self.complete()
        raise AssertionError('Unbounded worker submission')


class Store:
    def __init__(self):self.state=None;self.saved=[]
    def load(self):return RecoveryLoad(copy.deepcopy(self.state))
    def save(self,state):self.state=copy.deepcopy(state);self.saved.append(self.state);return SimpleNamespace(checksum='fixture')


class Service:
    def __init__(self):self.data=snapshot();self.calls=[];self.fail=False
    def snapshot(self):self.calls.append(('read',));return copy.deepcopy(self.data)
    def set_autonomy(self,mode):
        self.calls.append(('mode',mode))
        if self.fail:raise RuntimeError('private-fixture-error')
        self.data['sections']['autonomy']['data']['autonomy_mode']=mode
        return {'status':'success','autonomy_mode':mode}
    def chat(self,prompt,model):
        self.calls.append(('chat',prompt,model))
        if self.fail:raise RuntimeError('private-fixture-error')
        return {'status':'success','response':'actual fixture reply','tool_calls':[]}
    def halt(self):self.calls.append(('halt',));return {'status':'HALTED','autonomy_mode':'SAFE','revoked_count':1}


class ExecutiveViewTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.app=QApplication.instance()or QApplication([])
    def setUp(self):
        self.bus=Bus();self.service=Service();self.store=Store()
        self.view=ExecutiveCockpitFullView(self.bus,service=self.service,session_store=self.store)
        self.addCleanup(self.view.shutdown)
        self.addCleanup(self.view.deleteLater)
    def ready(self):self.bus.drain()

    def test_observed_data_replaces_fake_status_and_preserves_zero_values(self):
        self.assertNotIn('GREEN',self.view.matrix_status.text())
        self.assertEqual(self.view._autonomy_mode,None)
        self.ready()
        self.assertEqual(self.view._autonomy_mode,'SAFE')
        self.assertEqual(self.view.table_queue.rowCount(),1)
        self.assertIn('0%',self.view.metric_gpu.sub_lbl.text())
        self.assertEqual(self.view.metric_cpu.val_lbl.text(),'0.0%')
        self.assertIn('On demand',self.view.pillar_labels['broadcast'].text())
        self.assertIn('Loaded: 0',self.view.pillar_labels['ollama'].text())
        self.assertTrue(all(c[0]=='read'for c in self.service.calls))

    def test_failed_queue_and_expired_observation_never_look_clear_or_fresh(self):
        self.ready();self.service.data['sections']['pending']={'ok':False,'error':'Unavailable'}
        self.view.refresh();self.bus.drain()
        self.assertEqual(self.view.table_queue.rowCount(),1)
        self.assertIn('unavailable',self.view.queue_status_lbl.text().lower())
        self.view._mark_stale(now=self.view._observed_at+16)
        self.assertIn('stale',self.view.matrix_status.text().lower())
        self.assertFalse(self.view.btn_full.isEnabled())
        self.assertEqual(self.view._model_ids,set())

    def test_mode_changes_wait_for_service_ack_and_stale_refresh_cannot_undo_ack(self):
        self.ready();self.view._set_autonomy('SEMI_AUTO')
        self.assertEqual(self.view._autonomy_mode,'SAFE')
        self.assertFalse(self.view.btn_semi.isChecked())
        self.bus.drain();self.assertEqual(self.view._autonomy_mode,'SEMI_AUTO')
        self.service.fail=True;self.view._set_autonomy('FULL_AUTO');self.bus.drain()
        self.assertEqual(self.view._autonomy_mode,'SEMI_AUTO')
        self.assertNotIn('private-fixture-error',self.view.audit_log.toPlainText())

    def test_chat_failure_keeps_draft_and_never_retries_ambiguous_request(self):
        self.ready();self.service.fail=True;self.view.input_edit.setText('fixture unsent request')
        self.view._send_prompt(self.view.input_edit.text());self.view._send_prompt('second ignored')
        self.assertEqual(self.view.input_edit.text(),'fixture unsent request')
        self.bus.drain()
        self.assertEqual(len([c for c in self.service.calls if c[0]=='chat']),1)
        self.assertEqual(self.view.input_edit.text(),'fixture unsent request')
        self.assertNotIn('private-fixture-error',self.view.chat_display.toPlainText())

    def test_delayed_old_snapshot_cannot_undo_an_acknowledged_mode_change(self):
        self.ready();self.view.refresh()
        fn,args,done,fail=self.bus.jobs.pop(0);older=fn(*args)
        self.view._set_autonomy('SEMI_AUTO');self.bus.complete()
        self.assertEqual(self.view._autonomy_mode,'SEMI_AUTO')
        done(older)
        self.assertEqual(self.view._autonomy_mode,'SEMI_AUTO')
        self.bus.drain();self.assertEqual(self.view._autonomy_mode,'SEMI_AUTO')

    def test_cockpit_recovery_hook_is_data_only_and_flushes_current_draft(self):
        self.store.state={'transcript':'stored /ps fixture-command','draft':'prior unsent','scratchpad':'',
                          'history':[['prior','reply']],'model':'fixture-model'}
        self.ready()
        self.assertEqual(self.view.input_edit.text(),'prior unsent')
        self.assertIn('stored /ps fixture-command',self.view.chat_display.toPlainText())
        self.assertFalse([c for c in self.service.calls if c[0]!='read'])
        self.view.input_edit.setText('final current draft')
        self.assertTrue(self.view._chat_recovery.flush_for_close())
        self.assertEqual(self.store.state['draft'],'final current draft')

    def test_real_action_schema_labels_queue_and_history(self):
        self.service.data['sections']['pending']['data']['pending_actions'][0].pop('action')
        self.service.data['sections']['pending']['data']['pending_actions'][0]['action_name']='fixture_inspection'
        self.service.data['sections']['history']['data']['history']=[{'action_name':'fixture_completed','status':'EXECUTED'}]
        self.ready()
        self.assertEqual(self.view.table_queue.item(0,2).text(),'fixture_inspection')
        self.assertIn('fixture_completed | EXECUTED',self.view.audit_log.toPlainText())

    def test_measured_and_unavailable_hardware_captions_agree_with_values(self):
        self.ready()
        self.assertIn('Measured',self.view.metric_ram.sub_lbl.text())
        self.service.data['sections']['hardware']={'ok':False,'error':'Unavailable'}
        self.view.refresh();self.bus.drain()
        self.assertEqual(self.view.metric_cpu.val_lbl.text(),'Unavailable')
        self.assertNotIn('Measured',self.view.metric_cpu.sub_lbl.text())
        self.assertEqual(self.view.metric_ram.val_lbl.text(),'Unavailable')
        self.assertNotIn('Measured',self.view.metric_ram.sub_lbl.text())

    def test_readonly_transcript_and_history_have_legible_theme_contrast(self):
        from PyQt6.QtGui import QPalette
        from native_studio.theme import STYLESHEET
        prior=self.app.styleSheet();self.app.setStyleSheet(STYLESHEET)
        self.addCleanup(self.app.setStyleSheet,prior)
        def luminance(color):
            channels=[color.redF(),color.greenF(),color.blueF()]
            values=[c/12.92 if c<=0.04045 else ((c+0.055)/1.055)**2.4 for c in channels]
            return sum(a*b for a,b in zip(values,[0.2126,0.7152,0.0722]))
        for widget in [self.view.chat_display,self.view.audit_log]:
            widget.ensurePolished();palette=widget.viewport().palette()
            fg=luminance(palette.color(QPalette.ColorRole.Text));bg=luminance(palette.color(QPalette.ColorRole.Base))
            self.assertGreaterEqual((max(fg,bg)+0.05)/(min(fg,bg)+0.05),4.5)


if __name__=='__main__':unittest.main()
