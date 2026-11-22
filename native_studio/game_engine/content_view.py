"""Typed First Boot chapter authoring, separate from numeric world projects.

Published rows and immutable chapter exports come from the native chapter owner.
Owned native viewport and Play clients use pinned snapshots and verified asset
dependencies. This view never opens gameplay saves.
"""
from dataclasses import dataclass, replace
from pathlib import Path
from native_studio.responsive_layout import FlowLayout
import json
import math
import os
import struct
import tempfile
import uuid

from PyQt6.QtCore import Qt,QTimer
from PyQt6.QtWidgets import (QCheckBox, QLineEdit, QPlainTextEdit, QTreeWidgetItem,
    QLabel, QPushButton, QComboBox, QGroupBox, QVBoxLayout, QHBoxLayout, QFileDialog, QInputDialog, QWidget)

from .creator_view import CreatorView
from .creator_wire import Opcode
from .creator_commands import Status, scoped, prepared_handle
from .content_client import ContentClient
from .opening_project import OpeningProjectClient
from .content_commands import (open_document, snapshot_page, decode_description,
    decode_page, decode_preview, encode_scoped_edit, edit_command, history,
    SetField, CreateFixture, EraseFixture, CreateAssetPlacement, EraseAssetPlacement, decode_scoped_edit,
    CreateMemoryBinding, EraseMemoryBinding, export_content, decode_content_export)
from .content_proposals import MEMORY_AUDIO_REFERENCE_FIELDS
from .opening_fields import (INSPECTION_CAPABILITY,INITIAL_VIEW_CAPABILITY,INSPECTION_FIELDS,
    fixture_inspection_fields,validate_inspection_state,validate_inspection_edits,authored_inspections_from_rows,initial_view_authored_from_rows)
from .workshop_fields import (WORKSHOP_CAPABILITY,WORKSHOP_BINDING_FIELD,WORKSHOP_ROLE_FIELD,
    WORKSHOP_ACTIONS,WORKSHOP_LABELS,encode_workshop_binding,workshop_bindings_from_rows,
    opening_workshop_authored_from_rows,validate_workshop_edits,edits_require_workshop,
    edits_publish_workshop,require_workshop_host,WorkshopSaveGuard,workshop_default_centers)
from .sheltered_hub_fields import (SHELTERED_HUB_CAPABILITY, WRITING_DESK_TYPE,
    MEMORY_SHELVES_TYPE, SHARED_PLAY_TYPE, STATION_TYPES, SPATIAL_ZONES, ZONE_BOUNDS,
    validate_writing_desk, validate_memory_shelves, validate_shared_play, find_spatial_zone)
from .content_jobs import ContentProposalJobs
from .content_ai import ContentAIClient, LocalModel
from .content_preview import ContentViewportClient, ContentExportAssembly
from .content_play import ContentPlayClient
from .saved_play import SavedChapterPlayClient
from .saved_chapter_export import SavedChapterExportClient, hash_saved_journal
from .project_model import ProjectError, _text, _pairs, LIMIT
from .project_assets import (AssetDependency, ProjectAssetClient, ASSET_REFERENCE_FIELDS,
    dependencies_from_rows, validate_asset_profile)
from native_studio.game_build_monitor import read_native_player_capabilities
from native_studio.theme import PALETTE

CHAPTER_METADATA = '.aibs-chapter-project.json'
_COMPLETE_EXPORT_CAPABILITY = 'chapter-content-export-v2'
_SAVED_PLAY_CAPABILITY = 'chapter-saved-play-v1'
_COMPANION_MODEL_FIELDS = frozenset(('model_bound','model_asset_id','model_asset_sha256','model_pack_sha256'))
_MEMORY_CAPABILITY='chapter-memory-audio-v1'


@dataclass(frozen=True)
class ChapterProjectDefinition:
    directory: Path
    project: str
    branch: str
    asset_profile: str = 'legacy_v1'
    opening_workshop: bool = False

    def __post_init__(self):
        if type(self.opening_workshop)is not bool or self.opening_workshop and self.asset_profile!='warm-beginning':
            raise ProjectError('Workshop project metadata requires a typed boolean and Warm Beginning profile')

    @property
    def path(self):
        return self.directory / CHAPTER_METADATA

    @classmethod
    def create(cls, directory, project, branch='main', *, asset_profile='legacy_v1'):
        validate_asset_profile(asset_profile)
        try:
            root = Path(directory).resolve(strict=True)
            if not root.is_dir():
                raise ProjectError('Select an existing chapter project directory')
            target, world = root / CHAPTER_METADATA, root / 'chapter.aiba'
            if target.exists() or target.is_symlink() or world.exists() or world.is_symlink():
                raise ProjectError('Chapter metadata or document already exists; open the existing chapter')
            result = cls(root, _text(project), _text(branch), asset_profile)
            metadata={'version':1,'project':result.project,'branch':result.branch}
            if asset_profile!='legacy_v1':metadata.update(version=2,asset_profile=asset_profile)
            data = (json.dumps(metadata, ensure_ascii=False, indent=2) + '\n').encode('utf-8')
            if len(data) > LIMIT:
                raise ProjectError('Chapter definition exceeds 64 KiB')
            fd, name = tempfile.mkstemp(prefix='.aibs-chapter-', suffix='.tmp', dir=root)
            temporary = Path(name)
            try:
                with os.fdopen(fd, 'wb') as stream:
                    stream.write(data)
                    stream.flush()
                    os.fsync(stream.fileno())
                # Publish exclusively, never replacing existing project metadata.
                os.link(temporary, target)
            finally:
                temporary.unlink(missing_ok=True)
            return result
        except (OSError, UnicodeError) as error:
            raise ProjectError('Could not create chapter definition: ' + str(error)) from error

    @classmethod
    def load(cls, directory):
        try:
            root = Path(directory).resolve(strict=True)
            target = root / CHAPTER_METADATA
            if not root.is_dir() or target.is_symlink() or target.resolve().parent != root:
                raise ProjectError('Invalid chapter metadata path')
            with target.open('rb') as stream:
                data = stream.read(LIMIT + 1)
            if len(data) > LIMIT:
                raise ProjectError('Chapter definition exceeds 64 KiB')
            value = json.loads(data.decode('utf-8-sig'), object_pairs_hook=_pairs)
            if type(value) is not dict or type(value.get('version')) is not int:
                raise ProjectError('Unsupported chapter project definition')
            if value['version']==1 and set(value)=={'version','project','branch'}:profile='legacy_v1'
            elif value['version']==2 and set(value)=={'version','project','branch','asset_profile'}:
                profile=validate_asset_profile(value['asset_profile'])
            elif (value['version']==3 and set(value)=={'version','project','branch','asset_profile','opening_workshop'}
                    and type(value['opening_workshop'])is bool and value['opening_workshop']is True
                    and value['asset_profile']=='warm-beginning'):
                profile='warm-beginning'
            else:raise ProjectError('Unsupported chapter project definition')
            return cls(root, _text(value['project']), _text(value['branch']),profile,value['version']==3)
        except (OSError, UnicodeError, json.JSONDecodeError) as error:
            raise ProjectError('Could not read chapter definition: ' + str(error)) from error


class ContentView(CreatorView):
    """Chapter UI sharing the proven owned-process/close lifecycle with Creator."""

    def __init__(self, executable, parent=None, *, ai_client=None, asset_cooker=None, sample_asset_pack=None, opening_factory=None, opening_assets_root=None):
        self._saved_exporting=False
        self._saved_cancel_requested=False
        self._saved_owner_definition=None
        self._saved_status_message='Play a saved chapter. Gameplay progress is retained in its own save slot.'
        self._deferred_owner_close=None
        self._opening_context=None
        self._opening_close_requested=False
        self._opening_close_callback=None
        self._opening_last_message='Create a new curated chapter; existing projects are preserved.'
        self.description = None
        self._content_snapshot = None
        self._export = None
        self._export_action = None
        self._ai_job_id = None
        self._ai_pin = None
        self._ai_preview_request = None
        self._ai_preview_summary = ''
        self._ai_preview_provenance = ''
        self._ai_prepared_token = None
        self.asset_cooker = Path(asset_cooker) if asset_cooker is not None else None
        self.adopted_asset = None
        self._asset_pack = None
        self._asset_context = None
        self._inspected_asset=None;self._adopt_expected=None
        self.sample_asset_pack=Path(sample_asset_pack) if sample_asset_pack is not None else None
        self._sample_adopt_pending=False
        self._prepared_placement_id = None
        self._prepared_inspection_inputs = None
        self._workshop_history_seen=False
        self._workshop_preview_requests=set()
        self._workshop_prepared_tokens=set()
        self._workshop_mutation_requests=set()
        self._prepared_workshop_inputs=None
        self._workshop_save_guard=None
        super().__init__(executable, parent)
        old = self.client
        old.ready.disconnect(self._transport_ready)
        old.response.disconnect(self._response)
        old.request_failed.disconnect(self._failed)
        old.closed.disconnect(self._closed)
        old.deleteLater()
        self.client = ContentClient(self)
        self.client.ready.connect(self._transport_ready)
        self.client.response.connect(self._response)
        self.client.request_failed.connect(self._failed)
        self.client.closed.connect(self._closed)
        old_viewport = self.viewport
        old_viewport.selection.disconnect(self._viewport_selected)
        old_viewport.closed.disconnect(self._viewport_closed)
        old_viewport.deleteLater()
        self.viewport = ContentViewportClient(self, asset_cooker=self.asset_cooker)
        self.viewport.context_valid=self._export_snapshot_matches
        self.viewport.selection.connect(self._viewport_selected)
        self.viewport.message.connect(lambda text: self.status.setText(text))
        self.viewport.closed.connect(self._viewport_closed)
        self.play = ContentPlayClient(self, asset_cooker=self.asset_cooker)
        self.play.closed.connect(self._play_closed)
        self.play.state_changed.connect(lambda *_: self._controls())
        self.play.message.connect(lambda text: self.status.setText(text))
        self.saved_play = SavedChapterPlayClient(self, asset_cooker=self.asset_cooker)
        self.saved_play.closed.connect(self._saved_play_closed)
        self.saved_play.state_changed.connect(lambda *_: self._controls())
        self.saved_play.message.connect(self._saved_play_message)
        self.saved_export = SavedChapterExportClient(self)
        self.saved_export.completed.connect(self._saved_export_completed)
        self.saved_export.failed.connect(self._saved_export_failed)
        self.saved_export.closed.connect(self._saved_export_closed)
        self.saved_export.message.connect(self._saved_play_message)
        self.saved_export.state_changed.connect(lambda *_: self._controls())
        self.proposal_jobs = ContentProposalJobs(self.client, self.current_proposal_context)
        self.layout().itemAt(0).widget().setText('AI-BS Creator — First Boot Chapter')
        subtitle = self.layout().itemAt(1).widget()
        subtitle.setText('Typed chapter authoring · native 3D preview · isolated native Play from an immutable snapshot.')
        subtitle.setWordWrap(True)
        self.outliner.setHeaderLabels(['Object', 'Type', 'Persistent UUID'])
        self.alias_input.hide()
        self.name_input.setPlaceholderText('New fixture name')
        self.add_button.setText('Add fixture')
        self.delete_button.setText('Delete fixture')
        self.refresh_button.setText('Refresh chapter')
        self.save_button.setText('Save chapter')
        self.viewport_button.setText('Open chapter preview')
        self.stop_viewport_button.setText('Close preview')
        actions = self.layout().itemAt(self.layout().count()-1).layout()
        self.play_button = QPushButton('Play chapter')
        self.stop_play_button = QPushButton('Stop Play')
        actions.addWidget(self.play_button)
        actions.addWidget(self.stop_play_button)
        self.play_button.clicked.connect(lambda: self._run(self.start_play))
        self.stop_play_button.clicked.connect(self.stop_play)
        self.play_status = QLabel('Test this layout. Gameplay changes reset when Play stops; creator edits remain.')
        self.play_status.setWordWrap(True)
        self.layout().addWidget(self.play_status)
        self.saved_play_button = QPushButton('Play saved chapter')
        self.stop_saved_play_button = QPushButton('Stop saved chapter')
        actions.addWidget(self.saved_play_button)
        actions.addWidget(self.stop_saved_play_button)
        self.saved_play_button.clicked.connect(lambda: self._run(self.start_saved_play))
        self.stop_saved_play_button.clicked.connect(self.stop_saved_play)
        self.saved_play_status = QLabel(self._saved_status_message)
        self.saved_play_status.setWordWrap(True)
        self.layout().addWidget(self.saved_play_status)
        self.ai_client = ai_client if ai_client is not None else ContentAIClient(self)
        if self.ai_client.parent() is None:
            self.ai_client.setParent(self)
        if self.ai_client.thread() != self.thread():
            raise ProjectError('The local AI client must belong to the creator Qt thread')
        self._create_ai_panel()
        self.ai_client.inventory_ready.connect(self._ai_inventory_ready)
        self.ai_client.proposal_ready.connect(self._ai_proposal_ready)
        self.ai_client.failed.connect(self._ai_failed)
        self.ai_client.state_changed.connect(lambda *_: self._controls())
        self.asset_client = ProjectAssetClient(self.asset_cooker, self)
        self.asset_client.receipt.connect(self._asset_receipt)
        self.asset_client.failed.connect(lambda error: self.asset_status.setText('Project asset operation failed: ' + error))
        self.asset_client.state_changed.connect(self._controls)
        self.asset_client.closed.connect(self._asset_closed)
        self._create_asset_panel()
        self._create_inspection_panel()
        self._create_workshop_panel()
        self._create_sheltered_hub_panel()
        self.opening_client=OpeningProjectClient(opening_factory,opening_assets_root,self.executable,self)
        self.opening_client.context_valid=self._opening_context_valid
        self.opening_client.completed.connect(self._opening_completed)
        self.opening_client.failed.connect(self._opening_failed)
        self.opening_client.closed.connect(self._opening_closed)
        self.opening_client.message.connect(self.status.setText)
        self.opening_client.state_changed.connect(self._controls)
        self._create_opening_controls()
        self.status.setText('Choose or create a chapter project in an existing folder.'
            if self.executable.is_file() else 'Build the native chapter authoring host before editing.')
        self._controls()

    def _controls(self):
        super()._controls()
        row = next((row for row in self.rows if row.uuid == self.selected_id), None)
        if row is not None and row.type_id=='authoring.CompanionBinding':
            model_bound=self.field_editors.get('model_bound')
            if model_bound is not None:model_bound.setEnabled(False)
        self.delete_button.setText('Delete memory station' if row is not None and row.type_id=='authoring.MemoryBinding'
            else 'Delete placement' if row is not None and row.type_id=='authoring.AssetPlacement' else 'Delete fixture')
        self.delete_button.setEnabled(self.delete_button.isEnabled() and row is not None
            and (row.type_id in ('authoring.Fixture','authoring.AssetPlacement')
                or row.type_id=='authoring.MemoryBinding' and _MEMORY_CAPABILITY in self.client.capabilities))
        usable = self.save_button.isEnabled() and not self._closing_project
        if row is not None and row.type_id=='authoring.Fixture' and not self._inspection_supported():
            for key in INSPECTION_FIELDS:
                editor=self.field_editors.get(key)
                if isinstance(editor,(QLineEdit,QPlainTextEdit)):editor.setReadOnly(True)
                elif editor is not None:editor.setEnabled(False)
        if hasattr(self,'inspection_create_button'):
            self.inspection_create_button.setEnabled(usable and self._inspection_supported())
            self.inspection_create_button.setToolTip('Preview one reading or quiet-seat panel before Apply and Save.'
                if self._inspection_supported() else 'Requires a Warm Beginning chapter and a native host supporting authored inspections.')
        for key in (WORKSHOP_ROLE_FIELD,WORKSHOP_BINDING_FIELD):
            editor=self.field_editors.get(key)
            if isinstance(editor,(QLineEdit,QPlainTextEdit)):editor.setReadOnly(True)
            elif editor is not None:editor.setEnabled(False)
        if hasattr(self,'workshop_create_button'):
            supported=self._workshop_supported()
            for button in (self.workshop_create_button,self.workshop_bind_button,self.workshop_remove_button):
                button.setEnabled(usable and supported)
            for combo in self.workshop_selectors:combo.setEnabled(usable and supported)
            self.workshop_status.setText('Preview a complete group, then Apply and Save. Saved history requires a Workshop-capable Host.'
                if supported else 'Requires Warm Beginning and a native Host supporting Opening Workshop.')
        complete_export = (self.definition is None or self.definition.asset_profile=='legacy_v1'
            or _COMPLETE_EXPORT_CAPABILITY in self.client.capabilities)
        self.viewport_button.setEnabled(usable and complete_export and self.viewport.state == 'closed')
        self.viewport_button.setToolTip('' if complete_export else 'Upgrade the native chapter owner to export every model and audio dependency before Preview or Play.')
        self.stop_viewport_button.setEnabled(self.viewport.state not in ('closed', 'stopping'))
        if hasattr(self, 'play_button'):
            self.play_button.setEnabled(usable and complete_export and self.play.state == 'closed' and not self._saved_children_active() and self._play_binary() is not None)
            self.play_button.setToolTip('' if complete_export else 'Upgrade the native chapter owner to export every model and audio dependency before Preview or Play.')
            self.stop_play_button.setEnabled(self.play.state in ('staging','starting', 'ready'))
            self._update_play_label()
        if hasattr(self, 'saved_play_button'):
            self.saved_play_button.setEnabled(self._saved_launch_available())
            self.saved_play_button.setToolTip('Save the current chapter, then play with retained gameplay progress. Requires a saved-play capable native player.')
            self.stop_saved_play_button.setEnabled(self._saved_exporting or self.saved_export.busy
                or self.saved_play.state in ('staging','starting','ready'))
            self._update_saved_play_label()
        if hasattr(self, 'ai_generate_button'):
            model = self.ai_model_combo.currentData()
            available = not self.ai_client.busy and not self._closing_project and self._close_callback is None
            self.ai_refresh_button.setEnabled(available)
            self.ai_model_combo.setEnabled(available)
            self.ai_prompt.setEnabled(available)
            self.ai_generate_button.setEnabled(usable and available and row is not None
                and isinstance(model, LocalModel) and bool(self.ai_prompt.toPlainText().strip()))
            self.ai_cancel_button.setEnabled(self.ai_client.busy or self._ai_job_id is not None)
        if hasattr(self, 'asset_client'):
            capability='chapter-assets-v2' if self.definition is not None and self.definition.asset_profile=='warm-beginning' else 'chapter-assets-v1'
            asset_ready = usable and not self.asset_client.busy and self.asset_cooker is not None and self.asset_cooker.is_file() and capability in self.client.capabilities
            self.asset_open_button.setEnabled(asset_ready)
            self.asset_adopt_button.setEnabled(asset_ready and self._asset_pack is not None and self._inspected_asset is not None)
            kind = self._adopted_asset_kind()
            self.asset_place_button.setEnabled(asset_ready and kind in ('mesh','surface'))
            self.asset_adam_button.setEnabled(asset_ready and kind=='character' and
                self.definition.asset_profile=='warm-beginning' and
                'chapter-character-assets-v1' in self.client.capabilities and
                sum(row.type_id=='authoring.CompanionBinding' for row in self.rows)==1)
            memory_ready=(asset_ready and kind=='audio' and self.definition.asset_profile=='warm-beginning'
                and _MEMORY_CAPABILITY in self.client.capabilities)
            self.asset_memory_create_button.setEnabled(memory_ready and sum(row.type_id=='authoring.MemoryBinding' for row in self.rows)<8)
            self.asset_memory_assign_button.setEnabled(memory_ready and row is not None and row.type_id=='authoring.MemoryBinding')
            if self.sample_asset_button is not None:self.sample_asset_button.setEnabled(asset_ready)
        self._opening_controls()

    def _create_opening_controls(self):
        self.opening_create_button=QPushButton('Create First Boot opening')
        self.opening_cancel_button=QPushButton('Cancel opening creation')
        self.layout().itemAt(2).layout().addWidget(self.opening_create_button)
        self.layout().itemAt(2).layout().addWidget(self.opening_cancel_button)
        self.opening_status=QLabel();self.opening_status.setWordWrap(True);self.layout().addWidget(self.opening_status)
        self.opening_create_button.clicked.connect(lambda:self._run(self._choose_opening))
        self.opening_cancel_button.clicked.connect(self.opening_client.stop)

    def _opening_controls(self):
        if not hasattr(self,'opening_create_button'):return
        job=self.opening_client;busy=job.busy
        eligible=(self.definition is None and self.client.state=='closed' and self.viewport.state=='closed'
            and self.play.state=='closed' and not self._saved_children_active() and not self._closing_project and not self._opening_close_requested)
        reason=job.availability_error or ('Close the current chapter before creating a separate opening.'if not eligible else self._opening_last_message)
        self.opening_create_button.setEnabled(eligible and not busy and not job.availability_error)
        self.opening_create_button.setToolTip(reason)
        self.opening_cancel_button.setEnabled(busy and job.state!='cancelling')
        self.opening_status.setText('Opening creation: '+job.state if busy else reason)
        if busy:
            for button in(self.new_button,self.open_button,self.close_button,self.add_button,self.delete_button,
                self.preview_button,self.apply_button,self.save_button,self.refresh_button,self.undo_button,self.redo_button,
                self.viewport_button,self.play_button):button.setEnabled(False)

    def _choose_opening(self):
        self._can_open()
        parent=QFileDialog.getExistingDirectory(self,'Choose the parent folder for a new First Boot opening')
        if not parent:return
        name,accepted=QInputDialog.getText(self,'New opening folder','New child folder name:',text='First Boot opening')
        if not accepted:return
        if not name or name in('.','..')or any(c in name for c in '/\\:\0'):
            raise ProjectError('Enter one new child folder name without a path')
        return self.create_first_boot_opening(Path(parent)/name)

    def _can_open(self):
        if self._saved_children_active():raise ProjectError('Stop the saved chapter and wait for its reader to close first')
        if hasattr(self,'opening_client')and self.opening_client.busy:
            raise ProjectError('Cancel or finish the current opening creation job first')
        return super()._can_open()

    def _opening_context_valid(self):
        return (self._opening_context is not None and self.definition is None
            and self.client.state=='closed' and self.client.generation==self._opening_context
            and not self._closing_project and not self._opening_close_requested and self._close_callback is None)

    def create_first_boot_opening(self,output):
        self._can_open()
        self._opening_context=self.client.generation
        try:return self.opening_client.start(output)
        except Exception:
            self._opening_context=None;self._controls();raise

    def _opening_completed(self,result):
        if not self._opening_context_valid():
            self._opening_last_message='Opening was created at '+str(result.directory)+'; workspace changed, so it was not opened.'
            self._controls();return
        try:
            definition=ChapterProjectDefinition.load(result.directory)
            if not definition.opening_workshop:raise ProjectError('Generated opening is missing its Workshop project contract')
            self._opening_context=None
            self._opening_last_message='Created a separate First Boot opening at '+str(result.directory)
            self._open(definition,False)
        except Exception as error:self._opening_failed(str(error))

    def _opening_failed(self,error):
        self._opening_last_message='Opening creation failed: '+str(error)
        self.status.setText(self._opening_last_message);self._controls()

    def _opening_closed(self):
        self._opening_context=None
        self._controls()
        if self._opening_close_requested:
            callback=self._opening_close_callback;self._opening_close_callback=None;self._opening_close_requested=False
            if callback:QTimer.singleShot(0,callback)

    def _workshop_supported(self):
        return (self.definition is not None and self.definition.asset_profile=='warm-beginning'
            and WORKSHOP_CAPABILITY in self.client.capabilities)

    def _require_workshop_support(self):
        if not self._workshop_supported():
            raise ProjectError('Opening Workshop requires Warm Beginning and an upgraded native Host')

    def _create_workshop_panel(self):
        panel=QGroupBox('Opening Workshop — probe, sample, test and claim')
        panel.setCheckable(True);panel.setChecked(False)
        outer=QVBoxLayout(panel);body=QWidget();box=QVBoxLayout(body);outer.addWidget(body)
        body.setVisible(False);panel.toggled.connect(body.setVisible)
        self.workshop_status=QLabel();self.workshop_status.setWordWrap(True);box.addWidget(self.workshop_status)
        self.workshop_selectors=[]
        for label in WORKSHOP_LABELS:
            line=QHBoxLayout();line.addWidget(QLabel(label));combo=QComboBox();combo.addItem('Select an owned fixture',None)
            combo.currentIndexChanged.connect(lambda *_:self._invalidate_preview())
            line.addWidget(combo);box.addLayout(line);self.workshop_selectors.append(combo)
        line=FlowLayout()
        self.workshop_create_button=QPushButton('Preview five new fixtures')
        self.workshop_bind_button=QPushButton('Preview bindings')
        self.workshop_remove_button=QPushButton('Preview remove workflow')
        for button in (self.workshop_create_button,self.workshop_bind_button,self.workshop_remove_button):line.addWidget(button)
        box.addLayout(line)
        self.workshop_create_button.clicked.connect(lambda:self._run(self.preview_workshop_create))
        self.workshop_bind_button.clicked.connect(lambda:self._run(lambda:self.preview_workshop_bindings(self._workshop_inputs())))
        self.workshop_remove_button.clicked.connect(lambda:self._run(self.preview_workshop_remove))
        self.layout().addWidget(panel)

    def _workshop_inputs(self):
        return tuple(combo.currentData() for combo in self.workshop_selectors)

    def _refresh_workshop_selectors(self):
        if not hasattr(self,'workshop_selectors'):return
        current=workshop_bindings_from_rows(self.rows,self.definition.asset_profile)
        choices=[row for row in self.rows if row.type_id=='authoring.Fixture'
            and dict(row.fields).get('selectable')is True and not any(fixture_inspection_fields(row).values())]
        for index,combo in enumerate(self.workshop_selectors):
            previous=combo.currentData();selected=current[index] if current else previous
            combo.blockSignals(True);combo.clear();combo.addItem('Select an owned fixture',None)
            for row in choices:combo.addItem(row.name+' · '+row.uuid,row.uuid)
            combo.setCurrentIndex(max(0,combo.findData(selected)));combo.blockSignals(False)

    def _workshop_settings(self):
        settings=[row for row in self.rows if row.type_id=='authoring.ChapterSettings']
        if len(settings)!=1:raise ProjectError('Workshop requires one owned chapter settings record')
        return settings[0]

    def _preview_workshop_group(self,edits,label):
        self._require_editable();self._require_workshop_support()
        packet=self._encode_edits(tuple(edits),label)
        return self._submit_packet(packet,apply_after_preview=False,workshop_preview=True)

    def preview_workshop_bindings(self,identities):
        self._require_editable();self._require_workshop_support()
        identities=tuple(identities)
        binding=encode_workshop_binding(identities)
        old=workshop_bindings_from_rows(self.rows,self.definition.asset_profile)
        edits=[SetField(identity,WORKSHOP_ROLE_FIELD,False)for identity in old if identity not in identities]
        edits.extend(SetField(identity,WORKSHOP_ROLE_FIELD,True)for identity in identities)
        edits.append(SetField(self._workshop_settings().uuid,WORKSHOP_BINDING_FIELD,binding))
        return self._preview_workshop_group(edits,'Bound the five Opening Workshop actions')

    def preview_workshop_create(self):
        self._require_editable();self._require_workshop_support()
        old=workshop_bindings_from_rows(self.rows,self.definition.asset_profile)
        identities=tuple(str(uuid.uuid4())for _ in WORKSHOP_ACTIONS)
        edits=[SetField(identity,WORKSHOP_ROLE_FIELD,False)for identity in old]
        # Factory-relative current anchors put acquisition/testing in Jenison and
        # the workbench in shelter. Native Preview checks actual walkability/LOS.
        centers=workshop_default_centers(self.rows)
        for index,(identity,label,center)in enumerate(zip(identities,WORKSHOP_LABELS,centers)):
            color=(.25,.6,.4)if index==4 else(.26,.48,.58)
            edits.extend((CreateFixture(identity,label,center=center,half_extent=(.16,.16,.16),color=color,emission=.02),SetField(identity,WORKSHOP_ROLE_FIELD,True)))
        edits.append(SetField(self._workshop_settings().uuid,WORKSHOP_BINDING_FIELD,encode_workshop_binding(identities)))
        return self._preview_workshop_group(edits,'Created five Opening Workshop fixtures')

    def preview_workshop_remove(self):
        self._require_editable();self._require_workshop_support()
        old=workshop_bindings_from_rows(self.rows,self.definition.asset_profile)
        if not old:raise ProjectError('This chapter has no Opening Workshop binding')
        edits=[SetField(identity,WORKSHOP_ROLE_FIELD,False)for identity in old]
        edits.append(SetField(self._workshop_settings().uuid,WORKSHOP_BINDING_FIELD,''))
        return self._preview_workshop_group(edits,'Removed Opening Workshop bindings; saved history remains compatible')

    def _inspection_supported(self):
        return (self.definition is not None and self.definition.asset_profile=='warm-beginning'
            and INSPECTION_CAPABILITY in self.client.capabilities)

    def _require_inspection_support(self):
        if not self._inspection_supported():
            raise ProjectError('Authored inspection panels require a Warm Beginning chapter and an upgraded native owner')

    def _create_inspection_panel(self):
        panel=QGroupBox('Create a reading or quiet-seat panel')
        panel.setCheckable(True);panel.setChecked(False)
        outer=QVBoxLayout(panel);body=QWidget();box=QVBoxLayout(body);outer.addWidget(body)
        body.setVisible(False);panel.toggled.connect(body.setVisible)
        label=QLabel('Use the new fixture name above as the title. Keep the source reference with the authored text; reading and quiet seats award no progress.')
        label.setWordWrap(True);box.addWidget(label)
        self.inspection_text_input=QPlainTextEdit()
        self.inspection_text_input.setPlaceholderText('Authored inspection text (up to 2,048 UTF-8 bytes)')
        self.inspection_text_input.setMaximumHeight(90);box.addWidget(self.inspection_text_input)
        self.inspection_source_input=QLineEdit()
        self.inspection_source_input.setPlaceholderText('Source / provenance (up to 512 UTF-8 bytes)')
        box.addWidget(self.inspection_source_input)
        line=QHBoxLayout();self.inspection_action_combo=QComboBox()
        self.inspection_action_combo.addItem('Read','read');self.inspection_action_combo.addItem('Quiet seat','seat')
        line.addWidget(self.inspection_action_combo)
        self.inspection_create_button=QPushButton('Preview new inspection panel');line.addWidget(self.inspection_create_button);box.addLayout(line)
        self.inspection_create_button.clicked.connect(lambda:self._run(lambda:self.preview_inspection_fixture(
            self.name_input.text(),self.inspection_text_input.toPlainText(),self.inspection_source_input.text(),self.inspection_action_combo.currentData())))
        for widget in (self.name_input,self.inspection_source_input):widget.textChanged.connect(lambda *_:self._invalidate_preview())
        self.inspection_text_input.textChanged.connect(lambda:self._invalidate_preview())
        self.inspection_action_combo.currentIndexChanged.connect(lambda *_:self._invalidate_preview())
        self.layout().addWidget(panel)

    def _inspection_creation_inputs(self):
        return (self.name_input.text(),self.inspection_text_input.toPlainText(),
            self.inspection_source_input.text(),self.inspection_action_combo.currentData())

    def preview_inspection_fixture(self,name,text,source,action='read',center=(-35.,.4,10.)):
        self._require_editable();self._require_inspection_support()
        values=dict(zip(INSPECTION_FIELDS,(text,source,action)))
        validate_inspection_state(name,values)
        if not text:raise ProjectError('A new inspection panel needs text, source and an interaction')
        identity=str(uuid.uuid4())
        edits=(CreateFixture(identity,name,center=tuple(center)),)+tuple(SetField(identity,key,values[key])for key in INSPECTION_FIELDS)
        return self._submit_packet(self._encode_edits(edits,'Created inspection panel '+name),
            select_after=identity,apply_after_preview=False,placement_preview=True,inspection_inputs=self._inspection_creation_inputs())

    def _create_sheltered_hub_panel(self):
        panel = QGroupBox('Sheltered Hub & Pencil Room — Stations & Spatial Audio Triggers')
        panel.setCheckable(True)
        panel.setChecked(False)
        outer = QVBoxLayout(panel)
        body = QWidget()
        box = QVBoxLayout(body)
        outer.addWidget(body)
        body.setVisible(False)
        panel.toggled.connect(body.setVisible)

        station_header = QLabel('Station Placement & Viewport Ingestion:')
        box.addWidget(station_header)

        station_row = QHBoxLayout()
        station_row.addWidget(QLabel('Station:'))
        self.station_combo = QComboBox()
        self.station_combo.addItem('Writing Desk (Pencil Room: [-35.0, 0.4, 18.0])', WRITING_DESK_TYPE)
        self.station_combo.addItem('Memory Shelves (Sheltered Hub: [-38.0, 1.2, 8.5])', MEMORY_SHELVES_TYPE)
        self.station_combo.addItem('Shared Play Corner (Sheltered Hub: [-32.0, 0.2, 11.0])', SHARED_PLAY_TYPE)
        station_row.addWidget(self.station_combo)

        self.station_preview_button = QPushButton('Preview station in viewport')
        self.station_preview_button.clicked.connect(lambda: self._run(lambda: self.preview_sheltered_station(self.station_combo.currentData())))
        station_row.addWidget(self.station_preview_button)
        box.addLayout(station_row)

        trigger_header = QLabel('Spatial Narrative Trigger Zones (7 Routes):')
        box.addWidget(trigger_header)

        trigger_row = QHBoxLayout()
        trigger_row.addWidget(QLabel('Zone:'))
        self.trigger_zone_combo = QComboBox()
        for zone in SPATIAL_ZONES:
            bounds = ZONE_BOUNDS[zone]
            self.trigger_zone_combo.addItem(f"{zone} (X: {bounds[0][0]}..{bounds[1][0]}, Z: {bounds[0][2]}..{bounds[1][2]})", zone)
        trigger_row.addWidget(self.trigger_zone_combo)

        self.trigger_inspect_button = QPushButton('Inspect zone bounds')
        self.trigger_inspect_button.clicked.connect(self._inspect_selected_zone)
        trigger_row.addWidget(self.trigger_inspect_button)
        box.addLayout(trigger_row)

        self.sheltered_hub_status = QLabel('Ready to ingest Sheltered Hub stations and spatial trigger zones.')
        self.sheltered_hub_status.setWordWrap(True)
        box.addWidget(self.sheltered_hub_status)

        self.layout().addWidget(panel)

    def _inspect_selected_zone(self):
        zone_id = self.trigger_zone_combo.currentData()
        if zone_id and zone_id in ZONE_BOUNDS:
            bounds = ZONE_BOUNDS[zone_id]
            self.sheltered_hub_status.setText(
                f"Zone '{zone_id}': Min=({bounds[0][0]}, {bounds[0][1]}, {bounds[0][2]}), "
                f"Max=({bounds[1][0]}, {bounds[1][1]}, {bounds[1][2]}). "
                f"Physical motherboard route active."
            )

    def preview_sheltered_station(self, station_type: str):
        self._require_editable()
        identity = str(uuid.uuid4())
        if station_type == WRITING_DESK_TYPE:
            name = 'Writing Desk'
            center = (-35.0, 0.4, 18.0)
            half_extent = (0.6, 0.4, 0.4)
            color = (0.7, 0.5, 0.3)
            fields = {
                'station_type': station_type,
                'pencil_claimed': False,
                'mode': 'record',
                'active_note_id': '',
                'paper_remaining': 10,
                'pos_x': center[0],
                'pos_y': center[1],
                'pos_z': center[2],
            }
        elif station_type == MEMORY_SHELVES_TYPE:
            name = 'Memory Shelves'
            center = (-38.0, 1.2, 8.5)
            half_extent = (0.3, 0.9, 0.8)
            color = (0.5, 0.4, 0.3)
            fields = {
                'station_type': station_type,
                'capacity': 12,
                'secret_revealed': False,
                'placed_count': 0,
                'pos_x': center[0],
                'pos_y': center[1],
                'pos_z': center[2],
            }
        elif station_type == SHARED_PLAY_TYPE:
            name = 'Shared Play Corner'
            center = (-32.0, 0.2, 11.0)
            half_extent = (0.8, 0.2, 0.8)
            color = (0.3, 0.6, 0.5)
            fields = {
                'station_type': station_type,
                'power_restored': False,
                'session_active': False,
                'interaction_count': 0,
                'pos_x': center[0],
                'pos_y': center[1],
                'pos_z': center[2],
            }
        else:
            raise ProjectError(f'Unknown station type: {station_type}')

        edits = [
            CreateFixture(identity, name, center=center, half_extent=half_extent, color=color, emission=0.04)
        ]
        for key, val in fields.items():
            edits.append(SetField(identity, key, val))

        self.sheltered_hub_status.setText(f"Ingested '{name}' at {center} into viewport.")
        return self._submit_packet(
            self._encode_edits(tuple(edits), f'Ingested station {name}'),
            select_after=identity,
            apply_after_preview=False,
            placement_preview=True
        )

    def _create_asset_panel(self):
        panel = QGroupBox('Project assets — parts, Adam and memory recordings')
        box = QVBoxLayout(panel)
        profile_row=QHBoxLayout()
        profile_row.addWidget(QLabel('Profile for new chapters'))
        self.new_profile_combo=QComboBox()
        self.new_profile_combo.addItem('Legacy PC assets','legacy_v1')
        self.new_profile_combo.addItem('Textured PC assets — Warm Beginning','warm-beginning')
        self.new_profile_combo.setToolTip('Applies when creating a new chapter; existing projects retain their saved profile.')
        profile_row.addWidget(self.new_profile_combo);box.addLayout(profile_row)
        buttons = FlowLayout()
        self.asset_open_button = QPushButton('Open asset pack')
        self.asset_adopt_button = QPushButton('Copy asset to project')
        self.asset_place_button = QPushButton('Preview asset placement')
        self.asset_adam_button = QPushButton('Preview Adam model')
        self.asset_memory_create_button=QPushButton('Preview new memory station')
        self.asset_memory_assign_button=QPushButton('Preview recording assignment')
        self.asset_name_input = QLineEdit('Placed asset')
        self.asset_name_input.setPlaceholderText('Placement name')
        for widget in (self.asset_open_button,self.asset_adopt_button,self.asset_name_input,self.asset_place_button,self.asset_adam_button):buttons.addWidget(widget)
        self.sample_asset_button=None
        if self.sample_asset_pack is not None and self.sample_asset_pack.is_dir():
            self.sample_asset_button=QPushButton('Use bundled sample part')
            self.sample_asset_button.clicked.connect(lambda:self._run(self.use_sample_asset))
            buttons.addWidget(self.sample_asset_button)
        box.addLayout(buttons)
        memory_buttons=FlowLayout();memory_buttons.addWidget(self.asset_memory_create_button);memory_buttons.addWidget(self.asset_memory_assign_button);box.addLayout(memory_buttons)
        self.asset_status = QLabel('Choose a cooked pack. Verified dependencies are retained for Undo and Redo; placement requires Apply and Save.')
        self.asset_status.setWordWrap(True);box.addWidget(self.asset_status);self.layout().addWidget(panel)
        self.asset_open_button.clicked.connect(self._choose_asset_pack)
        self.asset_adopt_button.clicked.connect(lambda:self._run(self.adopt_asset_pack))
        self.asset_place_button.clicked.connect(lambda:self._run(lambda:self.preview_asset_placement(self.asset_name_input.text())))
        self.asset_adam_button.clicked.connect(lambda:self._run(self.preview_adam_model))
        self.asset_memory_create_button.clicked.connect(lambda:self._run(lambda:self.preview_memory_station(self.asset_name_input.text())))
        self.asset_memory_assign_button.clicked.connect(lambda:self._run(self.preview_memory_audio))
        self.asset_name_input.textChanged.connect(lambda *_:self._invalidate_preview())

    def _choose_asset_pack(self):
        path=QFileDialog.getExistingDirectory(self,'Choose an owned cooked asset pack')
        if path:self._run(lambda:self.inspect_asset_pack(Path(path)))

    def use_sample_asset(self):
        if self.sample_asset_pack is None:raise ProjectError('No bundled sample part is available')
        return self.inspect_asset_pack(self.sample_asset_pack,adopt_after=True)

    def inspect_asset_pack(self, root, *, adopt_after=False):
        self._require_editable()
        if self._closing_project:raise ProjectError('The project is closing')
        self._invalidate_preview()
        self._asset_pack=Path(root).resolve();self.adopted_asset=None
        self._inspected_asset=None
        self._sample_adopt_pending=adopt_after
        self._asset_context=(self.client.generation,self.definition.directory)
        self.asset_client.inspect_pack(self._asset_pack)

    def adopt_asset_pack(self, root=None):
        self._require_editable()
        if self._closing_project:raise ProjectError('The project is closing')
        self._invalidate_preview()
        root=Path(root).resolve() if root is not None else self._asset_pack
        if root is None:raise ProjectError('Choose a cooked asset pack first')
        self._adopt_expected=(self._inspected_asset['asset_id'],self._inspected_asset['sha256']) if self._inspected_asset is not None and root==self._asset_pack else None
        store=self.definition.directory/'assets/packs'
        for part in (store,*store.parents):
            if part.is_symlink() or part.is_junction():raise ProjectError('Project asset directories must not be redirected')
        store.mkdir(parents=True,exist_ok=True)
        self._asset_context=(self.client.generation,self.definition.directory)
        self.asset_client.adopt_pack(root,store)

    def _asset_receipt(self, mode, value):
        if self._closing_project or self.definition is None or self._asset_context!=(self.client.generation,self.definition.directory):return
        if mode=='inspect':
            if len(value['assets'])!=1:
                self._asset_pack=None;self.asset_status.setText('Choose a single-asset cooked pack for project adoption.');return
            row=value['assets'][0]
            if row.get('kind') in ('surface','character','audio') and self.definition.asset_profile!='warm-beginning':
                self._inspected_asset=None;self._asset_pack=None;self._sample_adopt_pending=False
                self.asset_status.setText('This pack needs a new chapter using the Textured PC assets profile. Existing chapter profiles are preserved.');return
            self._inspected_asset=row
            if row.get('kind')=='audio':
                from .asset_view import AssetView
                self.asset_status.setText(AssetView.audio_summary(row)+'. Copy it to this project, then preview a memory station or recording assignment.')
            else:self.asset_status.setText(f"{row['name']} · Authored character model. Copy to this project, then preview Adam's model."
                if row.get('kind')=='character' else f"{row['name']} · {row['triangles']} triangles · {row['materials']} materials. Copy to this project before placement.")
            if self._sample_adopt_pending:
                self._sample_adopt_pending=False
                self._run(self.adopt_asset_pack)
        elif mode=='adopt':
            if self._adopt_expected is not None and self._adopt_expected!=(value['asset_id'],value['asset_sha256']):
                self.adopted_asset=None;self._inspected_asset=None
                self.asset_status.setText('Asset pack changed since inspection. Inspect it again before placement.');self._controls();return
            self.adopted_asset=AssetDependency(*(value[key] for key in ('asset_id','asset_sha256','pack_sha256')))
            kind=self._adopted_asset_kind()
            self.asset_status.setText('Recording copied to this project. Preview a memory station or assignment, review, then Apply and Save.'
                if kind=='audio' else 'Model copied to this project. Preview Adam model, review, then Apply and Save.'
                if kind=='character' else 'Verified dependency copied to project. Preview placement, review, then Apply and Save.')
        self._controls()

    def _adopted_asset_kind(self):
        row=self._inspected_asset;reference=self.adopted_asset
        if reference is None or not isinstance(row,dict):return None
        if (row.get('asset_id'),row.get('sha256'))!=(reference.asset_id,reference.asset_sha256):return None
        return row.get('kind','mesh')

    def preview_adam_model(self):
        self._require_editable()
        if self.definition is None or self.definition.asset_profile!='warm-beginning':
            raise ProjectError('Adam models require a chapter using the Textured PC assets profile.')
        if 'chapter-character-assets-v1' not in self.client.capabilities:
            raise ProjectError('Upgrade the native chapter owner before assigning an Adam character model.')
        if self._adopted_asset_kind()!='character':
            raise ProjectError('Inspect and copy a verified character model into this project first.')
        bindings=tuple(row for row in self.rows if row.type_id=='authoring.CompanionBinding')
        if len(bindings)!=1:raise ProjectError('This chapter needs exactly one authored Adam companion binding before assigning a model.')
        identity=bindings[0].uuid;reference=self.adopted_asset
        edits=(SetField(identity,'model_bound',True),SetField(identity,'model_asset_id',reference.asset_id),
            SetField(identity,'model_asset_sha256',reference.asset_sha256),SetField(identity,'model_pack_sha256',reference.pack_sha256))
        return self._submit_packet(self._encode_edits(edits,'Assigned Adam character model'),select_after=identity,
            apply_after_preview=False,placement_preview=True)

    def _asset_closed(self):
        self._controls()
        if self._closing_project and self._children_closed():self._stop_owner()
        elif (self._close_callback is not None and self.definition is None and self.client.state=='closed'
              and self._children_closed()):
            callback,self._close_callback=self._close_callback,None;callback()
        elif not self.asset_client.busy:self._service_close()

    def _require_memory_audio(self):
        self._require_editable()
        if self.definition is None or self.definition.asset_profile!='warm-beginning':
            raise ProjectError('Memory recordings require a Warm Beginning chapter.')
        if _MEMORY_CAPABILITY not in self.client.capabilities:
            raise ProjectError('Upgrade the native chapter owner before creating or assigning memory audio.')
        if self._adopted_asset_kind()!='audio':
            raise ProjectError('Inspect and copy one verified audio pack into this project first.')

    def preview_memory_station(self,name='Memory station',position=(-35.,1.,10.)):
        self._require_memory_audio();_text(name)
        if sum(row.type_id=='authoring.MemoryBinding' for row in self.rows)>=8:
            raise ProjectError('This chapter already has the maximum eight memory stations.')
        identity=str(uuid.uuid4());ref=self.adopted_asset
        edit=CreateMemoryBinding(identity,name,ref.asset_id,ref.asset_sha256,ref.pack_sha256,tuple(position))
        return self._submit_packet(self._encode_edits((edit,),'Created optional memory station '+name),select_after=identity,
            apply_after_preview=False,placement_preview=True)

    def preview_memory_audio(self):
        self._require_memory_audio()
        row=next((row for row in self.rows if row.uuid==self.selected_id and row.type_id=='authoring.MemoryBinding'),None)
        if row is None:raise ProjectError('Select the memory station that should use this recording.')
        ref=self.adopted_asset
        edits=(SetField(row.uuid,'audio_asset_id',ref.asset_id),SetField(row.uuid,'audio_asset_sha256',ref.asset_sha256),SetField(row.uuid,'audio_pack_sha256',ref.pack_sha256))
        return self._submit_packet(self._encode_edits(edits,'Assigned verified memory recording'),select_after=row.uuid,
            apply_after_preview=False,placement_preview=True)

    def preview_asset_placement(self,name='Placed asset',center=(-35.,.4,10.),scale=(1.,1.,1.),rotation=(0.,0.,0.,1.),selectable=True):
        self._require_editable()
        if self._adopted_asset_kind() not in ('mesh','surface'):
            raise ProjectError('Choose a verified mesh or surface for placement; use the Adam or memory controls for those assets.')
        capability='chapter-assets-v2' if self.definition is not None and self.definition.asset_profile=='warm-beginning' else 'chapter-assets-v1'
        if capability not in self.client.capabilities:raise ProjectError('This native chapter host does not support the chapter asset profile')
        if self.adopted_asset is None:raise ProjectError('Copy a verified asset into this project first')
        _text(name);identity=str(uuid.uuid4());ref=self.adopted_asset
        edit=CreateAssetPlacement(identity,name,ref.asset_id,ref.asset_sha256,ref.pack_sha256,center,scale,rotation,selectable)
        return self._submit_packet(self._encode_edits((edit,),'Placed asset '+name),select_after=identity,
            apply_after_preview=False,placement_preview=True)

    def _create_ai_panel(self):
        panel = QGroupBox('Local AI authoring — selected object')
        layout = QVBoxLayout(panel)
        capabilities = QLabel('Propose changes to the selected object’s exposed text, number and boolean fields. '
            'Review the native preview, then Apply; Save is separate. Generated wording is a draft, not recovered memories.')
        capabilities.setWordWrap(True)
        layout.addWidget(capabilities)
        models = QHBoxLayout()
        self.ai_refresh_button = QPushButton('Refresh models')
        self.ai_model_combo = QComboBox()
        self.ai_model_combo.setSizeAdjustPolicy(QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon)
        self.ai_model_combo.setMinimumContentsLength(24)
        self.ai_model_combo.addItem('Choose an installed local model', None)
        models.addWidget(self.ai_refresh_button)
        models.addWidget(self.ai_model_combo, 1)
        layout.addLayout(models)
        self.ai_prompt = QPlainTextEdit()
        self.ai_prompt.setStyleSheet(f"QPlainTextEdit {{ background: {PALETTE['bg_dark']}; color: {PALETTE['text']}; border: 1px solid {PALETTE['border']}; padding: 8px; }}")
        self.ai_prompt.setPlaceholderText('Describe a change to the selected object…')
        self.ai_prompt.setMaximumHeight(70)
        layout.addWidget(self.ai_prompt)
        actions = QHBoxLayout()
        self.ai_generate_button = QPushButton('Generate proposal')
        self.ai_cancel_button = QPushButton('Cancel generation')
        actions.addWidget(self.ai_generate_button)
        actions.addWidget(self.ai_cancel_button)
        self.ai_status = QLabel('Refresh to discover installed models on local Ollama endpoints. No downloads are started.')
        self.ai_status.setWordWrap(True)
        actions.addWidget(self.ai_status, 1)
        layout.addLayout(actions)
        self.layout().addWidget(panel)
        self.ai_refresh_button.clicked.connect(lambda: self._run_ai(self.refresh_ai_models))
        self.ai_generate_button.clicked.connect(lambda: self._run_ai(self.generate_ai_proposal))
        self.ai_cancel_button.clicked.connect(lambda: self.cancel_ai_generation())
        self.ai_model_combo.currentIndexChanged.connect(lambda *_: self._controls())
        self.ai_prompt.textChanged.connect(self._controls)

    def _run_ai(self, action):
        try:
            return action()
        except Exception as error:
            self.ai_status.setText('AI authoring: ' + str(error))
            self._controls()
            return None

    def refresh_ai_models(self):
        if self.ai_client.busy:
            raise ProjectError('Cancel the current model request before refreshing')
        self.ai_status.setText('Discovering installed local models…')
        self.ai_client.refresh_models()
        self._controls()

    def _ai_inventory_ready(self, models, diagnostics):
        previous = self.ai_model_combo.currentData()
        self.ai_model_combo.blockSignals(True)
        self.ai_model_combo.clear()
        self.ai_model_combo.addItem('Choose an installed local model', None)
        selected = 0
        for model in models:
            self.ai_model_combo.addItem(f'{model.name} · {model.endpoint}', model)
            if model == previous:
                selected = self.ai_model_combo.count() - 1
        self.ai_model_combo.setCurrentIndex(selected)
        self.ai_model_combo.blockSignals(False)
        message = (f'{len(models)} installed local model(s). Choose a model and describe a selected-object change.'
            if models else 'No installed local models found.')
        if diagnostics:
            message += ' ' + ' · '.join(diagnostics)
        self.ai_status.setText(message)
        self._controls()

    @staticmethod
    def _ai_provenance(pin):
        model = pin['model']
        return f'{model.name} · {model.endpoint} · pinned revision {pin["revision"]} / {pin["fingerprint"][:12]}'

    def generate_ai_proposal(self):
        self._require_editable()
        if self._closing_project or self._close_callback is not None:
            raise ProjectError('The chapter project is closing')
        if self.ai_client.busy or self._ai_job_id is not None:
            raise ProjectError('Cancel the current generation first')
        model = self.ai_model_combo.currentData()
        if not isinstance(model, LocalModel):
            raise ProjectError('Choose an installed local model')
        instruction = self.ai_prompt.toPlainText().strip()
        if not instruction:
            raise ProjectError('Describe the selected-object change first')
        if not any(row.uuid == self.selected_id for row in self.rows):
            raise ProjectError('Select a chapter object first')
        job, prompt = self.proposal_jobs.begin([self.selected_id])
        self._invalidate_preview()
        self._ai_job_id = job
        self._ai_pin = {'selected': self.selected_id, 'inputs': self._editor_inputs(),
            'model': model, 'revision': prompt['context']['revision'],
            'fingerprint': prompt['context']['fingerprint']}
        self.ai_status.setText('Generating proposal: ' + self._ai_provenance(self._ai_pin)
            + '. Authoring may continue; changed context will reject this result.')
        try:
            self.ai_client.generate(job, model, prompt, instruction)
        except Exception:
            self.proposal_jobs.cancel(job)
            self._ai_job_id = self._ai_pin = None
            raise
        finally:
            self._controls()
        return job

    def _ai_proposal_ready(self, job_id, raw_json):
        if job_id != self._ai_job_id or self._ai_pin is None:
            return
        pin = self._ai_pin
        try:
            if (self._closing_project or self._close_callback is not None
                    or pin['selected'] != self.selected_id or pin['inputs'] != self._editor_inputs()):
                raise ProjectError('Authoring job context is stale: selection or inspector inputs changed')
            self._ai_preview_request = self.submit_proposal(job_id, raw_json)
            # submit_proposal has already admitted this JSON against the pinned
            # typed capabilities. Display every proposed delta for Apply review.
            proposal = json.loads(raw_json)
            rows = {row.uuid: row for row in self.rows}
            lines = ['Proposed field changes (not applied):', proposal['label']]
            for edit in proposal['edits']:
                row = rows[edit['entity_id']]
                lines.append(json.dumps({'object': row.name, 'uuid': row.uuid,
                    'field': edit['field'], 'before': dict(row.fields)[edit['field']],
                    'after': edit['value']}, ensure_ascii=False, allow_nan=False))
            self._ai_preview_provenance = self._ai_provenance(pin)
            self._ai_preview_summary = self._ai_preview_provenance + '\n' + '\n'.join(lines)
            self.ai_status.setText('Proposal received: ' + self._ai_provenance(pin)
                + '. Waiting for native preview; review before Apply.')
        except Exception as error:
            self.ai_status.setText('AI proposal rejected: ' + str(error) + ' · ' + self._ai_provenance(pin))
        finally:
            self.proposal_jobs.cancel(job_id)
            self._ai_job_id = self._ai_pin = None
            self._controls()

    def _ai_failed(self, job_id, error):
        if job_id and job_id != self._ai_job_id:
            return
        if self._ai_job_id is not None:
            self.proposal_jobs.cancel(self._ai_job_id)
        self._ai_job_id = self._ai_pin = None
        self.ai_status.setText('AI authoring failed: ' + error)
        self._controls()

    def cancel_ai_generation(self, reason='Generation cancelled; no proposal applied.'):
        if not hasattr(self, 'ai_client'):
            return
        active = self.ai_client.busy or self._ai_job_id is not None
        self.ai_client.cancel()
        if self._ai_job_id is not None:
            self.proposal_jobs.cancel(self._ai_job_id)
        self._ai_job_id = self._ai_pin = None
        if active:
            self.ai_status.setText(reason)
        self._controls()

    def _update_play_label(self):
        if not hasattr(self, 'play_status'):
            return
        if self.play.state != 'closed' and self.play.snapshot:
            snapshot = self.play.snapshot
            changed = (self.client.head is None or self.description is None or
                self.client.generation != snapshot.generation or self.client.head.scope != snapshot.scope or
                self.client.head.head_revision != snapshot.revision or self.description.fingerprint != snapshot.fingerprint)
            self.play_status.setText(f'Play {self.play.state}: pinned revision {snapshot.revision} / {snapshot.fingerprint[:12]} · '
                + ('authoring has changed; restart Play to use current edits. ' if changed else 'matches the current authoring snapshot. ')
                + 'Test gameplay resets when Play stops; creator edits remain.')
        elif self.play.last_result:
            self.play_status.setText(self.play.last_result['reason'])
        else:
            self.play_status.setText('Test this layout. Gameplay changes reset when Play stops; creator edits remain.')

    def _binary_candidates(self, name):
        root = Path(__file__).resolve().parents[2]
        return (self.executable.with_name(name), root/'engine/out/windows-msvc/Debug'/name,
            root/'engine/out/windows-msvc/Release'/name, root/'engine/install/release/bin'/name)

    def _play_binary(self, *, saved=False):
        memories=any(row.type_id=='authoring.MemoryBinding' for row in self.rows)
        inspections=authored_inspections_from_rows(self.rows)
        initial_view=initial_view_authored_from_rows(self.rows,self.definition.asset_profile if self.definition is not None else None)
        workshop=opening_workshop_authored_from_rows(self.rows,self.definition.asset_profile if self.definition is not None else None)
        for path in self._binary_candidates('aibs_motherboard.exe'):
            features=read_native_player_capabilities(path).get('features',{})
            if (features.get('first_boot_content_play') is True
                    and (not saved or features.get(_SAVED_PLAY_CAPABILITY) is True)
                    and (self.definition is None or self.definition.asset_profile=='legacy_v1' or features.get('chapter_asset_surfaces') is True)
                    and (not memories or features.get(_MEMORY_CAPABILITY) is True)
                    and (not inspections or features.get(INSPECTION_CAPABILITY)is True)
                    and (not initial_view or features.get(INITIAL_VIEW_CAPABILITY)is True)
                    and (not workshop or features.get(WORKSHOP_CAPABILITY)is True)):
                return path
        return None

    def _saved_play_binary(self):
        return ContentView._play_binary(self, saved=True)

    def new_project(self, directory, project, branch='main', *, asset_profile=None):
        self._can_open()
        profile=self.new_profile_combo.currentData() if asset_profile is None else validate_asset_profile(asset_profile)
        self._open(ChapterProjectDefinition.create(directory, project, branch,asset_profile=profile), True)

    def open_project(self, directory):
        self._can_open()
        definition = ChapterProjectDefinition.load(directory)
        world = definition.directory / 'chapter.aiba'
        if not world.is_file() or world.is_symlink():
            raise ProjectError('This project has no saved chapter; it will not be silently reinitialized')
        self._open(definition, False)

    def _open(self, definition, create):
        require_workshop_host(self.executable,getattr(definition,'opening_workshop',False))
        self._workshop_history_seen=getattr(definition,'opening_workshop',False)
        self._workshop_preview_requests.clear();self._workshop_prepared_tokens.clear();self._workshop_mutation_requests.clear()
        self._workshop_save_guard=None
        self.client.opening_workshop=self._workshop_history_seen
        self.cancel_ai_generation('Project changed; generation cancelled.')
        self.description = None
        self._content_snapshot = None
        self._export = None
        self._export_action = None
        self.adopted_asset=None;self._asset_pack=None;self._inspected_asset=None;self._adopt_expected=None;self._sample_adopt_pending=False
        self.client.asset_profile=definition.asset_profile
        super()._open(definition, create)

    def _transport_ready(self):
        if self.definition is not None:
            if self.definition.asset_profile=='warm-beginning' and not {'chapter-assets-v2','chapter-content-v3'}<=self.client.capabilities:
                self._failed(None,'This native owner does not support textured chapters');return
            self._run(lambda: self._send('open', Opcode.OPEN, open_document(
                self.definition.project, self.definition.branch, self._create_pending)))

    def _begin_refresh(self, message):
        self._invalidate_preview()
        self.busy = True
        self.loaded = False
        self._refresh_message = message
        self._controls()
        self._send('describe', Opcode.DESCRIBE, scoped(self.client.head.scope),
            self.client.head.head_revision)

    def _request_page(self):
        scope, revision, checkpoint = self._page_tag
        self._send('page', Opcode.SNAPSHOT_PAGE,
            snapshot_page(scope, checkpoint, self._cursor), revision)

    def _send(self,kind,opcode,payload,revision=None,extra=None):
        workshop_token=next((token for token in getattr(self,'_workshop_prepared_tokens',())
            if self.client.head is not None and payload==prepared_handle(self.client.head.scope,token)),None)
        identity=super()._send(kind,opcode,payload,revision,extra)
        if workshop_token and opcode==Opcode.APPLY_PREPARED:
            self._workshop_mutation_requests.add(identity)
            self._workshop_prepared_tokens.discard(workshop_token)
        elif workshop_token and opcode==Opcode.RELEASE_PREPARED:
            self._workshop_prepared_tokens.discard(workshop_token)
        return identity

    def save_world(self):
        self._require_editable()
        current=opening_workshop_authored_from_rows(self.rows,self.definition.asset_profile)
        if current or self._workshop_history_seen or self.definition.opening_workshop:
            self._require_workshop_support()
            self._workshop_save_guard=WorkshopSaveGuard.prepare(self.definition)
            self.definition=replace(self.definition,opening_workshop=True)
            self.client.opening_workshop=True
        try:return super().save_world()
        except Exception:
            # A synchronous send failure still needs exact unchanged-journal proof.
            self._finish_workshop_save(rejected=True)
            raise

    def _finish_workshop_save(self,*,rejected=False):
        guard=getattr(self,'_workshop_save_guard',None)
        self._workshop_save_guard=None
        if rejected and guard is not None and guard.restore_if_uncommitted():
            self.definition=ChapterProjectDefinition.load(self.definition.directory)
            self.client.opening_workshop=self.definition.opening_workshop

    def _response(self, identity, reply):
        if identity in getattr(self,'_workshop_preview_requests',()):
            self._workshop_preview_requests.discard(identity)
            if reply.status==Status.PREPARED and reply.token and reply.save_compatible:
                self._workshop_prepared_tokens.add(reply.token)
        if identity in getattr(self,'_workshop_mutation_requests',()):
            self._workshop_mutation_requests.discard(identity)
            if reply.status in (Status.APPLIED,Status.DUPLICATE):self._workshop_history_seen=True
        if getattr(self,'_tasks',{}).get(identity,(None,None))[0]=='save':
            self._finish_workshop_save(rejected=reply.status==Status.REJECTED)
        ai_preview = identity == self._ai_preview_request
        if ai_preview:
            self._ai_preview_request = None
        task = self._tasks.pop(identity, None)
        if task is not None and task[0] == 'export':
            try:
                if reply.status == Status.REJECTED:
                    raise ProjectError(reply.message)
                self._receive_export(reply)
            except Exception as error:
                self._export = None
                self._export_action = None
                self.busy = False
                self.status.setText(str(error))
                self._controls()
            self._service_close()
            return
        if reply.status in (Status.APPLIED, Status.UNDONE, Status.REDONE, Status.SAVED):
            self._deferred_releases.clear()
        self._flush_releases()
        if task is None:
            if self.loaded and not self.busy and self._snapshot_tag != self._tag(reply):
                self._run(lambda: self._begin_refresh('Chapter updated by another authoring request'))
            self._service_close()
            return
        kind, extra = task
        if kind == 'release':
            self._service_close()
            return
        try:
            if reply.status == Status.REJECTED:
                raise ProjectError(reply.message)
            if kind == 'open':
                self._begin_refresh('Chapter opened')
            elif kind == 'describe':
                self.description = decode_description(reply.body)
                self._page_tag = self._tag(reply)
                self._page_rows, self._page_uuids = [], set()
                self._page_bytes, self._cursor = 0, ''
                self._request_page()
            elif kind == 'page':
                self._receive_page(reply)
            elif kind in ('preview', 'auto_preview','placement_preview','workshop_preview'):
                if reply.status == Status.DUPLICATE:
                    self._begin_refresh('Previously accepted change; no effect repeated')
                    return
                if reply.status != Status.PREPARED or not reply.token:
                    raise ProjectError('No prepared chapter change returned')
                if not reply.save_compatible:
                    self._send('release', Opcode.RELEASE_PREPARED,
                        prepared_handle(reply.scope, reply.token))
                    raise ProjectError('Chapter document cannot be saved: ' + reply.save_message)
                dependencies = decode_preview(reply.body)
                details = self._dependency_text(reply, dependencies)
                if kind == 'auto_preview':
                    self.preview_details.setPlainText(details)
                    self._send('mutate', Opcode.APPLY_PREPARED,
                        prepared_handle(reply.scope, reply.token), reply.head_revision, extra)
                else:
                    selected, inputs = extra[:2]
                    if (selected != self.selected_id or inputs != self._editor_inputs()
                            or kind=='workshop_preview' and extra[2]!=self._workshop_inputs()
                            or kind=='placement_preview' and (extra[3]!=self.adopted_asset or extra[4]!=self.asset_name_input.text()
                                or len(extra)>5 and extra[5]is not None and extra[5]!=self._inspection_creation_inputs())):
                        self._send('release', Opcode.RELEASE_PREPARED,
                            prepared_handle(reply.scope, reply.token))
                        raise ProjectError('Selection or inputs changed; preview again')
                    self._token, self.busy = reply.token, False
                    self._prepared_workshop_inputs=extra[2] if kind=='workshop_preview' else None
                    self._prepared_placement_id=extra[2] if kind=='placement_preview' else None
                    self._prepared_inspection_inputs=extra[5] if kind=='placement_preview' and len(extra)>5 else None
                    self.preview_details.setPlainText(details)
                    if ai_preview:
                        self._ai_prepared_token = reply.token
                        self.preview_details.setPlainText(self._ai_preview_summary + '\n\n' + details)
                        self.ai_status.setText('Native preview ready: ' + self._ai_preview_provenance
                            + '. Review the proposed field changes, then Apply; Save is separate.')
                    self.status.setText('Native preview ready. Apply to publish one grouped change.')
                    self._controls()
            elif kind in ('mutate', 'save'):
                self._selected_after = extra
                self._begin_refresh('Chapter saved' if reply.status == Status.SAVED
                    else 'Chapter change applied; save to keep it')
        except Exception as error:
            if ai_preview:
                self.ai_status.setText('AI proposal rejected by native preview: ' + str(error))
                self._ai_preview_summary = self._ai_preview_provenance = ''
                self._ai_prepared_token = None
            if kind in ('open', 'describe', 'page'):
                self.loaded = False
                self._page_rows = []
            self.busy = False
            self.status.setText(str(error))
            self._controls()
            if kind in ('open', 'describe', 'page', 'save') and self._close_callback:
                self._close_callback, self._save_then_close = None, False
        self._service_close()

    @staticmethod
    def _dependency_text(reply, dependencies):
        yes = lambda value: 'yes' if value else 'no'
        lines = [f'Chapter document save compatible: {yes(reply.save_compatible)}',
            f'Encoded document: {reply.save_bytes:,} bytes', reply.save_message,
            'Existing gameplay saves: ' + ('compatible' if dependencies.gameplay_save_compatible
                else 'new Play branch required'),
            f'Render rebuild: {yes(dependencies.render_rebuild)} · collision rebuild: {yes(dependencies.collision_rebuild)}',
            f'Power dependencies: {yes(dependencies.power_dependencies)} · quest dependencies: {yes(dependencies.quest_dependencies)}',
            'Affected UUIDs: ' + (', '.join(dependencies.affected_ids) or 'none'),
            'Dependencies: ' + (', '.join(dependencies.dependencies) or 'none'),
            'Navigation: ' + dependencies.navigation]
        return '\n'.join(lines)

    def _receive_page(self, reply):
        if self._tag(reply) != self._page_tag:
            raise ProjectError('Chapter snapshot changed during refresh; retry')
        rows, cursor, more = decode_page(reply.body)
        self._page_bytes += len(reply.body)
        if self._page_bytes > 64 * 1024 * 1024 or len(self._page_rows) + len(rows) > 10000:
            raise ProjectError('Chapter view storage limit exceeded')
        previous = self._cursor
        for row in rows:
            if row.uuid in self._page_uuids or row.uuid <= previous:
                raise ProjectError('Duplicate or unordered chapter UUID')
            previous = row.uuid
            self._page_uuids.add(row.uuid)
            self._page_rows.append(row)
        if (rows and cursor != rows[-1].uuid) or (more and (not rows or cursor <= self._cursor)):
            raise ProjectError('Chapter snapshot cursor did not advance')
        self._cursor = cursor
        if more:
            self._request_page()
            return
        # known_count includes reserved/historical identities; only world_count
        # is the count of currently published authoring rows.
        if len(self._page_rows) != reply.world_count:
            raise ProjectError('Chapter row count differs from native snapshot')
        profile=self._validated_asset_profile(self._page_rows)
        initial_view_authored_from_rows(self._page_rows,profile)
        workshop=opening_workshop_authored_from_rows(self._page_rows,profile)
        if workshop and WORKSHOP_CAPABILITY not in self.client.capabilities:raise ProjectError('This chapter requires an upgraded Workshop-capable Host')
        if workshop:self._workshop_history_seen=True
        for row in self._page_rows:
            if row.type_id=='authoring.Fixture':fixture_inspection_fields(row)
        selected = self._selected_after or self.selected_id
        self._selected_after = None
        self.rows = tuple(self._page_rows)
        self._snapshot_tag, self.loaded, self.busy = self._page_tag, True, False
        self.outliner.blockSignals(True)
        self.outliner.clear()
        selected_item = None
        for row in self.rows:
            item = QTreeWidgetItem([row.name, row.type_id, row.uuid])
            item.setData(0, Qt.ItemDataRole.UserRole, row.uuid)
            self.outliner.addTopLevelItem(item)
            if row.uuid == selected:
                selected_item = item
        self.outliner.setCurrentItem(selected_item)
        self.outliner.blockSignals(False)
        self._refresh_workshop_selectors()
        self._selection_changed()
        self.status.setText(f'{self._refresh_message} · revision {reply.head_revision} · '
            + ('unsaved' if self.client.dirty else 'saved'))
        self._controls()
        self.document_changed.emit()
        self._publish_viewport()

    def _selection_changed(self):
        self._invalidate_preview()
        item = self.outliner.currentItem()
        self.selected_id = item.data(0, Qt.ItemDataRole.UserRole) if item else None
        while self.form.rowCount():
            self.form.removeRow(0)
        self.field_editors = {}
        row = next((row for row in self.rows if row.uuid == self.selected_id), None)
        if row is not None:
            self.selection_label.setText(f'{row.name}\n{row.type_id}\n{row.uuid}')
            # The native descriptor exposes authoring fields only: no open,
            # unlocked, completed, or other transient gameplay flags are inferred.
            for name, value in row.fields:
                if row.type_id=='authoring.Fixture' and name=='inspection_action':
                    editor=QComboBox()
                    for label,data in [('Unbound',''),('Read','read'),('Quiet seat','seat')]:editor.addItem(label,data)
                    editor.setCurrentIndex(editor.findData(value));editor.setEnabled(self._inspection_supported())
                    editor.currentIndexChanged.connect(lambda *_:self._invalidate_preview())
                elif type(value) is bool:
                    editor = QCheckBox()
                    editor.setChecked(value)
                    if row.type_id=='authoring.CompanionBinding' and name in _COMPANION_MODEL_FIELDS:editor.setEnabled(False)
                    editor.toggled.connect(lambda *_: self._invalidate_preview())
                elif type(value) is str and ('\n' in value or name.startswith('hint.') or name=='inspection_text'):
                    editor = QPlainTextEdit(value)
                    editor.setMaximumHeight(85)
                    editor.textChanged.connect(lambda: self._invalidate_preview())
                else:
                    editor = QLineEdit(value if type(value) is str else repr(value))
                    if row.type_id=='authoring.AssetPlacement' and name in ASSET_REFERENCE_FIELDS:
                        editor.setReadOnly(True);editor.setCursorPosition(0)
                    if row.type_id=='authoring.CompanionBinding' and name in _COMPANION_MODEL_FIELDS:
                        editor.setReadOnly(True);editor.setCursorPosition(0)
                    if row.type_id=='authoring.MemoryBinding' and name in MEMORY_AUDIO_REFERENCE_FIELDS:
                        editor.setReadOnly(True);editor.setCursorPosition(0)
                    if row.type_id=='authoring.ChapterSettings' and name=='asset_profile':
                        editor.setReadOnly(True);editor.setCursorPosition(0)
                    editor.textChanged.connect(lambda *_: self._invalidate_preview())
                editor.setToolTip('Native authoring type: ' + type(value).__name__)
                if row.type_id=='authoring.AssetPlacement' and name in ASSET_REFERENCE_FIELDS:
                    editor.setToolTip('Immutable verified dependency: '+value)
                if row.type_id=='authoring.CompanionBinding' and name in _COMPANION_MODEL_FIELDS:
                    editor.setToolTip('Use Preview Adam model to assign one verified model, then Apply and Save.')
                if row.type_id=='authoring.MemoryBinding' and name in MEMORY_AUDIO_REFERENCE_FIELDS:
                    editor.setToolTip('Use Preview recording assignment for one verified audio pack, then Apply and Save.')
                if row.type_id=='authoring.Fixture' and name in INSPECTION_FIELDS:
                    editor.setToolTip('Authored inspection data; preserve source provenance. Use a complete text/source/action group, or clear all three. Reading and quiet seats do not award progress.')
                    if isinstance(editor,(QLineEdit,QPlainTextEdit)):editor.setReadOnly(not self._inspection_supported())
                display={'inspection_text':'Inspection text','inspection_source':'Source / provenance','inspection_action':'Interaction'}.get(name,name)
                self.form.addRow(display, editor)
                self.field_editors[name] = editor
        else:
            self.selection_label.setText('Select a chapter object')
        self.preview_details.clear()
        self._controls()
        self._publish_viewport()

    def _editor_inputs(self):
        result = {}
        for key, editor in self.field_editors.items():
            result[key] = (editor.isChecked() if isinstance(editor, QCheckBox)
                else editor.toPlainText() if isinstance(editor, QPlainTextEdit)
                else editor.currentData() if isinstance(editor,QComboBox) else editor.text())
        return result

    def _validated_asset_profile(self,rows):
        expected=validate_asset_profile(self.definition.asset_profile)
        profiles=[value for row in rows if row.type_id=='authoring.ChapterSettings'
                  for key,value in row.fields if key=='asset_profile']
        if len(profiles)>1 or profiles and profiles[0] not in ('legacy_v1','warm_beginning'):
            raise ProjectError('Invalid native chapter asset profile')
        actual='warm-beginning' if profiles==['warm_beginning'] else 'legacy_v1'
        if expected!=actual:raise ProjectError('Project asset profile differs from the native chapter document')
        return actual

    def _invalidate_preview(self, release=True):
        self._prepared_placement_id=None
        self._prepared_inspection_inputs=None
        self._prepared_workshop_inputs=None
        ai_preview = self._token is not None and self._token == self._ai_prepared_token
        super()._invalidate_preview(release)
        if ai_preview:
            self._ai_prepared_token = None
            self._ai_preview_summary = self._ai_preview_provenance = ''
            self.ai_status.setText('AI preview invalidated. Review a fresh proposal before Apply.')

    def apply_preview(self):
        if self._prepared_workshop_inputs is not None and self._prepared_workshop_inputs!=self._workshop_inputs():
            self._invalidate_preview();raise ProjectError('Workshop selections changed; preview the complete group again')
        if self._prepared_placement_id is not None:
            self._require_editable()
            identity,token=self._prepared_placement_id,self._token
            if not token:raise ProjectError('Preview the asset placement first')
            if self._prepared_inspection_inputs is not None and self._prepared_inspection_inputs!=self._inspection_creation_inputs():
                self._invalidate_preview();raise ProjectError('Inspection inputs changed; preview the panel again')
            self._prepared_placement_id=self._token=None;self.busy=True;self._controls()
            self._prepared_inspection_inputs=None
            return self._send('mutate',Opcode.APPLY_PREPARED,prepared_handle(self.client.head.scope,token),self.client.head.head_revision,identity)
        ai_preview = self._token is not None and self._token == self._ai_prepared_token
        result = super().apply_preview()
        if ai_preview:
            self._ai_prepared_token = None
            self._ai_preview_summary = self._ai_preview_provenance = ''
            self.ai_status.setText('Reviewed AI proposal submitted for Apply. See chapter status for the result; Save is separate.')
        return result

    def _require_editable(self):
        super()._require_editable()
        if self.description is None:
            raise ProjectError('Refresh the native chapter descriptor before editing')

    def _encode_edits(self, edits, label):
        edits=tuple(edits)
        if any(isinstance(edit,SetField)and edit.field in INSPECTION_FIELDS for edit in edits):self._require_inspection_support()
        validate_inspection_edits(self.rows,edits)
        if edits_require_workshop(edits):self._require_workshop_support()
        validate_workshop_edits(self.rows,edits,self.definition.asset_profile)
        return encode_scoped_edit(self.client.head.scope, self.description.definition_id,
            str(uuid.uuid4()), self.client.head.head_revision, self.description.fingerprint,
            label, tuple(edits))

    def preview_selected(self):
        self._require_editable()
        self._invalidate_preview()
        row = next((row for row in self.rows if row.uuid == self.selected_id), None)
        if row is None:
            raise ProjectError('Select a chapter object first')
        inputs, edits = self._editor_inputs(), []
        for name, original in row.fields:
            raw = inputs[name]
            if row.type_id=='authoring.CompanionBinding' and name in _COMPANION_MODEL_FIELDS:
                if raw!=original:raise ProjectError('Use Preview Adam model to change verified model references as one group')
                continue
            if row.type_id=='authoring.MemoryBinding' and name in MEMORY_AUDIO_REFERENCE_FIELDS:
                if raw!=original:raise ProjectError('Use Preview recording assignment to change verified audio references as one group')
                continue
            if row.type_id=='authoring.AssetPlacement' and name in ASSET_REFERENCE_FIELDS:
                if raw!=original:raise ProjectError('Asset dependency references are immutable')
                continue
            if row.type_id=='authoring.ChapterSettings' and name=='asset_profile':
                if raw!=original:raise ProjectError('Chapter asset profile is immutable')
                continue
            if name in (WORKSHOP_ROLE_FIELD,WORKSHOP_BINDING_FIELD):
                if raw!=original:raise ProjectError('Use the grouped Opening Workshop panel to change roles and bindings')
                continue
            if type(original) is bool:
                value = raw
            elif type(original) in (float, int):
                try:
                    value = float(raw) if type(original) is float else int(raw)
                except (ValueError, OverflowError) as error:
                    raise ProjectError('Enter a valid number for ' + name) from error
                if type(value) is float and not math.isfinite(value):
                    raise ProjectError('Enter a finite number for ' + name)
            else:
                value = raw
            same = (struct.pack('<d', value) == struct.pack('<d', original)
                if type(original) is float else value == original)
            if not same:
                edits.append(SetField(row.uuid, name, value))
        if not edits:
            raise ProjectError('No chapter fields changed')
        packet = self._encode_edits(edits, 'Edited ' + row.name)
        self.busy = True
        self._controls()
        return self._send('preview', Opcode.PREVIEW, edit_command(self.client.head.scope, packet),
            self.client.head.head_revision, (row.uuid, inputs))

    def submit_edits(self, edits, label, select_after=None):
        self._require_editable()
        return self._submit_packet(self._encode_edits(edits, label), select_after)

    def _submit_packet(self, packet, select_after=None, *, apply_after_preview=True,placement_preview=False,inspection_inputs=None,workshop_preview=False):
        self._require_editable()
        self._invalidate_preview()
        payload = edit_command(self.client.head.scope, packet)
        self.busy = True
        self._controls()
        kind = 'placement_preview' if placement_preview else ('auto_preview' if apply_after_preview else 'preview')
        extra = select_after if apply_after_preview else (self.selected_id, self._editor_inputs())
        if placement_preview:extra=(*extra,select_after,self.adopted_asset,self.asset_name_input.text(),inspection_inputs)
        if workshop_preview:
            if apply_after_preview or placement_preview:raise ProjectError('Workshop requires its own explicit grouped Preview')
            kind='workshop_preview';extra=(*extra,self._workshop_inputs())
        identity=self._send(kind, Opcode.PREVIEW, payload,self.client.head.head_revision,extra)
        if edits_publish_workshop(decode_scoped_edit(packet).edits):self._workshop_preview_requests.add(identity)
        return identity

    def current_proposal_context(self):
        if (not self.loaded or self.busy or self.description is None or
                self.client.state != 'ready' or self.client.pending_count or
                self.client.head is None or self._snapshot_tag != self._tag(self.client.head)):
            return None
        return self.description.definition_id, self.description.fingerprint, self.rows

    def submit_proposal(self, job_id, raw_json):
        self._require_editable()
        packet = self.proposal_jobs.consume(job_id, raw_json)
        return self._submit_packet(packet, apply_after_preview=False)

    def add_node(self, alias, name):
        return self.add_fixture(name)

    def add_fixture(self, name):
        self._require_editable()
        _text(name)
        identity = str(uuid.uuid4())
        return self.submit_edits((CreateFixture(identity, name, center=(-35., .4, 10.)),),
            'Created fixture ' + name, select_after=identity)

    def delete_selected(self):
        self._require_editable()
        row = next((row for row in self.rows if row.uuid == self.selected_id), None)
        if row is not None and row.type_id=='authoring.MemoryBinding':
            if _MEMORY_CAPABILITY not in self.client.capabilities:raise ProjectError('Upgrade the native owner before erasing a memory station')
            return self._submit_packet(self._encode_edits((EraseMemoryBinding(row.uuid),),'Deleted memory station '+row.name),
                select_after=None,apply_after_preview=False,placement_preview=True)
        if row is None or row.type_id not in ('authoring.Fixture','authoring.AssetPlacement'):
            raise ProjectError('Only authoring fixtures can be deleted here; required chapter records are retained')
        bindings=workshop_bindings_from_rows(self.rows,self.definition.asset_profile)
        if row.uuid in bindings:
            raise ProjectError('Workshop '+WORKSHOP_ACTIONS[bindings.index(row.uuid)]+' depends on this fixture; rebind it or preview removing the workflow before deletion')
        edit=EraseAssetPlacement(row.uuid) if row.type_id=='authoring.AssetPlacement' else EraseFixture(row.uuid)
        return self.submit_edits((edit,), 'Deleted authored object ' + row.name)

    def _travel(self, redo):
        self._require_editable()
        self._invalidate_preview()
        payload = history(self.client.head.scope, str(uuid.uuid4()), redo, self.description.fingerprint)
        self.busy = True
        self._controls()
        self._send('mutate', Opcode.HISTORY, payload, self.client.head.head_revision)

    def _snapshot_is_current(self):
        return self._export_snapshot_matches(self._content_snapshot)

    def _export_snapshot_matches(self,snapshot):
        complete = _COMPLETE_EXPORT_CAPABILITY in self.client.capabilities
        return (snapshot is not None and self.definition is not None and self.description is not None and self.client.head is not None and
            snapshot.asset_profile==self.definition.asset_profile and
            getattr(snapshot,'authored_inspections',False)==authored_inspections_from_rows(self.rows) and
            getattr(snapshot,'initial_view_authored',False)==initial_view_authored_from_rows(self.rows,self.definition.asset_profile) and
            getattr(snapshot,'opening_workshop_authored',False)==opening_workshop_authored_from_rows(self.rows,self.definition.asset_profile) and
            (getattr(snapshot,'export_version',1)==2 if complete else
                self.definition.asset_profile=='legacy_v1' and getattr(snapshot,'export_version',1)==1) and
            self.client.generation == snapshot.generation and self.client.head.scope == snapshot.scope and
            self.client.head.head_revision == snapshot.revision and self.client.head.checkpoint_id == snapshot.checkpoint_id and
            self.description.definition_id == snapshot.definition_id and self.description.fingerprint == snapshot.fingerprint and
            self.description.content_revision == snapshot.content_revision)

    def _begin_export(self, action, probe_directory=None):
        self._require_editable()
        if self._closing_project:
            raise ProjectError('The chapter project is closing')
        complete = _COMPLETE_EXPORT_CAPABILITY in self.client.capabilities
        inspections=authored_inspections_from_rows(self.rows)
        initial_view=initial_view_authored_from_rows(self.rows,self.definition.asset_profile)
        workshop=opening_workshop_authored_from_rows(self.rows,self.definition.asset_profile)
        if workshop and WORKSHOP_CAPABILITY not in self.client.capabilities:raise ProjectError('Upgrade the native Host before exporting Opening Workshop')
        if initial_view and INITIAL_VIEW_CAPABILITY not in self.client.capabilities:raise ProjectError('Upgrade the native owner before exporting an authored initial view')
        if inspections and INSPECTION_CAPABILITY not in self.client.capabilities:raise ProjectError('Upgrade the native owner before exporting authored inspections')
        if self.definition.asset_profile!='legacy_v1' and not complete:
            raise ProjectError('Upgrade the native chapter owner: complete model and audio dependency export is required before Preview or Play.')
        if self._snapshot_is_current():
            self._use_snapshot(action, probe_directory)
            return
        head = self.client.head
        self._export = ContentExportAssembly(head.scope, self.client.generation, head.head_revision,
            head.checkpoint_id, self.description, (row.uuid for row in self.rows),
            asset_refs=() if complete else dependencies_from_rows(self.rows),asset_store=self.definition.directory/'assets/packs',
            asset_profile=self._validated_asset_profile(self.rows),require_complete_dependencies=complete,authored_inspections=inspections,initial_view_authored=initial_view,opening_workshop_authored=workshop)
        self._export_action = (action, probe_directory)
        self.busy = True
        self.status.setText('Exporting a pinned native chapter snapshot…')
        self._controls()
        self._request_export()

    def _request_export(self):
        assembly = self._export
        self._send('export', Opcode.DESCRIBE, export_content(assembly.scope, assembly.offset,
            256*1024, assembly.description.fingerprint,complete_dependencies=assembly.require_complete_dependencies), assembly.revision)

    def _receive_export(self, reply):
        assembly = self._export
        if assembly is None:
            raise ProjectError('The content export was cancelled')
        snapshot = assembly.accept(decode_content_export(reply.body), reply.scope, self.client.generation,
            reply.head_revision, reply.checkpoint_id)
        if snapshot is None:
            self._request_export()
            return
        action, probe_directory = self._export_action
        self._export = None
        self._export_action = None
        self._content_snapshot = snapshot
        self.busy = False
        self._controls()
        if self._close_callback is not None or self._closing_project:
            self.status.setText('Chapter snapshot export cancelled by project close.')
            return
        if not self._snapshot_is_current():
            raise ProjectError('Chapter changed during export; refresh before opening a view')
        self._use_snapshot(action, probe_directory)

    def _use_snapshot(self, action, probe_directory=None):
        snapshot = self._content_snapshot
        if action == 'preview':
            if self.viewport.state == 'closed':
                candidates = self._binary_candidates('aibs_creator_viewport.exe')
                modern=snapshot.asset_profile=='warm-beginning'
                executable = next((path for path in candidates if path.is_file() and
                    (not modern or read_native_player_capabilities(path).get('features',{}).get('chapter_asset_surfaces') is True)
                    and (2 not in snapshot.dependency_kinds or read_native_player_capabilities(path).get('features',{}).get('audio_asset_v2') is True)
                    and (not snapshot.authored_inspections or read_native_player_capabilities(path).get('features',{}).get(INSPECTION_CAPABILITY)is True)
                    and (not getattr(snapshot,'initial_view_authored',False) or read_native_player_capabilities(path).get('features',{}).get(INITIAL_VIEW_CAPABILITY)is True)
                    and (not getattr(snapshot,'opening_workshop_authored',False) or read_native_player_capabilities(path).get('features',{}).get(WORKSHOP_CAPABILITY)is True)),None)
                if executable is None:raise ProjectError('A compatible native chapter preview is not built or packaged')
                selection={'selected_id':self.selected_id} if self.selected_id is not None else {}
                self.viewport.start_content(executable, snapshot, probe_directory,**selection)
            elif self.viewport.state in ('staging','ready', 'starting'):
                self.viewport.publish(snapshot.scope, snapshot.revision, snapshot.checkpoint_id, snapshot,
                    selected_id=self.selected_id)
        elif action == 'saved_play':
            self._start_saved_export(snapshot)
        elif action == 'play':
            executable = self._play_binary()
            if executable is None:
                raise ProjectError('The content-aware native Play executable has not been built or packaged')
            self.play.start(executable, snapshot)
        self._controls()

    def open_viewport(self, probe_directory=None):
        if self.viewport.state != 'closed':
            raise ProjectError('Close the current chapter preview first')
        self._begin_export('preview', probe_directory)

    def _publish_viewport(self):
        if (self.viewport.state not in ('staging','ready', 'starting') or not self.loaded or self.busy or
                self._closing_project or self.client.head is None or self._snapshot_tag != self._tag(self.client.head)):
            return
        self._run(lambda: self._begin_export('preview'))

    def start_play(self):
        if self.play.state != 'closed' or self._saved_children_active():
            raise ProjectError('Stop the current Play or saved chapter session first')
        self._begin_export('play')

    def stop_play(self):
        self.play.stop()
        self._controls()

    def _saved_children_active(self):
        return (hasattr(self,'saved_export') and self.saved_export.busy
            or hasattr(self,'saved_play') and self.saved_play.state!='closed')

    def _children_closed(self):
        return (self.play.state=='closed' and self.viewport.state=='closed'
            and not self._saved_children_active() and not self.asset_client.busy)

    def _saved_context_matches(self, snapshot, definition=None):
        return (self.definition is not None and (definition is None or self.definition is definition)
            and self.loaded and self.client.state=='ready' and not self._closing_project
            and self._close_callback is None and not self.client.pending_count
            and not self.client.uncertain_operations and not self.client.dirty
            and self.description is not None and not self.description.dirty
            and self.client.head is not None and bool(self.client.head.checkpoint_id)
            and self._snapshot_tag==self._tag(self.client.head)
            and _COMPLETE_EXPORT_CAPABILITY in self.client.capabilities
            and self._export_snapshot_matches(snapshot))

    def _require_saved_launch(self):
        self._require_editable()
        if self._closing_project or self._close_callback is not None:
            raise ProjectError('The chapter project is closing')
        if self.definition is None or self.description is None or self.client.head is None:
            raise ProjectError('Open and refresh a saved chapter first')
        if self.client.pending_count or self.client.uncertain_operations:
            raise ProjectError('Resolve the pending or interrupted chapter operation first')
        if self.client.dirty or self.description.dirty or not self.client.head.checkpoint_id:
            raise ProjectError('Save the chapter before playing with retained progress')
        if _COMPLETE_EXPORT_CAPABILITY not in self.client.capabilities:
            raise ProjectError('Saved chapter play requires complete native dependency export')
        if self.play.state!='closed' or self._saved_children_active() or self._saved_exporting:
            raise ProjectError('Stop the current Play or saved chapter session first')
        if self._saved_play_binary() is None:
            raise ProjectError('A compatible saved chapter player has not been built or packaged')

    def _saved_launch_available(self):
        try:
            self._require_saved_launch()
            return True
        except (ValueError,RuntimeError,AttributeError):
            return False

    def start_saved_play(self):
        self._require_saved_launch()
        self._saved_cancel_requested=False
        self._saved_status_message='Verifying the saved chapter in a separate native reader…'
        self._saved_owner_definition=self.definition
        self._begin_export('saved_play')

    def _start_saved_export(self, snapshot):
        if self._saved_cancel_requested or self._closing_project or self._close_callback is not None:
            return
        if not self._saved_context_matches(snapshot):
            raise ProjectError('Save and refresh the current chapter before playing it')
        self._saved_owner_definition=self.definition
        self._saved_exporting=True
        self.busy=True
        definition=self.definition
        try:
            self.saved_export.start(self.executable,definition,snapshot,
                context_valid=lambda:self._saved_context_matches(snapshot,definition))
        except Exception:
            self._saved_exporting=False
            self.busy=False
            self._controls()
            raise

    def _saved_export_completed(self, result):
        self._saved_exporting=False
        self.busy=False
        definition=self._saved_owner_definition or self.definition
        if (self.saved_export.busy or self._saved_cancel_requested or
                not self._saved_context_matches(result.snapshot,definition)):
            self._saved_status_message='Saved chapter launch cancelled because its owner or selection changed.'
            self._controls()
            return
        try:
            journal=hash_saved_journal(definition.directory)
            if (journal.sha256,journal.bytes)!=(result.journal_sha256,result.journal_bytes):
                raise ProjectError('The saved chapter journal changed before player staging')
            def valid():
                try:
                    return (self._saved_context_matches(result.snapshot,definition)
                        and hash_saved_journal(definition.directory)==journal)
                except (ValueError,OSError):
                    return False
            executable=self._saved_play_binary()
            if executable is None:raise ProjectError('A compatible saved chapter player is unavailable')
            self.saved_play.start(executable,result.snapshot,definition.directory,context_valid=valid)
            self._saved_status_message='Starting the saved chapter; gameplay progress is retained in its own save slot.'
        except Exception as error:
            self._saved_status_message='Saved chapter launch failed: '+str(error)
            self.status.setText(self._saved_status_message)
        self._controls()

    def _saved_export_failed(self, message):
        self._saved_exporting=False
        self.busy=False
        self._saved_status_message='Saved chapter verification failed: '+message
        self.status.setText(self._saved_status_message)
        self._controls()

    def _saved_export_closed(self):
        if self._saved_exporting:
            self._saved_exporting=False
            self.busy=False
        self._controls()
        if self._closing_project:self._stop_owner()
        else:self._service_close()

    def _saved_play_message(self, message):
        self._saved_status_message=message
        self.status.setText(message)
        self._update_saved_play_label()

    def _update_saved_play_label(self):
        if not hasattr(self,'saved_play_status'):return
        if self.saved_play.state!='closed':
            snapshot=self.saved_play.snapshot
            pinned=(f' · content {snapshot.fingerprint[:12]}' if snapshot is not None else '')
            self.saved_play_status.setText('Saved chapter '+self.saved_play.state+pinned
                +'. Gameplay progress is retained in its own save slot.')
        else:self.saved_play_status.setText(self._saved_status_message)

    def stop_saved_play(self):
        self._saved_cancel_requested=True
        self.saved_export.stop()
        self.saved_play.stop()
        self._saved_status_message='Saved chapter stopped. Retained progress has not been discarded.'
        self._controls()

    def _saved_play_closed(self):
        self._controls()
        if self._closing_project:self._stop_owner()
        else:self._service_close()

    def _stop_owner(self):
        if self._children_closed():
            super()._stop_owner()

    def close_project(self, discard=False):
        if hasattr(self,'opening_client')and self.opening_client.busy:
            self._opening_close_requested=True;self._opening_close_callback=lambda:None
            self.opening_client.stop();return
        if self._saved_exporting and self._export is None:
            self._saved_cancel_requested=True
            self._saved_exporting=False
            self.busy=False
        if self.busy or self.client.pending_count:
            raise ProjectError('Wait for the current chapter operation before closing')
        if not discard and self.definition and (self.client.dirty or self.client.uncertain_operations):
            raise ProjectError('Save changes or explicitly discard before closing')
        if discard:
            for record in self.client.uncertain_operations:
                self.client.acknowledge_recovery(record.generation, record.request_id)
        self._closing_project = True
        self.asset_client.stop()
        self.cancel_ai_generation('Project closing; generation cancelled.')
        self.play.stop()
        self.saved_export.stop()
        self.saved_play.stop()
        self.viewport.stop()
        self._controls()
        if self._children_closed():
            self._stop_owner()

    def prepare_close(self, callback=None):
        if self._saved_exporting and self._export is None:
            self._close_callback=callback or (lambda:None)
            self._saved_cancel_requested=True
            self.saved_export.stop()
            return False
        if hasattr(self,'opening_client')and self.opening_client.busy:
            self._opening_close_requested=True;self._opening_close_callback=callback or (lambda:None)
            self.opening_client.stop();return False
        if self.asset_client.busy:
            self._close_callback=callback or (lambda:None)
            self.asset_client.stop()
            return False
        if (self.definition is None and self.client.state == 'closed' and
                (self.play.state != 'closed' or self.viewport.state != 'closed' or self._saved_children_active())):
            self._close_callback = callback or (lambda: None)
            self.close_project(discard=True)
            return False
        result = super().prepare_close(callback)
        if self._close_callback is not None or self._closing_project:
            self.cancel_ai_generation('Project closing; generation cancelled.')
        return result

    def _service_close(self):
        if hasattr(self,'opening_client')and self.opening_client.busy:return
        if hasattr(self,'asset_client') and self.asset_client.busy:return
        if self._saved_exporting or self.saved_export.busy:return
        super()._service_close()

    def _viewport_closed(self):
        self._controls()
        if self._closing_project:
            self._stop_owner()

    def _play_closed(self):
        self._controls()
        if self._closing_project:
            self._stop_owner()

    def closeEvent(self, event):
        # The owner can exit before a requested child drain completes. Keep the
        # standalone widget alive even after its document has been cleared.
        if self.play.state != 'closed' or self.viewport.state != 'closed' or self._saved_children_active() or self.asset_client.busy or hasattr(self,'opening_client')and self.opening_client.busy:
            event.ignore()
            self.prepare_close(self.close)
            return
        if self.definition is None and self.client.state == 'closed':
            self.cancel_ai_generation('View closing; generation cancelled.')
        super().closeEvent(event)

    def _closed(self, reason):
        if hasattr(self,'saved_export'):
            self._saved_cancel_requested=True
            self.saved_export.stop()
            self.saved_play.stop()
            if self._closing_project and not self._children_closed():
                self._deferred_owner_close=reason
                return
        if getattr(self,'_workshop_mutation_requests',()):self._workshop_history_seen=True
        self._workshop_save_guard=None  # Unknown transport outcome retains the conservative metadata.
        if hasattr(self,'asset_client'):self.asset_client.stop()
        self.cancel_ai_generation('Chapter owner closed; generation cancelled.')
        self._ai_preview_request = None
        self._ai_prepared_token = None
        self._ai_preview_summary = self._ai_preview_provenance = ''
        self.description = None
        self._content_snapshot = None
        self._export = None
        self._export_action = None
        if hasattr(self, 'play') and not self._closing_project:
            self.play.stop()
        super()._closed(reason)

    def _failed(self, identity, message):
        if identity in getattr(self,'_workshop_mutation_requests',()):
            self._workshop_mutation_requests.discard(identity);self._workshop_history_seen=True
        if getattr(self,'_tasks',{}).get(identity,(None,None))[0]=='save':self._workshop_save_guard=None
        if identity == self._ai_preview_request:
            self._ai_preview_request = None
            self._ai_preview_summary = self._ai_preview_provenance = ''
            self._ai_prepared_token = None
            self.ai_status.setText('AI native preview failed: ' + message)
        super()._failed(identity, message)

