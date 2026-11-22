"""Service-backed native executive cockpit with private, data-only recovery."""
from __future__ import annotations
import json,math,time
from PyQt6.QtCore import Qt,QTimer
from PyQt6.QtWidgets import (QWidget,QLabel,QPushButton,QComboBox,QLineEdit,QPlainTextEdit,
    QVBoxLayout,QHBoxLayout,QGridLayout,QSplitter,QScrollArea,QTableWidget,QTableWidgetItem,QHeaderView,QMessageBox)
from native_studio import __version__
from native_studio.widgets import Card,MetricCard
from native_studio.executive_service import ExecutiveService,MODES
from native_studio.chat_recovery import ChatRecoveryController,ChatRecoveryStore
from ui_modernization.generated.studio_overview import OVERVIEW_QSS


def _label(text):
    result=QLabel(text);result.setWordWrap(True);result.setTextFormat(Qt.TextFormat.PlainText)
    return result


def _number(value):
    return float(value)if isinstance(value,(int,float))and not isinstance(value,bool)and math.isfinite(value)else None


class ExecutiveCockpitFullView(QWidget):
    def __init__(self,bus,parent=None,*,service=None,session_store=None):
        super().__init__(parent)
        self.bus=bus;self.service=service or ExecutiveService()
        self._autonomy_mode=None;self._is_streaming=False;self._closed=False
        self._refresh_pending=False;self._generation=0;self._observed_at=None
        self._model_ids=set();self._pending_rows=[];self._queue_fresh=False
        self._conversation_history=[];self._local_audit=[];self._history_text=''
        self._build_ui()
        self._chat_recovery=ChatRecoveryController(self,bus,store=session_store,
            store_factory=lambda:ChatRecoveryStore(namespace='executive'))
        self._chat_recovery.begin()
        self.timer=QTimer(self);self.timer.setInterval(10000);self.timer.timeout.connect(self.refresh);self.timer.start()
        self._age_timer=QTimer(self);self._age_timer.setInterval(1000);self._age_timer.timeout.connect(self._mark_stale);self._age_timer.start()
        self.refresh()

    def _build_ui(self):
        self.setObjectName('aibsStudioOverview')
        self.setStyleSheet(OVERVIEW_QSS)
        layout=QVBoxLayout(self);layout.setContentsMargins(0,0,0,0);layout.setSpacing(0)
        self.overview_scroll=QScrollArea();self.overview_scroll.setWidgetResizable(True)
        content=QWidget();content.setProperty('overviewSurface','content')
        body=QVBoxLayout(content);body.setContentsMargins(24,24,24,24);body.setSpacing(16)
        self.overview_scroll.setWidget(content);layout.addWidget(self.overview_scroll)
        eyebrow=_label('STEHOUWER / EXECUTIVE WORKSPACE');eyebrow.setProperty('overviewRole','eyebrow');body.addWidget(eyebrow)
        top=QHBoxLayout();title=_label('Studio overview');title.setProperty('overviewRole','title');top.addWidget(title,1)
        version=_label('v'+__version__.removeprefix('v'));version.setProperty('overviewRole','muted');top.addWidget(version);body.addLayout(top)
        self.service_status=_label('Opening executive service…');self.service_status.setProperty('overviewRole','muted');body.addWidget(self.service_status)
        self.overview_actions=QGridLayout();self.overview_actions.setSpacing(8);body.addLayout(self.overview_actions)
        self.btn_safe=QPushButton('SAFE');self.btn_semi=QPushButton('SEMI_AUTO');self.btn_full=QPushButton('FULL_AUTO')
        for button,mode in [(self.btn_safe,'SAFE'),(self.btn_semi,'SEMI_AUTO'),(self.btn_full,'FULL_AUTO')]:
            button.setCheckable(True);button.setEnabled(False)
            button.clicked.connect(lambda _checked,m=mode:self._set_autonomy(m))
        self.btn_rollback=QPushButton('Recovery not connected');self.btn_rollback.setEnabled(False)
        self.btn_rollback.setToolTip('A reviewed checkpoint recovery adapter is still required. No files will be changed.')
        self.btn_halt=QPushButton('Halt queued actions');self.btn_halt.clicked.connect(self._on_halt);self.btn_halt.setProperty('overviewRole','halt')
        self._overview_action_buttons=[self.btn_safe,self.btn_semi,self.btn_full,self.btn_rollback,self.btn_halt]
        strip=QGridLayout();self.sentinel_status=_label('Sentinel state not observed.');strip.addWidget(self.sentinel_status,0,0,1,2)
        self.refresh_btn=QPushButton('Refresh observed state');self.refresh_btn.clicked.connect(self.refresh);strip.addWidget(self.refresh_btn,1,0)
        self.voice_btn=QPushButton('Voice not connected');self.voice_btn.setEnabled(False);strip.addWidget(self.voice_btn,1,1)
        body.addLayout(strip)
        self.overview_grid=QGridLayout();self.overview_grid.setSpacing(16);body.addLayout(self.overview_grid)
        self._overview_panels=[self._copilot(),self._matrix(),self._queue(),self._hardware_panel()]
        for panel in self._overview_panels:panel.setMinimumHeight(540)
        self._overview_columns=0;self._overview_action_columns=0
        self.send_btn.setProperty('overviewRole','primary')
        for metric in (self.metric_gpu,self.metric_cpu,self.metric_ram,self.metric_vault,self.metric_spend):
            metric.val_lbl.setStyleSheet('');metric.val_lbl.setProperty('overviewRole','metric')
            metric.sub_lbl.setStyleSheet('');metric.sub_lbl.setProperty('overviewRole','muted');metric.sub_lbl.setWordWrap(True)
        self.recovery_status=_label('Opening private executive recovery…');self.recovery_retry=QPushButton('Retry private recovery')
        self.recovery_status.setProperty('overviewRole','muted')
        footer=QHBoxLayout();footer.addWidget(self.recovery_status,1);footer.addWidget(self.recovery_retry);body.addLayout(footer)
        QTimer.singleShot(0,self._reflow_overview)

    def _reflow_overview(self):
        if self._closed:return
        width=self.overview_scroll.viewport().width()
        columns=2 if width>=1050 else 1
        if columns!=self._overview_columns:
            self._overview_columns=columns
            while self.overview_grid.count():self.overview_grid.takeAt(0)
            for index,panel in enumerate(self._overview_panels):self.overview_grid.addWidget(panel,index//columns,index%columns)
            self.overview_grid.setColumnStretch(0,1);self.overview_grid.setColumnStretch(1,1 if columns==2 else 0)
        action_columns=5 if width>=1150 else 3 if width>=850 else 2
        if action_columns!=self._overview_action_columns:
            self._overview_action_columns=action_columns
            while self.overview_actions.count():self.overview_actions.takeAt(0)
            for index,button in enumerate(self._overview_action_buttons):self.overview_actions.addWidget(button,index//action_columns,index%action_columns)

    def resizeEvent(self,event):
        super().resizeEvent(event)
        if hasattr(self,'overview_scroll') and not self._closed:QTimer.singleShot(0,self._reflow_overview)

    def _copilot(self):
        panel=Card('Executive copilot');lay=panel.layout_box
        self.model_picker=QComboBox();self.model_combo=self.model_picker;lay.addWidget(self.model_picker)
        presets=QHBoxLayout()
        for text,callback in [('Observed health',self._show_observed),('Render request',lambda:self.input_edit.setText('Render a vertical 9:16 short'))]:
            button=QPushButton(text);button.clicked.connect(callback);presets.addWidget(button)
            if text=='Render request':button.setProperty('overviewRole','secondary')
        lay.addLayout(presets)
        self.chat_display=QPlainTextEdit();self.chat_display.setObjectName('Console');self.chat_display.setReadOnly(True)
        self.chat_display.setPlainText('Executive requests are handled by the local AI-BS service.\nNo action has been submitted by opening this view.\n')
        self.chat_edit=self.chat_display;lay.addWidget(self.chat_display,1)
        row=QHBoxLayout();self.input_edit=QLineEdit();self.prompt_input=self.input_edit
        self.input_edit.setPlaceholderText('Describe an executive request…')
        self.input_edit.returnPressed.connect(lambda:self._send_prompt(self.input_edit.text()))
        self.send_btn=QPushButton('Send to service');self.send_btn.clicked.connect(lambda:self._send_prompt(self.input_edit.text()))
        row.addWidget(self.input_edit,1);row.addWidget(self.send_btn);lay.addLayout(row)
        return panel

    def _matrix(self):
        panel=Card('Observed services');lay=panel.layout_box
        self.matrix_status=_label('No current observation.');lay.addWidget(self.matrix_status)
        self.pillar_labels={}
        for key,title in [('core','Web core'),('media','Media'),('broadcast','Broadcast'),('crypto','Crypto'),('ollama','Models'),('vector','Vector / VST')]:
            card=Card(title);label=_label('Not observed.');self.pillar_labels[key]=label;card.addWidget(label);lay.addWidget(card)
        lay.addStretch();scroll=QScrollArea();scroll.setWidgetResizable(True);scroll.setWidget(panel);return scroll

    def _queue(self):
        panel=Card('Action queue and service history');lay=panel.layout_box
        self.queue_status_lbl=_label('Queue not observed.');lay.addWidget(self.queue_status_lbl)
        self.table_queue=QTableWidget(0,4);self.table_queue.setHorizontalHeaderLabels(['ID','Pillar','Action','Status'])
        self.table_queue.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table_queue.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table_queue.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch);lay.addWidget(self.table_queue,1)
        controls=QHBoxLayout();self.approve_btn=QPushButton('Review approval');self.reject_btn=QPushButton('Reject selected')
        self.approve_btn.clicked.connect(lambda:self._resolve_selected('APPROVE'))
        self.reject_btn.clicked.connect(lambda:self._resolve_selected('REJECT'))
        for button in [self.approve_btn,self.reject_btn]:button.setEnabled(False);controls.addWidget(button)
        lay.addLayout(controls)
        self.audit_log=QPlainTextEdit();self.audit_log.setObjectName('Console');self.audit_log.setReadOnly(True);self.audit_log.setMaximumHeight(180);lay.addWidget(self.audit_log)
        return panel

    def _hardware_panel(self):
        panel=Card('Observed hardware and service policy');lay=panel.layout_box
        self.metric_gpu=MetricCard('GPU','Unavailable','No current GPU observation.')
        self.metric_cpu=MetricCard('CPU','Unavailable','No current CPU observation.')
        self.metric_ram=MetricCard('Memory','Unavailable','No current memory observation.')
        self.metric_vault=MetricCard('Vault','Not measured','A connected read-only vault count is still required.')
        self.metric_spend=MetricCard('Service spend ledger','Not observed','External billing is not verified here.')
        for metric in [self.metric_gpu,self.metric_cpu,self.metric_ram,self.metric_vault,self.metric_spend]:lay.addWidget(metric)
        lay.addStretch();scroll=QScrollArea();scroll.setWidgetResizable(True);scroll.setWidget(panel);return scroll

    def _audit(self,text):
        self._local_audit.append(time.strftime('%H:%M:%S')+' '+text);self._local_audit=self._local_audit[-50:]
        self.audit_log.setPlainText(self._history_text+'\n'+'\n'.join(self._local_audit))

    def _apply_mode(self,mode):
        self._autonomy_mode=mode if mode in MODES else None
        for button,value in [(self.btn_safe,'SAFE'),(self.btn_semi,'SEMI_AUTO'),(self.btn_full,'FULL_AUTO')]:
            button.setChecked(self._autonomy_mode==value);button.setEnabled(self._autonomy_mode is not None and not self._is_streaming)

    def refresh(self):
        if self._closed or self._refresh_pending or self._is_streaming:return
        self._refresh_pending=True;generation=self._generation
        def done(data):
            self._refresh_pending=False
            if self._closed:return
            if generation!=self._generation:
                if not self._is_streaming:self.refresh()
                return
            self._apply_snapshot(data)
        def failed(_message):
            self._refresh_pending=False
            if not self._closed:
                self.service_status.setText('Executive observations unavailable; displayed values may be stale.')
                self.matrix_status.setText('Observations unavailable / stale.');self._queue_fresh=False;self._model_ids.clear();self._enable_actions()
                for button in [self.btn_safe,self.btn_semi,self.btn_full]:button.setEnabled(False)
        try:self.bus.submit(self.service.snapshot,on_result=done,on_error=failed)
        except Exception:failed('')

    def _apply_snapshot(self,snapshot):
        self._observed_at=snapshot['observedMonotonic'];self._snapshot=snapshot
        sections=snapshot['sections']
        def data(key):
            part=sections.get(key,{})
            return part.get('data',{})if part.get('ok')and isinstance(part.get('data'),dict)else None
        self.service_status.setText('Executive service responded.'if data('backend')is not None else 'Executive service unavailable.')
        failed=sum(not p.get('ok',False)for p in sections.values())
        self.matrix_status.setText('Observed '+time.strftime('%H:%M:%S')+f' • {failed} unavailable sections • listener checks are not workflow acceptance.')
        mode=data('autonomy');self._apply_mode(mode.get('autonomy_mode')if mode else None)
        ports=snapshot.get('ports',{})
        def port(p):
            value=ports.get(p,{}).get('listening')
            return f'{p}: '+('listening'if value is True else 'not listening'if value is False else 'unavailable')
        self.pillar_labels['core'].setText('\n'.join(port(p)for p in [8080,8000,5173]))
        self.pillar_labels['media'].setText(port(8188)+'\n'+port(8189)+'\nRender/NVENC readiness has not been tested.')
        unreal=ports.get(8888,{}).get('listening')
        demand='On demand: off as expected.'if unreal is False else 'On demand: listener present; session ownership unverified.'if unreal else 'On demand: state unavailable.'
        self.pillar_labels['broadcast'].setText('Native Broadcast Studio\nManage capture and output in Creative Media → Universal AV.\n'+demand)
        self.pillar_labels['crypto'].setText(port(8007)+'\nTrading state / order guards are not verified here.')
        self.pillar_labels['vector'].setText('\n'.join(port(p)for p in [11435,8002,8013]))
        installed,loaded=data('installed_models'),data('loaded_models')
        installed_names=[m['name']for m in installed.get('models',[])if isinstance(m.get('name'),str)]if installed else None
        loaded_names=[m['name']for m in loaded.get('models',[])if isinstance(m.get('name'),str)]if loaded else None
        self.pillar_labels['ollama'].setText(port(11434)+'\nInstalled: '+(str(len(installed_names))if installed_names is not None else 'unavailable')+' | Loaded: '+(str(len(loaded_names))if loaded_names is not None else 'unavailable'))
        if installed_names is not None:
            selected=self.model_picker.currentData();self.model_picker.blockSignals(True);self.model_picker.clear()
            for name in installed_names:self.model_picker.addItem(name,name)
            index=self.model_picker.findData(selected)
            if index>=0:self.model_picker.setCurrentIndex(index)
            self.model_picker.blockSignals(False);self._model_ids=set(installed_names)
        else:self._model_ids=set()
        pending=data('pending');self._queue_fresh=pending is not None
        if pending is not None:
            self._pending_rows=pending['pending_actions'][:500];self.table_queue.setRowCount(len(self._pending_rows))
            for row,item in enumerate(self._pending_rows):
                for col,key in enumerate(['action_id','pillar','action','status']):
                    value=item.get('action_name')or item.get('action','—')if key=='action'else item.get(key,'—')
                    self.table_queue.setItem(row,col,QTableWidgetItem(str(value)))
            self.queue_status_lbl.setText(f'{len(pending["pending_actions"])} pending actions observed.')
        else:self.queue_status_lbl.setText('Queue unavailable; earlier rows retained without current confirmation.')
        history=data('history')
        self._history_text='Service history unavailable.'if history is None else '\n'.join(str(row.get('action_name')or row.get('action')or 'Unnamed action')+' | '+str(row.get('status','unreported'))for row in history['history'][:25])or 'Service history: no records returned.'
        self.audit_log.setPlainText(self._history_text+'\n'+'\n'.join(self._local_audit))
        sentinel=data('sentinel')
        self.sentinel_status.setText('Sentinel unavailable.'if sentinel is None else f'Service sentinel reports {len(sentinel["alerts"])} alerts. Engine: '+str(sentinel.get('engine_status',{}).get('running',sentinel.get('engine_status',{}).get('status','unreported'))))
        cloud=data('cloud');policy=cloud.get('gpu_sovereignty',{})if cloud else {}
        spend=_number(policy.get('current_daily_spend_usd'))
        self.metric_spend.set_value(f'${spend:.2f}'if spend is not None else 'Unavailable')
        self.metric_spend.set_summary('Service-recorded value; external billing unverified. Cloud burst: '+str(policy.get('cloud_burst_enabled','unreported')))
        hardware=data('hardware')or {};gpu=hardware.get('gpu',{});system=hardware.get('system',{})
        temp=_number(gpu.get('temp_c'));used=_number(gpu.get('vram_used_gb'));total=_number(gpu.get('vram_total_gb'));fan=_number(gpu.get('fan_pct'))
        self.metric_gpu.set_value(f'{temp:g}°C'if gpu.get('detected')and temp is not None else 'Unavailable')
        self.metric_gpu.set_summary((f'{used:.1f}/{total:.1f} GB VRAM'if used is not None and total is not None else 'VRAM unavailable')+' | Fan '+(f'{fan:g}%'if fan is not None else 'unavailable'))
        cpu=_number(system.get('cpu_pct'));ram=_number(system.get('ram_used_gb'));ram_total=_number(system.get('ram_total_gb'))
        self.metric_cpu.set_value(f'{cpu:.1f}%'if cpu is not None else 'Unavailable');self.metric_cpu.set_summary('Measured CPU utilization.'if cpu is not None else 'No current CPU observation.')
        self.metric_ram.set_value(f'{ram:.1f}/{ram_total:.1f} GB'if ram is not None and ram_total is not None else 'Unavailable')
        self.metric_ram.set_summary('Measured system memory usage.'if ram is not None and ram_total is not None else 'No current memory observation.')
        self._enable_actions()

    def _mark_stale(self,*,now=None):
        current=time.monotonic()if now is None else now
        if self._observed_at is not None and current-self._observed_at>15:
            self.service_status.setText('The last service observation is stale.')
            self.matrix_status.setText('Observed state is stale; refresh before relying on these values.')
            self._queue_fresh=False;self._model_ids.clear();self._enable_actions()
            for button in [self.btn_safe,self.btn_semi,self.btn_full]:button.setEnabled(False)

    def _enable_actions(self):
        enabled=self._queue_fresh and not self._is_streaming
        self.approve_btn.setEnabled(enabled);self.reject_btn.setEnabled(enabled)
        self.btn_halt.setEnabled(not self._is_streaming)

    def _mutate(self,operation,on_result):
        if self._closed or self._is_streaming:return
        self._generation+=1;self._is_streaming=True;self.send_btn.setEnabled(False);self._apply_mode(self._autonomy_mode);self._enable_actions()
        def done(data):
            if self._closed:return
            self._is_streaming=False;self.send_btn.setEnabled(self._chat_recovery.ready)
            on_result(data);self._apply_mode(self._autonomy_mode);self._enable_actions();self.refresh()
        def failed(_message):
            if self._closed:return
            self._is_streaming=False;self.send_btn.setEnabled(self._chat_recovery.ready)
            self._audit('Service action not confirmed. No automatic retry; refresh actual state before deciding.')
            self._apply_mode(self._autonomy_mode);self._enable_actions();self.refresh()
        try:self.bus.submit(operation,on_result=done,on_error=failed)
        except Exception:failed('')

    def _set_autonomy(self,mode):
        self._apply_mode(self._autonomy_mode)
        def acknowledged(data):
            self._apply_mode(data['autonomy_mode']);self._audit('Service acknowledged governance mode '+data['autonomy_mode']+'.')
        self._mutate(lambda:self.service.set_autonomy(mode),acknowledged)

    def _on_halt(self):
        def acknowledged(data):
            self._apply_mode(data['autonomy_mode']);self._audit('Service acknowledged HALTED; revoked count: '+str(data.get('revoked_count','unreported'))+'. External system state is not inferred.')
        self._mutate(self.service.halt,acknowledged)

    def _resolve_selected(self,decision):
        row=self.table_queue.currentRow()
        if not self._queue_fresh or row<0 or row>=len(self._pending_rows)or self._is_streaming:return
        item=self._pending_rows[row];action_id=item.get('action_id')
        detail=json.dumps(item,ensure_ascii=False,indent=2)
        answer=QMessageBox.question(self,'Review service action',decision+' this exact service action?\n\n'+detail,QMessageBox.StandardButton.Yes|QMessageBox.StandardButton.No,QMessageBox.StandardButton.No)
        if answer!=QMessageBox.StandardButton.Yes:return
        self._mutate(lambda:self.service.resolve(action_id,decision),lambda data:self._audit('Service acknowledged action decision; result: '+str(data['resolution'].get('status','unreported'))))

    def _send_prompt(self,text):
        if self._is_streaming or not self._chat_recovery.ready or self._chat_recovery._load_failed:return
        prompt=text.strip()
        if not prompt:return
        if prompt.startswith('/switch '):
            target=prompt.split(maxsplit=1)[1];window=self.window()
            if hasattr(window,'jump_to_tab'):window.jump_to_tab(target)
            return
        if prompt in {'/oversight','/parent'}:self._show_observed();return
        model=self.model_picker.currentData()
        if model not in self._model_ids:
            self._audit('Choose a model from a current observed model list. Your draft is retained.');return
        def acknowledged(data):
            self.chat_display.appendPlainText('\n[OPERATOR]:\n'+prompt+'\n\n[EXECUTIVE SERVICE]:\n'+data['response'])
            for action in data['tool_calls']:
                self.chat_display.appendPlainText('[SERVICE ACTION RESULT]: '+json.dumps(action,ensure_ascii=False))
            self._conversation_history=(self._conversation_history+[(prompt,data['response'])])[-10:]
            if self.input_edit.text()==text:self.input_edit.clear()
            self._chat_recovery.tick()
        self._mutate(lambda:self.service.chat(prompt,model),acknowledged)

    def _show_observed(self):
        self.chat_display.appendPlainText('\n[OBSERVED STATE]:\n'+self.matrix_status.text()+'\n'+'\n'.join(label.text()for label in self.pillar_labels.values()))
        self.refresh()

    def capture_recovery_state(self):
        return {'transcript':self.chat_display.toPlainText(),'draft':self.input_edit.text(),'scratchpad':'',
                'history':[list(pair)for pair in self._conversation_history],'model':str(self.model_picker.currentData()or '')}

    def apply_recovery_state(self,state):
        self.chat_display.setPlainText(state['transcript']);self.input_edit.setText(state['draft'])
        self._conversation_history=[tuple(pair)for pair in state['history']]
        if state['model']and self.model_picker.findData(state['model'])<0:self.model_picker.addItem(state['model']+' (restored, unverified)',state['model'])
        index=self.model_picker.findData(state['model'])
        if index>=0:self.model_picker.setCurrentIndex(index)

    def shutdown(self):
        self._closed=True;self._generation+=1
        self.timer.stop();self._age_timer.stop();self._chat_recovery.shutdown()
