"""Numeric authoring workspace backed by the real native creator process."""
from pathlib import Path
import math
import struct
import uuid
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (QWidget,QVBoxLayout,QHBoxLayout,QFormLayout,QLabel,QPushButton,
    QLineEdit,QTreeWidget,QTreeWidgetItem,QListWidget,QSplitter,QPlainTextEdit,
    QFileDialog,QInputDialog,QMessageBox,QScrollArea,QLayout)
from .project_model import ProjectDefinition,ProjectError
from .creator_client import CreatorClient
from .creator_viewport import ViewportClient
from .creator_wire import Opcode
from .creator_payload import Transaction,EditRequest,Create,Erase,SetField,encode_edit
from .creator_commands import (Status,open_document,scoped,prepared_handle,history,
                               snapshot_page,decode_page,decode_description)
from native_studio.theme import PALETTE
from native_studio.responsive_layout import FlowLayout


class CreatorView(QWidget):
    document_changed=pyqtSignal()

    def __init__(self,executable,parent=None):
        super().__init__(parent)
        self.setObjectName('Root');self.executable=Path(executable)
        self.client=CreatorClient(self);self.definition=None;self.rows=();self.selected_id=None
        self.viewport=ViewportClient(self);self.viewport.selection.connect(self._viewport_selected)
        self.viewport.message.connect(lambda text:self.status.setText(text));self.viewport.closed.connect(self._viewport_closed)
        self.field_editors={};self.loaded=False;self.busy=False;self.schemas=()
        self._tasks={};self._token=None;self._snapshot_tag=None;self._page_rows=[];self._deferred_releases=set()
        self._close_callback=None;self._closing_project=False;self._create_pending=False
        self._selected_after=None;self._refresh_message='';self._known_projects={}
        layout=QVBoxLayout(self)
        layout.setSizeConstraint(QLayout.SizeConstraint.SetMinimumSize)
        title=QLabel('AI-BS Creator — World Workspace');title.setObjectName('PanelTitle');layout.addWidget(title)
        subtitle=QLabel('Native world authoring · 3D preview opens in its own window; chapter-layout tools remain in development.')
        subtitle.setWordWrap(True);layout.addWidget(subtitle)
        bar=FlowLayout();layout.addLayout(bar)
        self.new_button=QPushButton('New project');self.open_button=QPushButton('Open project');self.close_button=QPushButton('Close project')
        for button in (self.new_button,self.open_button,self.close_button):bar.addWidget(button)
        self.new_button.clicked.connect(self._choose_new);self.open_button.clicked.connect(self._choose_open)
        self.close_button.clicked.connect(lambda:self.prepare_close())
        self.address=QLabel('No project selected');self.address.setWordWrap(True);layout.addWidget(self.address)
        self.status=QLabel('Choose or create a local project.');self.status.setWordWrap(True);layout.addWidget(self.status)
        split=QSplitter();self.workspace_splitter=split;split.setChildrenCollapsible(False)
        split.setMinimumHeight(320);layout.addWidget(split,1)
        project_panel=QWidget();p=QVBoxLayout(project_panel);p.addWidget(QLabel('Selected projects'))
        self.projects=QListWidget();p.addWidget(self.projects);split.addWidget(project_panel)
        self.projects.setStyleSheet(f"QListWidget {{ background: {PALETTE['bg_dark']}; color: {PALETTE['text']}; border: 1px solid {PALETTE['border']}; }} QListWidget::item:selected {{ background: {PALETTE['panel_alt']}; color: {PALETTE['cyan']}; }}")
        self.projects.itemDoubleClicked.connect(lambda item:self._run(lambda:self.open_project(Path(item.data(Qt.ItemDataRole.UserRole)))))
        objects=QWidget();o=QVBoxLayout(objects);o.addWidget(QLabel('World outliner'))
        self.outliner=QTreeWidget();self.outliner.setObjectName('CreatorOutliner');self.outliner.setHeaderLabels(['Object','Alias','UUID'])
        self.outliner.setStyleSheet(f"QTreeWidget {{ background: {PALETTE['bg_dark']}; color: {PALETTE['text']}; border: 1px solid {PALETTE['border']}; }} QTreeWidget::item:selected {{ background: {PALETTE['panel_alt']}; color: {PALETTE['cyan']}; }}")
        for column,width in enumerate((200,140,300)):self.outliner.setColumnWidth(column,width)
        self.outliner.currentItemChanged.connect(lambda *_:self._selection_changed());o.addWidget(self.outliner)
        nodebar=FlowLayout();o.addLayout(nodebar);self.alias_input=QLineEdit();self.alias_input.setPlaceholderText('New object alias')
        self.name_input=QLineEdit();self.name_input.setPlaceholderText('Display name');nodebar.addWidget(self.alias_input);nodebar.addWidget(self.name_input)
        self.add_button=QPushButton('Add node');self.delete_button=QPushButton('Delete selected');nodebar.addWidget(self.add_button);nodebar.addWidget(self.delete_button)
        self.add_button.clicked.connect(lambda:self._run(lambda:self.add_node(self.alias_input.text(),self.name_input.text())))
        self.delete_button.clicked.connect(lambda:self._run(self.delete_selected));split.addWidget(objects)
        inspector=QWidget();i=QVBoxLayout(inspector);i.addWidget(QLabel('Inspector'))
        self.selection_label=QLabel('Select an object');self.selection_label.setWordWrap(True);i.addWidget(self.selection_label)
        scroll=QScrollArea();scroll.setWidgetResizable(True);self.form_widget=QWidget();self.form=QFormLayout(self.form_widget);scroll.setWidget(self.form_widget);i.addWidget(scroll)
        edits=FlowLayout();i.addLayout(edits);self.preview_button=QPushButton('Preview change');self.apply_button=QPushButton('Apply preview')
        edits.addWidget(self.preview_button);edits.addWidget(self.apply_button)
        self.preview_button.clicked.connect(lambda:self._run(self.preview_selected));self.apply_button.clicked.connect(lambda:self._run(self.apply_preview))
        self.preview_details=QPlainTextEdit();self.preview_details.setReadOnly(True);self.preview_details.setMaximumHeight(150);i.addWidget(self.preview_details);split.addWidget(inspector)
        self.preview_details.setStyleSheet(f"QPlainTextEdit {{ background: {PALETTE['bg_dark']}; color: {PALETTE['text']}; border: 1px solid {PALETTE['border']}; padding: 8px; }}")
        split.setSizes([190,500,350])
        actions=FlowLayout();layout.addLayout(actions)
        self.refresh_button=QPushButton('Refresh world');self.undo_button=QPushButton('Undo');self.redo_button=QPushButton('Redo');self.save_button=QPushButton('Save world')
        for button in (self.refresh_button,self.undo_button,self.redo_button,self.save_button):actions.addWidget(button)
        self.viewport_button=QPushButton('Open 3D preview');self.stop_viewport_button=QPushButton('Close 3D preview')
        actions.addWidget(self.viewport_button);actions.addWidget(self.stop_viewport_button)
        self.viewport_button.clicked.connect(lambda:self._run(self.open_viewport));self.stop_viewport_button.clicked.connect(self.viewport.stop)
        self.refresh_button.clicked.connect(lambda:self._run(self.refresh_world))
        self.undo_button.clicked.connect(lambda:self._run(lambda:self._travel(False)))
        self.redo_button.clicked.connect(lambda:self._run(lambda:self._travel(True)))
        self.save_button.clicked.connect(lambda:self._run(self.save_world))
        self.client.ready.connect(self._transport_ready);self.client.response.connect(self._response)
        self.client.request_failed.connect(self._failed);self.client.closed.connect(self._closed)
        self._controls()
        if not self.executable.is_file():self.status.setText('The native creator host must be built before editing projects.')

    def _run(self,action):
        try:return action()
        except Exception as error:self.status.setText(str(error));self._controls();return None

    @staticmethod
    def _tag(reply):return (reply.scope,reply.head_revision,reply.checkpoint_id)

    def _controls(self):
        connected=self.client.state=='ready' and self.definition is not None
        coherent=self.client.head is not None and self._snapshot_tag==self._tag(self.client.head)
        usable=connected and self.loaded and coherent and not self.busy
        self.viewport_button.setEnabled(usable and self.viewport.state=='closed')
        self.stop_viewport_button.setEnabled(self.viewport.state not in ('closed','stopping'))
        for button in (self.new_button,self.open_button):button.setEnabled(self.executable.is_file() and self.definition is None and self.client.state=='closed')
        self.close_button.setEnabled(self.definition is not None and not self._closing_project)
        self.add_button.setEnabled(usable);self.delete_button.setEnabled(usable and self.selected_id is not None)
        self.preview_button.setEnabled(usable and self.selected_id is not None)
        self.apply_button.setEnabled(usable and self._token is not None)
        self.save_button.setEnabled(usable);self.refresh_button.setEnabled(connected and not self.busy)
        self.undo_button.setEnabled(usable and self.client.head.undo_depth>0)
        self.redo_button.setEnabled(usable and self.client.head.redo_depth>0)
        self.outliner.setEnabled(usable)
        for editor in self.field_editors.values():editor.setEnabled(usable)

    def _choose_new(self):
        directory=QFileDialog.getExistingDirectory(self,'Create project in selected folder')
        if not directory:return
        name,ok=QInputDialog.getText(self,'Project name','Project identifier:',text=Path(directory).name)
        if ok:self._run(lambda:self.new_project(Path(directory),name))

    def _choose_open(self):
        directory=QFileDialog.getExistingDirectory(self,'Open project folder')
        if directory:self._run(lambda:self.open_project(Path(directory)))

    def _can_open(self):
        if self.definition is not None or self.client.state!='closed' or self.viewport.state!='closed':raise ProjectError('Close the current project first')
        if self.client.uncertain_operations:raise ProjectError('Review or explicitly discard interrupted operations before switching projects')
        if not self.executable.is_file():raise ProjectError('Native creator host is unavailable')

    def new_project(self,directory,project,branch='main'):
        self._can_open();self._open(ProjectDefinition.create(directory,project,branch),True)

    def open_project(self,directory):
        self._can_open();definition=ProjectDefinition.load(directory)
        if not (definition.directory/'world.aibs').is_file():raise ProjectError('This project has no saved world; it will not be silently reinitialized')
        self._open(definition,False)

    def _open(self,definition,create):
        self.definition=definition;self._create_pending=create;self.loaded=False;self.busy=True
        self.rows=();self.selected_id=None;self._tasks.clear();self._snapshot_tag=None;self._token=None;self._selected_after=None;self._deferred_releases.clear()
        key=str(definition.directory)
        if key not in self._known_projects:
            self.projects.addItem(definition.project);item=self.projects.item(self.projects.count()-1);item.setData(Qt.ItemDataRole.UserRole,key);item.setToolTip(key);self._known_projects[key]=item
        self.address.setText(f'{definition.project} / {definition.branch}\n{definition.directory}')
        self.status.setText('Connecting to native authoring owner…');self._controls()
        self.client.start(self.executable,definition.directory)

    def _transport_ready(self):
        if self.definition is None:return
        self._run(lambda:self._send('open',Opcode.OPEN,open_document(self.definition.project,self.definition.branch,self.definition.fields,self._create_pending)))

    def _send(self,kind,opcode,payload,revision=None,extra=None):
        try:identity=self.client.request(opcode,payload,revision=revision)
        except Exception:
            self.busy=False;self._controls();raise
        if self.client.state!='ready':raise ProjectError('Creator connection closed before request admission')
        self._tasks[identity]=(kind,extra);return identity

    def _require_editable(self):
        if not self.loaded or self.busy or self.client.state!='ready':raise ProjectError('Wait for the current world operation')
        if self._snapshot_tag!=self._tag(self.client.head):raise ProjectError('World changed; refresh before editing')

    def _invalidate_preview(self,release=True):
        token=self._token;self._token=None;self.apply_button.setEnabled(False)
        if token and release and self.client.state=='ready' and self.client.head:
            self._deferred_releases.add(token);self._flush_releases()
        if token:
            self.preview_details.clear();self.status.setText('Preview invalidated; preview the current inputs again.')

    def _flush_releases(self):
        if self.client.state!='ready' or not self.client.head:return
        while self._deferred_releases and self.client.pending_count<8:
            token=next(iter(self._deferred_releases))
            try:
                identity=self.client.request(Opcode.RELEASE_PREPARED,prepared_handle(self.client.head.scope,token))
            except Exception:return
            self._tasks[identity]=('release',None);self._deferred_releases.remove(token)

    def refresh_world(self):
        if self.busy:raise ProjectError('Wait for the current world operation')
        self._begin_refresh('World refreshed')

    def _begin_refresh(self,message):
        self._invalidate_preview();self.busy=True;self._refresh_message=message
        self._page_tag=self._tag(self.client.head);self._page_rows=[];self._page_uuids=set();self._page_aliases=set();self._page_bytes=0;self._cursor=''
        self._controls();self._request_page()

    def _request_page(self):
        scope,revision,checkpoint=self._page_tag
        self._send('page',Opcode.SNAPSHOT_PAGE,snapshot_page(scope,checkpoint,self._cursor),revision)

    def _response(self,identity,reply):
        task=self._tasks.pop(identity,None)
        if reply.status in (Status.APPLIED,Status.UNDONE,Status.REDONE,Status.SAVED):self._deferred_releases.clear()
        self._flush_releases()
        if task is None:
            if self.loaded and not self.busy and self._snapshot_tag!=self._tag(reply):self._run(lambda:self._begin_refresh('World updated by another authoring request'))
            self._service_close()
            return
        kind,extra=task
        if kind=='release':self._service_close();return
        try:
            if reply.status==Status.REJECTED:raise ProjectError(reply.message)
            if kind=='open':self._send('describe',Opcode.DESCRIBE,scoped(reply.scope),reply.head_revision)
            elif kind=='describe':
                self.schemas=decode_description(reply.body)
                if self.schemas!=self.definition.fields:raise ProjectError('Native schemas differ from project definition')
                self._begin_refresh('Project opened')
            elif kind=='page':self._receive_page(reply)
            elif kind in ('preview','auto_preview'):
                if reply.status==Status.DUPLICATE:self._begin_refresh('Previously accepted operation; no effect repeated');return
                if reply.status!=Status.PREPARED or not reply.token:raise ProjectError('No prepared change returned')
                if not reply.save_compatible:
                    self._send('release',Opcode.RELEASE_PREPARED,prepared_handle(reply.scope,reply.token))
                    raise ProjectError('Change cannot be checkpointed: '+reply.save_message)
                if kind=='auto_preview':
                    self._send('mutate',Opcode.APPLY_PREPARED,prepared_handle(reply.scope,reply.token),reply.head_revision,extra)
                else:
                    selected,texts=extra
                    if selected!=self.selected_id or texts!={k:e.text() for k,e in self.field_editors.items()}:
                        self._send('release',Opcode.RELEASE_PREPARED,prepared_handle(reply.scope,reply.token));raise ProjectError('Selection or inputs changed; preview again')
                    self._token=reply.token;self.busy=False
                    self.preview_details.setPlainText(f'Save compatible: yes\nEncoded checkpoint: {reply.save_bytes:,} bytes\n{reply.save_message}\nNative geometry, route and navigation dependencies are not assessed by this numeric editor.')
                    self.status.setText('Preview ready. Apply to publish one grouped change.');self._controls()
            elif kind in ('mutate','save'):
                self._selected_after=extra
                self._begin_refresh('Saved world' if reply.status==Status.SAVED else 'Authoring change applied; save to keep it')
        except Exception as error:
            if kind in ('open','describe','page'):
                self.loaded=False
                self._page_rows=[]
            self.busy=False;self.status.setText(str(error));self._controls()
            if kind in ('open','describe','page','save') and self._close_callback:
                self._close_callback=None;self._save_then_close=False
        self._service_close()

    def _receive_page(self,reply):
        if self._tag(reply)!=self._page_tag:raise ProjectError('Snapshot changed during refresh; retry')
        rows,cursor,more=decode_page(reply.body);self._page_bytes+=len(reply.body)
        if self._page_bytes>64*1024*1024 or len(self._page_rows)+len(rows)>10000:raise ProjectError('World view storage limit exceeded')
        previous=self._cursor
        for row in rows:
            if row.uuid in self._page_uuids or row.alias in self._page_aliases or row.alias<=previous:raise ProjectError('Duplicate or unordered snapshot entity')
            previous=row.alias;self._page_uuids.add(row.uuid);self._page_aliases.add(row.alias);self._page_rows.append(row)
        if (rows and cursor!=rows[-1].alias) or (more and (not rows or cursor<=self._cursor)):raise ProjectError('Snapshot cursor did not advance')
        self._cursor=cursor
        if more:self._request_page();return
        if len(self._page_rows)!=reply.world_count:raise ProjectError('Snapshot entity count differs from native world')
        selected=self._selected_after or self.selected_id;self._selected_after=None
        self.rows=tuple(self._page_rows);self._snapshot_tag=self._page_tag;self.loaded=True;self.busy=False
        self.outliner.blockSignals(True);self.outliner.clear()
        selected_item=None
        for row in self.rows:
            item=QTreeWidgetItem([row.name,row.alias,row.uuid]);item.setData(0,Qt.ItemDataRole.UserRole,row.uuid);self.outliner.addTopLevelItem(item)
            if row.uuid==selected:selected_item=item
        self.outliner.setCurrentItem(selected_item)
        self.outliner.blockSignals(False);self._selection_changed()
        self.status.setText(f'{self._refresh_message} · revision {reply.head_revision} · '+('unsaved' if self.client.dirty else 'saved'))
        self._controls();self.document_changed.emit()

    def _selection_changed(self):
        self._invalidate_preview();item=self.outliner.currentItem();self.selected_id=item.data(0,Qt.ItemDataRole.UserRole) if item else None
        while self.form.rowCount():self.form.removeRow(0)
        self.field_editors={}
        row=next((r for r in self.rows if r.uuid==self.selected_id),None)
        if row:
            self.selection_label.setText(f'{row.name}\n{row.uuid}');values=dict(row.fields)
            for name,low,high in self.schemas:
                editor=QLineEdit(repr(values[name]) if name in values else '');editor.setPlaceholderText('Not set')
                editor.setToolTip(f'Allowed: {low:g} to {high:g}');editor.textChanged.connect(lambda *_:self._invalidate_preview())
                self.form.addRow(name,editor);self.field_editors[name]=editor
        else:self.selection_label.setText('Select an object')
        self.preview_details.clear();self._controls();self._publish_viewport()

    def open_viewport(self,probe_directory=None):
        self._require_editable()
        candidates=(self.executable.with_name('aibs_creator_viewport.exe'),Path(__file__).resolve().parents[2]/'engine/out/windows-msvc/Debug/aibs_creator_viewport.exe')
        executable=next((p for p in candidates if p.is_file()),candidates[0])
        head=self.client.head;first_boot=any(field[0]=='firstboot.kind' for field in self.definition.fields)
        self.viewport.start(executable,head.scope,head.head_revision,head.checkpoint_id,self.rows,first_boot,probe_directory)
        self._controls()

    def _publish_viewport(self):
        if self.viewport.state not in ('ready','starting') or not self.loaded or self.busy:return
        if self._snapshot_tag!=self._tag(self.client.head):return
        first_boot=any(field[0]=='firstboot.kind' for field in self.definition.fields)
        self._run(lambda:self.viewport.publish(self.client.head.scope,self.client.head.head_revision,self.client.head.checkpoint_id,self.rows,first_boot,self.selected_id))

    def _viewport_selected(self,identity,scope):
        if not self.loaded or self.busy or not self.client.head or self._snapshot_tag!=self._tag(self.client.head):return
        if scope!=self.client.head.scope:return
        if not self.viewport._tag or (self.viewport._tag[1],self.viewport._tag[2],self.viewport._tag[3])!=self._snapshot_tag:return
        if identity is None:self.outliner.setCurrentItem(None)
        else:self.select_entity(identity,scope)

    def _viewport_closed(self):
        self._controls()
        if self._closing_project:self._stop_owner()

    def _stop_owner(self):
        if self.client.state=='closed':self._closed('Project closed')
        else:self.client.stop()

    def select_entity(self,persistent_id,scope=None):
        if scope is not None and (not self.client.head or scope!=self.client.head.scope):return False
        for index in range(self.outliner.topLevelItemCount()):
            item=self.outliner.topLevelItem(index)
            if item.data(0,Qt.ItemDataRole.UserRole)==persistent_id:self.outliner.setCurrentItem(item);return True
        return False

    def _defaults(self):
        return tuple((name,1. if name.startswith('half_') and low<=1<=high else max(low,min(0.,high))) for name,low,high in self.schemas)

    def add_node(self,alias,name):
        self._require_editable();identifier=str(uuid.uuid4())
        tx=Transaction(str(uuid.uuid4()),self.client.head.head_revision,'Created '+name,(Create(alias,name,identifier,self._defaults()),))
        return self.submit_transaction(tx,select_after=identifier)

    def delete_selected(self):
        self._require_editable();row=next((r for r in self.rows if r.uuid==self.selected_id),None)
        if row is None:raise ProjectError('Select an object first')
        return self.submit_transaction(Transaction(str(uuid.uuid4()),self.client.head.head_revision,'Deleted '+row.name,(Erase(row.alias,row.uuid),)))

    def submit_transaction(self,transaction,select_after=None):
        self._require_editable();self._invalidate_preview()
        payload=encode_edit(EditRequest(self.client.head.scope,transaction))
        self.busy=True;self._controls()
        return self._send('auto_preview',Opcode.PREVIEW,payload,transaction.revision,select_after)

    def preview_selected(self):
        self._require_editable();self._invalidate_preview()
        row=next((r for r in self.rows if r.uuid==self.selected_id),None)
        if row is None:raise ProjectError('Select an object first')
        existing=dict(row.fields);edits=[]
        for name,low,high in self.schemas:
            text=self.field_editors[name].text().strip()
            if not text and name not in existing:continue
            try:value=float(text)
            except ValueError as error:raise ProjectError('Enter a number for '+name) from error
            if not math.isfinite(value) or not low<=value<=high:raise ProjectError('Value is outside the allowed range: '+name)
            if name not in existing or struct.pack('<d',value)!=struct.pack('<d',existing[name]):edits.append(SetField(row.alias,name,value,row.uuid))
        if not edits:raise ProjectError('No numeric fields changed')
        tx=Transaction(str(uuid.uuid4()),self.client.head.head_revision,'Edited '+row.name,tuple(edits))
        payload=encode_edit(EditRequest(self.client.head.scope,tx));inputs={k:e.text() for k,e in self.field_editors.items()}
        self.busy=True;self._controls();return self._send('preview',Opcode.PREVIEW,payload,tx.revision,(row.uuid,inputs))

    def apply_preview(self):
        self._require_editable()
        if not self._token:raise ProjectError('Preview the change first')
        token=self._token;self._token=None;self.busy=True;self._controls()
        self._send('mutate',Opcode.APPLY_PREPARED,prepared_handle(self.client.head.scope,token),self.client.head.head_revision)

    def _travel(self,redo):
        self._require_editable();self._invalidate_preview();self.busy=True;self._controls()
        self._send('mutate',Opcode.HISTORY,history(self.client.head.scope,str(uuid.uuid4()),redo),self.client.head.head_revision)

    def save_world(self):
        self._require_editable();self._invalidate_preview();self.busy=True;self._controls()
        self._send('save',Opcode.SAVE,scoped(self.client.head.scope),self.client.head.head_revision)

    def close_project(self,discard=False):
        if self.busy or self.client.pending_count:raise ProjectError('Wait for the current world operation before closing')
        if not discard and self.definition and (self.client.dirty or self.client.uncertain_operations):raise ProjectError('Save changes or explicitly discard before closing')
        if discard:
            for record in self.client.uncertain_operations:self.client.acknowledge_recovery(record.generation,record.request_id)
        self._closing_project=True
        self.viewport.stop()
        if self.viewport.state=='closed':self._stop_owner()

    def prepare_close(self,callback=None):
        if self.definition is None and self.client.state=='closed' and self.viewport.state=='closed':return True
        if self._closing_project:return False
        if self.busy or self.client.pending_count:self._close_callback=callback or (lambda:None);return False
        if self.definition and (self.client.dirty or self.client.uncertain_operations):
            buttons=QMessageBox.StandardButton.Discard|QMessageBox.StandardButton.Cancel
            if self.save_button.isEnabled() and not self.client.uncertain_operations:buttons|=QMessageBox.StandardButton.Save
            answer=QMessageBox.question(self,'Close project','This project has unsaved changes or interrupted operations. Save before closing, or explicitly discard them.',buttons,QMessageBox.StandardButton.Cancel)
            if answer==QMessageBox.StandardButton.Cancel:self._close_callback=None;self._save_then_close=False;return False
            if answer==QMessageBox.StandardButton.Save:
                self._close_callback=callback or (lambda:None);self._save_then_close=True;self._run(self.save_world);return False
            discard=True
        else:discard=False
        self._close_callback=callback or (lambda:None);self.close_project(discard=discard);return False

    def _service_close(self):
        if not self._close_callback or self.busy or self.client.pending_count or self._closing_project:return
        callback=self._close_callback;self._close_callback=None
        if getattr(self,'_save_then_close',False) and not self.client.dirty:
            self._save_then_close=False;self._close_callback=callback;self.close_project()
        else:self.prepare_close(callback)

    def _failed(self,identity,message):
        self._tasks.pop(identity,None);self.busy=False;self.loaded=False;self.status.setText(message);self._controls()

    def _closed(self,reason):
        self.busy=False;self.loaded=False;self._tasks.clear();self._token=None;self._deferred_releases.clear()
        if self._closing_project:
            self.definition=None;self.rows=();self.selected_id=None;self.outliner.clear();self._selection_changed();self.address.setText('No project selected')
            self._closing_project=False;callback=self._close_callback;self._close_callback=None
            self.status.setText('Project closed');self._controls()
            if callback:callback()
        else:
            self.viewport.stop()
            self.status.setText(reason+f' · interrupted operations retained: {len(self.client.uncertain_operations)}');self._controls()
            self._service_close()

    def closeEvent(self,event):
        if self.definition is not None or self.client.state!='closed':
            event.ignore();self.prepare_close(self.close)
        else:super().closeEvent(event)
