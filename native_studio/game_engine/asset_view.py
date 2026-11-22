"""Owned native asset cooking/inspection and preview; no authoring-save access."""
import json
from pathlib import Path
import re
import uuid

from PyQt6.QtCore import QCoreApplication, QProcess, QThread, QTimer, Qt
from PyQt6.QtWidgets import (QComboBox, QFileDialog, QFormLayout, QHBoxLayout, QInputDialog,
    QLabel, QLineEdit, QPushButton, QTreeWidget, QTreeWidgetItem, QVBoxLayout, QWidget)
from native_studio.theme import PALETTE

OUTPUT_LIMIT = 65536
MAX_ASSETS = 64
_SHA = re.compile(r'[0-9a-f]{64}\Z')


def _uuid(value):
    if type(value) is not str or str(uuid.UUID(value)) != value or uuid.UUID(value).version != 4:
        raise ValueError('A canonical version-4 asset UUID is required')
    return value


def _text(value, maximum=4096):
    if (type(value) is not str or not value or len(value.encode('utf-8')) > maximum
            or any(ord(c) < 32 or ord(c) == 127 for c in value)):
        raise ValueError('A bounded asset name is required')
    return value


def _plain(path, *, file=False, directory=False, fresh=False):
    path = Path(path).absolute()
    for part in (path, *path.parents):
        if part.is_symlink() or part.is_junction():
            raise ValueError('Choose plain local files and folders')
    path = path.resolve()
    if file and not path.is_file():
        raise ValueError('Choose an existing input file')
    if directory and not path.is_dir():
        raise ValueError('Choose an existing asset pack folder')
    if fresh and (path.exists() or not path.parent.is_dir()):
        raise ValueError('Choose a new asset pack folder inside an existing parent folder')
    return path


def _pairs(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError('Duplicate native receipt key')
        result[key] = value
    return result


def _constant(value):
    raise ValueError('Nonfinite native receipt value: ' + value)


class AssetView(QWidget):
    def __init__(self, cooker: Path, player: Path, parent=None, *, sample_pack: Path | None = None):
        super().__init__(parent)
        self.cooker, self.player = Path(cooker), Path(player)
        self.sample_pack = Path(sample_pack) if sample_pack is not None else None
        self.asset_rows = ()
        self.current_root = None
        self._tool = self._preview = None
        self._closing = False
        self._close_callback = None
        self._context = None
        self._tool_failure = self._preview_failure = ''
        self._preview_stopping = False
        self._tool_stdout = bytearray()
        self._tool_stderr = bytearray()
        self._preview_stdout = bytearray()
        self._preview_stderr = bytearray()
        self._tool_timer = QTimer(self)
        self._tool_timer.setSingleShot(True)
        self._tool_timer.setInterval(30000)
        self._tool_timer.timeout.connect(self._tool_timeout)
        self._preview_timer = QTimer(self)
        self._preview_timer.setSingleShot(True)
        self._preview_timer.setInterval(1500)
        self._preview_timer.timeout.connect(self._kill_preview)
        layout = QVBoxLayout(self)
        title = QLabel('AI-BS Native Assets')
        title.setObjectName('PanelTitle')
        layout.addWidget(title)
        details = QLabel('Cook your triangulated OBJ with an explicit material table and license. '
            'Choose legacy color materials or textured surfaces with UVs and embedded PNGs. '
            'Textured surfaces require AIBMAT2; full PBR is still in development.')
        details.setWordWrap(True)
        layout.addWidget(details)
        form = QFormLayout()
        layout.addLayout(form)
        self.format_combo=QComboBox()
        self.format_combo.addItem('Legacy color mesh (AIBMAT1)','mesh')
        self.format_combo.addItem('Textured surface (AIBMAT2 + PNG)','surface')
        self.format_combo.addItem('Memory recording (PCM16 WAV)','audio')
        form.addRow('Asset format',self.format_combo)
        self.uv_origin_combo=QComboBox()
        self.uv_origin_combo.addItem('Bottom-left (Blender OBJ)','bottom-left')
        self.uv_origin_combo.addItem('Top-left','top-left')
        self.uv_origin_combo.setEnabled(False)
        self.format_combo.currentIndexChanged.connect(lambda *_:self.uv_origin_combo.setEnabled(self.format_combo.currentData()=='surface'))
        form.addRow('Texture UV origin',self.uv_origin_combo)
        self.source_input = self._path_row(form, 'OBJ / WAV source', self._choose_source)
        self.materials_input = self._path_row(form, 'Engine materials', lambda: self._choose_file(self.materials_input, 'Choose engine material table', 'AI-BS materials (*.aibmat);;All files (*)'))
        self.license_input = self._path_row(form, 'License / provenance', lambda: self._choose_file(self.license_input, 'Choose license or provenance', 'Text files (*.txt);;All files (*)'))
        self.output_input = self._path_row(form, 'New pack folder', self._choose_output)
        self.name_input = QLineEdit('Part')
        self.asset_id_input = QLineEdit(str(uuid.uuid4()))
        form.addRow('Asset name', self.name_input)
        form.addRow('Asset UUID', self.asset_id_input)
        actions = QHBoxLayout()
        layout.addLayout(actions)
        self.cook_button = QPushButton('Cook new asset pack')
        self.open_button = QPushButton('Open asset pack')
        self.cancel_button = QPushButton('Cancel operation')
        for button in (self.cook_button, self.open_button, self.cancel_button):
            actions.addWidget(button)
        self.sample_button = None
        if self.sample_pack is not None:
            self.sample_button = QPushButton('Open bundled sample pack')
            self.sample_button.clicked.connect(lambda: self._run(lambda: self.inspect_pack(self.sample_pack)))
            actions.addWidget(self.sample_button)
        self.tree = QTreeWidget()
        self.tree.setHeaderLabels(['Asset', 'Triangles', 'Materials', 'UUID'])
        self.tree.setStyleSheet(
            f"QTreeWidget {{ background: {PALETTE['bg_dark']}; color: {PALETTE['text']}; "
            f"border: 1px solid {PALETTE['border']}; }} "
            "QTreeWidget::item { padding: 6px; } "
            f"QTreeWidget::item:selected {{ background: {PALETTE['panel_alt']}; color: {PALETTE['cyan']}; }}")
        for column, width in enumerate((430, 120, 120, 420)):
            self.tree.setColumnWidth(column, width)
        self.tree.header().setStretchLastSection(True)
        self.tree.currentItemChanged.connect(lambda *_: self._controls())
        layout.addWidget(self.tree, 1)
        preview = QHBoxLayout()
        layout.addLayout(preview)
        self.preview_button = QPushButton('Preview selected')
        self.stop_button = QPushButton('Stop preview')
        preview.addWidget(self.preview_button)
        preview.addWidget(self.stop_button)
        self.status = QLabel('Choose user-owned source files or open a cooked asset pack.')
        self.status.setWordWrap(True)
        layout.addWidget(self.status)
        self.cook_button.clicked.connect(lambda: self._run(self._cook_selected))
        self.format_combo.currentIndexChanged.connect(lambda *_: self.materials_input.setEnabled(self.format_combo.currentData()!='audio'))
        self.open_button.clicked.connect(self._choose_pack)
        self.cancel_button.clicked.connect(self.cancel_operation)
        self.preview_button.clicked.connect(lambda: self._run(self.preview_selected))
        self.stop_button.clicked.connect(self.stop_preview)
        app = QCoreApplication.instance()
        if app is not None:
            app.aboutToQuit.connect(self.shutdown)
        self._controls()

    @property
    def busy(self):
        return self._tool is not None

    @property
    def tool_process_id(self):
        return int(self._tool.processId()) if self._tool is not None else 0

    @property
    def preview_process_id(self):
        return int(self._preview.processId()) if self._preview is not None else 0

    def _path_row(self, form, label, choose):
        row = QHBoxLayout()
        field = QLineEdit()
        browse = QPushButton('Browse…')
        browse.clicked.connect(lambda: self._run(choose))
        row.addWidget(field, 1)
        row.addWidget(browse)
        form.addRow(label, row)
        return field

    def _choose_file(self, field, title, filters):
        path, _ = QFileDialog.getOpenFileName(self, title, '', filters)
        if path:
            field.setText(path)

    def _choose_source(self):
        audio=self.format_combo.currentData()=='audio'
        self._choose_file(self.source_input,'Choose PCM16 WAV recording' if audio else 'Choose triangulated OBJ',
            'PCM WAV (*.wav)' if audio else 'OBJ (*.obj)')

    def _cook_selected(self):
        if self.format_combo.currentData()=='audio':
            return self.cook_audio_asset(self.source_input.text(),self.license_input.text(),
                self.output_input.text(),self.asset_id_input.text(),self.name_input.text())
        return self.cook_asset(self.source_input.text(),self.materials_input.text(),self.license_input.text(),
            self.output_input.text(),self.asset_id_input.text(),self.name_input.text(),
            surface=self.format_combo.currentData()=='surface',uv_origin=self.uv_origin_combo.currentData())

    def _choose_output(self):
        parent = QFileDialog.getExistingDirectory(self, 'Choose parent folder for a new asset pack')
        if not parent:
            return
        name, accepted = QInputDialog.getText(self, 'New asset pack folder', 'Folder name:', text='MyAssetPack')
        if accepted:
            if not name or Path(name).name != name or name in ('.', '..') or '/' in name or '\\' in name:
                raise ValueError('Enter one new folder name')
            self.output_input.setText(str(Path(parent) / name))

    def _choose_pack(self):
        path = QFileDialog.getExistingDirectory(self, 'Open cooked asset pack')
        if path:
            self._run(lambda: self.inspect_pack(Path(path)))

    def _run(self, action):
        try:
            return action()
        except Exception as error:
            self.status.setText('Asset operation failed: ' + str(error))
            self._controls()
            return None

    def _thread(self):
        if QThread.currentThread() != self.thread():
            raise RuntimeError('Use the asset workspace on its Qt thread')

    def _available(self):
        self._thread()
        if self._closing:
            raise RuntimeError('The asset workspace is closing')
        if self._tool is not None or self._preview is not None:
            raise RuntimeError('Finish the current operation or stop its preview first')

    def _controls(self):
        ready = not self._closing and not self.busy and self._preview is None
        for button in (self.cook_button, self.open_button, self.sample_button):
            if button is not None:
                button.setEnabled(ready and self.cooker.is_file())
        self.cancel_button.setEnabled(not self._closing and self.busy)
        current=self.tree.currentItem()
        identity=current.data(0,Qt.ItemDataRole.UserRole) if current is not None else None
        row=next((r for r in self.asset_rows if r['asset_id']==identity),{})
        self.preview_button.setEnabled(ready and self.current_root is not None
            and current is not None and self.player.is_file() and self._preview_supported(row))
        self.stop_button.setEnabled(self._preview is not None)
        self.tree.setEnabled(ready)

    def cook_asset(self, source, materials, license, output, asset_id=None, name='Part', *, surface=False, uv_origin='bottom-left'):
        self._available()
        if type(surface) is not bool or surface and uv_origin not in ('bottom-left','top-left'):
            raise ValueError('Choose an explicit supported asset format and UV origin')
        source, materials, license = (_plain(path, file=True) for path in (source, materials, license))
        output = _plain(output, fresh=True)
        identity = _uuid(asset_id if asset_id is not None else str(uuid.uuid4()))
        name = _text(name)
        arguments=['--source', str(source), '--materials', str(materials), '--asset-id', identity,
            '--name', name, '--license', str(license), '--output', str(output)]
        if surface:arguments=['--cook-surface',*arguments,'--uv-origin',uv_origin]
        self._start_tool(arguments,
            {'mode': 'cook', 'root': output, 'asset_id': identity})

    def inspect_pack(self, root):
        self._available()
        root = _plain(root, directory=True)
        self._start_tool(['--inspect', str(root)], {'mode': 'inspect', 'root': root})

    def cook_audio_asset(self, source, license, output, asset_id=None, name='Memory recording'):
        self._available()
        source,license=(_plain(path,file=True) for path in (source,license))
        output=_plain(output,fresh=True)
        identity=_uuid(asset_id if asset_id is not None else str(uuid.uuid4()))
        name=_text(name,128)
        self._start_tool(['--cook-audio','--source',str(source),'--asset-id',identity,'--name',name,
            '--license',str(license),'--output',str(output)],
            {'mode':'cook','root':output,'asset_id':identity,'kind':'audio'})

    def _start_tool(self, arguments, context):
        executable = _plain(self.cooker, file=True)
        process = QProcess(self)
        self._tool, self._context = process, context
        self._tool_stdout.clear()
        self._tool_stderr.clear()
        self._tool_failure = ''
        process.setWorkingDirectory(str(executable.parent))
        process.setProcessChannelMode(QProcess.ProcessChannelMode.SeparateChannels)
        process.readyReadStandardOutput.connect(lambda: self._drain(process, 'tool', False))
        process.readyReadStandardError.connect(lambda: self._drain(process, 'tool', True))
        process.finished.connect(lambda code, status: self._tool_finished(process, code, status))
        process.errorOccurred.connect(lambda error: self._tool_error(process, error))
        self.status.setText('Cooking native asset pack…' if context['mode'] == 'cook' else 'Inspecting native asset pack…')
        self._tool_timer.start()
        self._controls()
        process.start(str(executable), arguments)

    def _drain(self, process, owner, stderr):
        if process is not getattr(self, '_' + owner):
            return
        failure = '_' + owner + '_failure'
        process.setReadChannel(QProcess.ProcessChannel.StandardError if stderr else QProcess.ProcessChannel.StandardOutput)
        buffer = getattr(self, '_' + owner + ('_stderr' if stderr else '_stdout'))
        while process.bytesAvailable():
            chunk = bytes(process.read(min(4096, process.bytesAvailable())))
            available = OUTPUT_LIMIT - len(buffer)
            buffer.extend(chunk[:available])
            if len(chunk) > available:
                setattr(self, failure, 'Native asset output limit exceeded')
                process.kill()
                return

    def _tool_error(self, process, error):
        if process is self._tool and error == QProcess.ProcessError.FailedToStart:
            self._tool_failure = process.errorString()
            self._tool_finished(process, -1, QProcess.ExitStatus.CrashExit)

    def _tool_timeout(self):
        if self._tool is not None:
            self._tool_failure = 'Native asset operation timed out after 30 seconds'
            self._tool.kill()

    def cancel_operation(self):
        self._thread()
        if self._tool is not None:
            self._tool_failure = 'Native asset operation cancelled'
            self._tool.kill()

    @staticmethod
    def _audio_row(row,identity,name,sha):
        keys=('sample_rate','channels','bits_per_sample','frame_count','pcm_bytes','payload_bytes',
            'decoded_bytes','caption_count','caption_text_bytes')
        if any(type(row.get(key)) is not int for key in keys):
            raise ValueError('Audio inspection requires complete bounded native metadata; upgrade the native cooker')
        rate,channels,bits,frames,pcm,payload,decoded,cues,text=(row[key] for key in keys)
        if (not 8000<=rate<=192000 or channels not in (1,2) or bits!=16 or frames<1
                or pcm!=frames*channels*2 or not 0<pcm<=48*1024*1024
                or not 0<payload<=48*1024*1024 or not pcm+text<=decoded<=64*1024*1024
                or not 0<=cues<=2048 or not 0<=text<=256*1024
                or (text!=0 if cues==0 else text<cues)
                or row.get('caption_review') not in ('draft','checked')
                or any(key in row for key in ('triangles','materials','vertices','image_count','decoded_image_bytes','joint_count','clip_count'))):
            raise ValueError('Invalid audio format, counts, caption declaration or residency budget')
        name=_text(name,128)
        if payload!=204+len(name.encode('utf-8'))+pcm+20*cues+text:
            raise ValueError('Audio metadata differs from complete canonical AIBAudio2 size')
        return {'asset_id':identity,'name':name,'sha256':sha,'kind':'audio',
            **{key:row[key] for key in keys},'caption_review':row['caption_review'],'duration_seconds':frames/rate}

    @staticmethod
    def audio_summary(row):
        declaration=('draft captions; listening review required' if row['caption_review']=='draft'
            else 'author-declared checked captions; wording is not independently reviewed')
        return (f"{row['name']} · {row['sample_rate']:,} Hz · {row['channels']} channel(s) · "
            f"{row['duration_seconds']:.2f} s · {row['caption_count']} caption cue(s) · {declaration}")

    @staticmethod
    def _rows(receipt):
        rows = receipt.get('assets')
        if type(rows) is not list or not 1 <= len(rows) <= MAX_ASSETS:
            raise ValueError('Native receipt requires 1..64 assets')
        admitted, identities = [], set()
        for row in rows:
            if type(row) is not dict:
                raise ValueError('Invalid native asset row')
            identity, name = _uuid(row.get('asset_id')), _text(row.get('name'))
            sha, triangles, materials = row.get('sha256'), row.get('triangles'), row.get('materials')
            if row.get('kind')=='audio':
                if identity in identities or type(sha) is not str or not _SHA.fullmatch(sha):
                    raise ValueError('Invalid audio identity or digest')
                admitted.append(AssetView._audio_row(row,identity,name,sha));identities.add(identity);continue
            if (identity in identities or type(sha) is not str or not _SHA.fullmatch(sha)
                    or type(triangles) is not int or not 1 <= triangles <= (524288 if row.get('kind')=='character' else 100000)
                    or type(materials) is not int or not 1 <= materials <= 64):
                raise ValueError('Invalid native asset identity, digest or counts')
            identities.add(identity)
            result={'asset_id':identity,'name':name,'sha256':sha,'triangles':triangles,'materials':materials}
            if 'kind' in row:
                kind=row['kind'];images=row.get('image_count');image_bytes=row.get('decoded_image_bytes');decoded=row.get('decoded_bytes')
                if (kind not in ('mesh','surface','character') or type(images) is not int or not 0<=images<=32
                        or type(image_bytes) is not int or not 0<=image_bytes<=32*1024*1024
                        or type(decoded) is not int or not image_bytes<=decoded<=(64 if kind=='character' else 128)*1024*1024
                        or kind=='mesh' and (images!=0 or image_bytes!=0)):
                    raise ValueError('Invalid typed visual asset receipt or residency counts')
                result.update(kind=kind,image_count=images,decoded_image_bytes=image_bytes,decoded_bytes=decoded)
                if kind=='character':
                    joints,clips,vertices=(row.get(key) for key in ('joint_count','clip_count','vertices'))
                    if (type(joints) is not int or not 1<=joints<=64
                            or type(clips) is not int or not 0<=clips<=8
                            or type(vertices) is not int or not 1<=vertices<=262144):
                        raise ValueError('Invalid character skeleton, animation or vertex counts')
                    result.update(joint_count=joints,clip_count=clips,vertices=vertices)
            admitted.append(result)
        return tuple(admitted)

    def _tool_finished(self, process, code, status):
        if process is not self._tool:
            return
        self._drain(process, 'tool', False)
        self._drain(process, 'tool', True)
        context, failure = self._context, self._tool_failure
        raw = bytes(self._tool_stdout)
        error_tail = bytes(self._tool_stderr[-2048:]).decode('utf-8', 'replace')
        self._tool_timer.stop()
        self._tool = self._context = None
        process.deleteLater()
        if not self._closing:
            try:
                if failure or code != 0 or status != QProcess.ExitStatus.NormalExit:
                    raise ValueError(failure or error_tail or 'Native cooker exited unsuccessfully')
                receipt = json.loads(raw.decode('utf-8', 'strict'), object_pairs_hook=_pairs, parse_constant=_constant)
                if type(receipt) is not dict or receipt.get('status') != 'passed':
                    raise ValueError('Native asset receipt did not pass')
                if context['mode'] == 'cook':
                    if (receipt.get('asset_id') != context['asset_id']
                            or type(receipt.get('sha256')) is not str or not _SHA.fullmatch(receipt['sha256'])
                            or type(receipt.get('output_root')) is not str
                            or Path(receipt['output_root']).resolve() != context['root']):
                        raise ValueError('Native cook receipt does not identify the requested output')
                    if context.get('kind')=='audio':
                        if self._rows({'assets':[receipt]})[0].get('kind')!='audio':
                            raise ValueError('Native audio cook receipt changed asset kind')
                    elif (type(receipt.get('triangles')) is not int or not 1<=receipt['triangles']<=100000
                            or type(receipt.get('vertices')) is not int or not 1<=receipt['vertices']<=100000):
                        raise ValueError('Native visual cook counts exceed legacy limits')
                    self._start_tool(['--inspect', str(context['root'])], {'mode': 'inspect', 'root': context['root']})
                else:
                    rows = self._rows(receipt)
                    self.asset_rows, self.current_root = rows, context['root']
                    self.tree.clear()
                    for row in rows:
                        audio=row.get('kind')=='audio'
                        item = QTreeWidgetItem([row['name'],f"{row['sample_rate']:,} Hz" if audio else str(row['triangles']),
                            f"{row['channels']} channels" if audio else str(row['materials']),row['asset_id']])
                        item.setData(0, Qt.ItemDataRole.UserRole, row['asset_id'])
                        item.setToolTip(0, 'SHA-256: ' + row['sha256'])
                        self.tree.addTopLevelItem(item)
                    self.tree.setCurrentItem(self.tree.topLevelItem(0))
                    self.status.setText(self.audio_summary(rows[0])+'. Assign it to an optional memory station in the chapter creator.'
                        if len(rows)==1 and rows[0].get('kind')=='audio'
                        else f"{len(rows)} native asset(s) inspected. Select one to preview. Pack: {self.current_root}")
            except Exception as error:
                self.status.setText('Asset operation failed: ' + str(error))
        self._controls()
        self._complete_close()

    def preview_selected(self):
        self._available()
        item = self.tree.currentItem()
        identity = item.data(0, Qt.ItemDataRole.UserRole) if item is not None else None
        if self.current_root is None or not any(row['asset_id'] == identity for row in self.asset_rows):
            raise ValueError('Select an inspected native asset first')
        row=next(row for row in self.asset_rows if row['asset_id']==identity)
        if not self._preview_supported(row):raise ValueError('This native player does not support textured asset preview; use a compatible chapter creator')
        executable = _plain(self.player, file=True)
        process = QProcess(self)
        self._preview = process
        self._preview_failure = ''
        self._preview_stopping = False
        self._preview_stdout.clear()
        self._preview_stderr.clear()
        process.setWorkingDirectory(str(executable.parent))
        process.setProcessChannelMode(QProcess.ProcessChannelMode.SeparateChannels)
        process.readyReadStandardOutput.connect(lambda: self._drain(process, 'preview', False))
        process.readyReadStandardError.connect(lambda: self._drain(process, 'preview', True))
        process.finished.connect(lambda code, status: self._preview_finished(process, code, status))
        process.errorOccurred.connect(lambda error: self._preview_error(process, error))
        process.started.connect(lambda: self.status.setText('Native asset preview running.') if process is self._preview and not self._closing else None)
        self._controls()
        process.start(str(executable), ['--asset-showcase', '--asset-root', str(self.current_root), '--asset-id', identity])

    def _preview_supported(self,row):
        if row.get('kind') in ('character','audio'):return False
        if row.get('kind')!='surface':return True
        from native_studio.game_build_monitor import read_native_player_capabilities
        return read_native_player_capabilities(self.player).get('features',{}).get('chapter_asset_surfaces') is True

    def _preview_error(self, process, error):
        if process is self._preview and error == QProcess.ProcessError.FailedToStart:
            self._preview_failure = process.errorString()
            self._preview_finished(process, -1, QProcess.ExitStatus.CrashExit)

    def _preview_finished(self, process, code, status):
        if process is not self._preview:
            return
        self._drain(process, 'preview', False)
        self._drain(process, 'preview', True)
        if (not self._preview_failure and not self._preview_stopping
                and (code != 0 or status != QProcess.ExitStatus.NormalExit)):
            self._preview_failure = (bytes(self._preview_stderr[-2048:]).decode('utf-8', 'replace')
                or 'Native player exited unsuccessfully')
        self._preview = None
        self._preview_timer.stop()
        process.deleteLater()
        if not self._closing:
            self.status.setText('Asset preview stopped.' if not self._preview_failure else 'Asset preview failed: ' + self._preview_failure)
        self._controls()
        self._complete_close()

    def stop_preview(self):
        self._thread()
        if self._preview is not None:
            self._preview_stopping = True
            self._preview.terminate()
            self._preview_timer.start()

    def _kill_preview(self):
        if self._preview is not None:
            self._preview.kill()

    def prepare_close(self, callback=None):
        self._thread()
        self._closing = True
        if callback is not None:
            self._close_callback = callback
        self.cancel_operation()
        self.stop_preview()
        self._controls()
        if self._tool is None and self._preview is None:
            self._close_callback = None
            return True
        return False

    def _complete_close(self):
        if self._closing and self._tool is None and self._preview is None and self._close_callback is not None:
            callback, self._close_callback = self._close_callback, None
            QTimer.singleShot(0, callback)

    def shutdown(self):
        self._thread()
        self._closing = True
        self._close_callback = None
        self._tool_timer.stop()
        self._preview_timer.stop()
        # Normal operations and parent close are asynchronous. Application exit
        # alone performs bounded joins of these two owned child handles.
        for process in (self._tool, self._preview):
            if process is not None and process.state() != QProcess.ProcessState.NotRunning:
                process.terminate()
                if not process.waitForFinished(1000):
                    process.kill()
                    process.waitForFinished(1000)

    def closeEvent(self, event):
        if not self.prepare_close(self.close):
            event.ignore()
            return
        super().closeEvent(event)
