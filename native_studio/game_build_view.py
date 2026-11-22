"""Native AI-BS custom game-engine progress workspace."""
from pathlib import Path
from native_studio.responsive_layout import workspace_scroll
import json
import sys

from PyQt6.QtCore import QProcess, QSize, QTimer, QUrl, Qt
from PyQt6.QtGui import QDesktopServices
from PyQt6.QtWidgets import (QLabel, QLayout, QPlainTextEdit, QPushButton,
                             QScrollArea, QSizePolicy, QVBoxLayout, QWidget, QTabWidget)

from native_studio.game_build_monitor import read_build_progress, read_native_player_capabilities
from native_studio.theme import PALETTE

# The existing shell may retain a historical AI_BS_ROOT pointing to another
# drive. This workspace follows the actual source checkout, not that variable.
GAME_PROJECT_ROOT = Path(__file__).resolve().parents[1]
if not (GAME_PROJECT_ROOT / 'engine/CMakeLists.txt').exists():
    GAME_PROJECT_ROOT = Path('C:/AI-BS')


def _bundle_root() -> Path | None:
    if getattr(sys, 'frozen', False) and getattr(sys, '_MEIPASS', None):
        return Path(sys._MEIPASS)
    return None


def _playground_path(root: Path) -> Path:
    bundle = _bundle_root()
    candidates = []
    if bundle:
        candidates.append(bundle / 'game_assets/playground/index.html')
    candidates.extend((root / 'frontend/public/bs-game/index.html',
                       root / 'docs/game_engine/concept_playground/first_boot_playground.html'))
    return next((path for path in candidates if path.is_file()), candidates[-1])


def _native_player_candidates(root: Path) -> tuple[Path, ...]:
    bundle = _bundle_root()
    candidates = []
    if bundle:
        candidates.append(bundle / 'game_assets/player/aibs_motherboard.exe')
    candidates.extend((root / 'engine/install/0.17.2/runtime-release/bin/aibs_motherboard.exe',
                           root / 'engine/install/0.17.1/runtime-release/bin/aibs_motherboard.exe',
                           root / 'engine/install/0.17.0/runtime-release/bin/aibs_motherboard.exe',
                           root / 'engine/install/0.16.6/runtime-release/bin/aibs_motherboard.exe',
                           root / 'engine/install/0.16.5/runtime-release/bin/aibs_motherboard.exe',
                       root / 'engine/install/0.16.4/runtime-release/bin/aibs_motherboard.exe',
                       root / 'engine/install/0.16.3/runtime-release/bin/aibs_motherboard.exe',
                       root / 'engine/install/0.16.2/runtime-release/bin/aibs_motherboard.exe',
                       root / 'engine/install/0.16.1/runtime-release/bin/aibs_motherboard.exe',
                       root / 'engine/install/0.16.0/runtime-release/bin/aibs_motherboard.exe',
                       root / 'engine/install/0.15.0/runtime-release/bin/aibs_motherboard.exe',
                       root / 'engine/install/0.11.0/release/bin/aibs_motherboard.exe',
                       root / 'engine/install/release/bin/aibs_motherboard.exe',
                       root / 'engine/out/windows-msvc/Release/aibs_motherboard.exe'))
    return tuple(candidates)


def _native_player_path(root: Path) -> Path:
    candidates = _native_player_candidates(root)
    return next((path for path in candidates if path.is_file()), candidates[-2])


def _chapter_player_path(root: Path) -> Path | None:
    return next((path for path in _native_player_candidates(root)
                 if read_native_player_capabilities(path)['chapter_capable']), None)


def _asset_workspace_paths(root: Path):
    bundle = _bundle_root()
    if bundle:
        binary = bundle / 'game_assets/player'
        return binary / 'aibs_assetc.exe', binary / 'aibs_motherboard.exe', bundle / 'game_assets/reference_part'
    legacy = (root / 'engine/install/0.11.0/release/bin',
                  root / 'engine/install/0.10.0/release/bin',
                  root / 'engine/out/windows-msvc/Release',
                  root / 'engine/install/0.9.0/release/bin')
    candidates = (root / 'engine/install/0.17.2/runtime-release/bin',
                  root / 'engine/install/0.17.1/runtime-release/bin',
                  root / 'engine/install/0.17.0/runtime-release/bin',
                  root / 'engine/install/0.16.6/runtime-release/bin',
                  root / 'engine/install/0.16.5/runtime-release/bin',
                       root / 'engine/install/0.16.4/runtime-release/bin',
                       root / 'engine/install/0.16.3/runtime-release/bin',
                       root / 'engine/install/0.16.2/runtime-release/bin',
                       root / 'engine/install/0.16.1/runtime-release/bin',
                  root / 'engine/install/0.16.0/runtime-release/bin',
                  root / 'engine/install/0.15.0/runtime-release/bin', *legacy)
    binary = next((path for path in candidates
                   if (path / 'aibs_assetc.exe').is_file() and (path / 'aibs_motherboard.exe').is_file()), legacy[0])
    return binary / 'aibs_assetc.exe', binary / 'aibs_motherboard.exe', root / 'engine/assets/cooked/motherboard-reference'


def _opening_workspace_paths(root: Path, host: Path):
    # Factory and curator resources must belong to the same packaged resource
    # root. Source checkouts without that optional bundle retain legacy tools.
    bundle=_bundle_root()
    if bundle is None and host.parent.name=='player'and host.parent.parent.name=='game_assets':
        bundle=host.parent.parent.parent
    if bundle is not None:
        resources=bundle/'game_assets/opening'
    else:
        previews=(root/'engine/assets/cooked/warm-opening-v20-surface',
                  root/'engine/assets/cooked/warm-opening-v18')
        resources=next((p for p in previews if p.exists()),root/'engine/assets/cooked/warm-opening')
    factory=host.with_name('aibs_warm_opening_project.exe')
    return (factory if factory.is_file()else None,resources if resources.is_dir()else None)


def _warm_beginning_lines(summary: dict, *, detailed: bool = False) -> list[str]:
    lines = ['WARM BEGINNING — recorded progress']
    if summary.get('status') != 'available':
        lines += ['Summary: ' + summary.get('status','not_run') + '; no Warm Beginning verification claim.',
                  'Goal complete: no (not established by an available valid summary).']
        if summary.get('error'):
            lines.append(summary['error'])
        return lines
    lines.append('Goal complete: ' + ('yes (explicit recorded declaration)' if summary['goal_complete']
                                      else 'no (explicit recorded declaration)'))
    for key,label,version in (('native_source','Recorded native/source evidence: SDK','sdk_version'),
                              ('packaged_candidate','Packaged candidate: Studio','studio_version'),
                              ('deployed','Deployed launcher: Studio','studio_version')):
        entry = summary[key]
        lines.append(f"{label} {entry[version]} | {entry['status']}")
        if detailed:
            lines.append('  ' + entry['summary'])
            lines.extend('  Evidence: ' + path for path in entry['evidence_paths'])
    lines.append('Candidate tests and deployed launcher are separate recorded states.')
    if detailed:
        lines.append('Recorded summary: ' + summary['updated_at'])
        lines.append('Source: ' + summary['source_path'])
        lines.append('REMAINING ACCEPTANCE WORK')
        lines.extend(f"  {item['title']} [{item['status']}]: {item['detail']}" for item in summary['remaining'])
        lines.append('Next: ' + summary['next_step'])
    else:
        lines.append('Remaining: ' + '; '.join(item['title']+' ['+item['status']+']' for item in summary['remaining']))
    return lines


class _BuildProgressDetails(QPlainTextEdit):
    """Keep a readable log viewport when the surrounding page must scroll."""
    def minimumSizeHint(self):
        minimum = super().minimumSizeHint()
        # Ten text lines plus the document margin and this view's 10px padding.
        # Derive this on demand so font/style changes do not retain a stale height.
        height = (10 * self.fontMetrics().lineSpacing() +
                  round(2 * self.document().documentMargin()) + 2 * self.frameWidth() + 20)
        return minimum.expandedTo(QSize(0, height))

    def sizeHint(self):
        return super().sizeHint().expandedTo(self.minimumSizeHint())


class GameBuildNativeView(QWidget):
    def __init__(self, bus, parent=None, root: Path = GAME_PROJECT_ROOT):
        super().__init__(parent)
        self.setObjectName('Root')
        self.bus, self.root, self.pending = bus, Path(root), False
        outer = QVBoxLayout(self)
        self.workspace_tabs = QTabWidget()
        self.creator_view = None
        self.content_view = None
        self.asset_view = None
        self._creator_page = QWidget()
        self._creator_layout = QVBoxLayout(self._creator_page)
        self._content_page = QWidget()
        self._content_layout = QVBoxLayout(self._content_page)
        self._asset_page = QWidget()
        self._asset_layout = QVBoxLayout(self._asset_page)
        self.progress_scroll = QScrollArea()
        self.progress_scroll.setWidgetResizable(True)
        self._progress_content = QWidget()
        self.workspace_tabs.addTab(self.progress_scroll, 'Build progress')
        self.workspace_tabs.addTab(self._creator_page, 'Creator')
        self.workspace_tabs.addTab(self._content_page, 'Chapter creator')
        self.workspace_tabs.addTab(self._asset_page, 'Assets')
        self.workspace_tabs.currentChanged.connect(self._workspace_changed)
        outer.addWidget(self.workspace_tabs)
        layout = QVBoxLayout(self._progress_content)
        # Content keeps its natural text/control minimums; a short window scrolls
        # the page instead of squeezing labels, actions and the log to zero.
        layout.setSizeConstraint(QLayout.SizeConstraint.SetMinimumSize)
        title = QLabel('AI-BS Custom Game Engine — Build Progress')
        title.setObjectName('PanelTitle')
        layout.addWidget(title)
        layout.addWidget(QLabel("Adam's Infinite-Brett Stehouwer Living Learning Memoir"))
        layout.addWidget(QLabel(f'Project: {self.root}'))
        self.summary = QLabel('Reading build observations…')
        self.summary.setWordWrap(True)
        layout.addWidget(self.summary)
        self.warm_summary = QLabel('\n'.join(_warm_beginning_lines({'status':'not_run'})))
        self.warm_summary.setTextFormat(Qt.TextFormat.PlainText)
        self.warm_summary.setWordWrap(True)
        layout.addWidget(self.warm_summary)
        refresh = QPushButton('Refresh progress')
        refresh.clicked.connect(self.refresh)
        layout.addWidget(refresh)
        ledger = QPushButton('Open architectural builder ledger')
        ledger.clicked.connect(lambda: QDesktopServices.openUrl(QUrl.fromLocalFile(str(self.root / 'docs/game_engine/AI_BS_GAME_ARCHITECTURAL_BUILDER_LEDGER.md'))))
        layout.addWidget(ledger)
        self.playground_path = _playground_path(self.root)
        self.playground_button = QPushButton('Open Concept Playground (browser)')
        self.playground_button.setEnabled(self.playground_path.is_file())
        self.playground_button.setToolTip('Optional browser concept; simulated values and separate native checkpoints. The packaged/hosted copy includes its renderer for offline use; the original source sketch uses a CDN.')
        self.playground_button.clicked.connect(lambda: QDesktopServices.openUrl(QUrl.fromLocalFile(str(self.playground_path))))
        layout.addWidget(self.playground_button)
        self.native_player_path = _native_player_path(self.root)
        self.native_player_button = QPushButton('Launch native motherboard world (PC / DX12)')
        self.native_player_button.setToolTip('Launch the bundled or installed AI-BS native PC renderer. Enabled only when its executable exists.')
        self.native_player_button.clicked.connect(self._launch_native_player)
        layout.addWidget(self.native_player_button)
        self.obstacle_course_button = QPushButton('Launch native obstacle course (PC / DX12)')
        self.obstacle_course_button.setToolTip('Test steps, slopes, walls and recovery in the native PC course. WASD walk; Space jump; V camera; E repair core; F5 save; F9 reload/return.')
        self.obstacle_course_button.clicked.connect(self._launch_obstacle_course)
        layout.addWidget(self.obstacle_course_button)
        self.durable_world_button = QPushButton('Launch durable First Boot world (PC / DX12)')
        self.durable_world_button.setToolTip('Native First Boot with background SQLite saves and recorded Adam outcomes. E/click repair; B build; Delete dismantle; F5 retry; F9 reload. Uses its dedicated durable-world save.')
        self.durable_world_button.clicked.connect(self._launch_durable_world)
        layout.addWidget(self.durable_world_button)
        self.warm_opening_button = QPushButton('Open Warm Beginning')
        self.warm_opening_button.setToolTip('Open the current First Boot opening with Adam, the boot nook and repair/bypass Workshop. Create a separate opening to use the current character assets, or open an existing one to continue its saved world. Then use Play saved chapter.')
        self.warm_opening_button.clicked.connect(self._open_warm_beginning)
        layout.addWidget(self.warm_opening_button)
        self.chapter_player_path = _chapter_player_path(self.root)
        self.chapter_button = QPushButton('Play First Boot chapter (legacy blockout)')
        self.chapter_button.setToolTip('Original compiled chapter and its dedicated legacy save. For the current detailed opening and retained chapter gameplay, choose Open Warm Beginning.')
        self.chapter_button.clicked.connect(self._launch_chapter)
        layout.addWidget(self.chapter_button)
        self.launch_status = QLabel('')
        self.launch_status.setWordWrap(True)
        layout.addWidget(self.launch_status)
        self._update_launch_targets()
        self.details = _BuildProgressDetails()
        self.details.setReadOnly(True)
        self.details.setStyleSheet(f"QPlainTextEdit {{ background: {PALETTE['bg_dark']}; color: {PALETTE['text']}; border: 1px solid {PALETTE['border']}; padding: 10px; }}")
        layout.addWidget(self.details)
        for label in self._progress_content.findChildren(QLabel):
            label.setTextFormat(Qt.TextFormat.PlainText)
            label.setWordWrap(True)
            label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)
        for button in self._progress_content.findChildren(QPushButton):
            # Qt's font/style-aware sizeHint includes the theme's button padding.
            button.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.progress_scroll.setWidget(self._progress_content)
        self.timer = QTimer(self)
        self.timer.setInterval(3000)
        self.timer.timeout.connect(self.refresh)

    def _workspace_changed(self, index):
        if index == 3:
            if self.asset_view is None:
                from native_studio.game_engine.asset_view import AssetView
                cooker, player, sample = _asset_workspace_paths(self.root)
                self.asset_view = AssetView(cooker, player, self._asset_page, sample_pack=sample)
                self._asset_layout.addWidget(self.asset_view)
            return
        if index == 2 and self.content_view is None:
            from native_studio.game_engine.content_view import ContentView
            bundle = _bundle_root()
            candidates = ([bundle / 'game_assets/player/aibs_content_host.exe'] if bundle else [])
            candidates.extend((self.root / 'engine/install/0.17.2/runtime-release/bin/aibs_content_host.exe',
                           self.root / 'engine/install/0.17.1/runtime-release/bin/aibs_content_host.exe',
                           self.root / 'engine/install/0.17.0/runtime-release/bin/aibs_content_host.exe',
                           self.root / 'engine/install/0.16.6/runtime-release/bin/aibs_content_host.exe',
                           self.root / 'engine/install/0.16.5/runtime-release/bin/aibs_content_host.exe',
                       self.root / 'engine/install/0.16.4/runtime-release/bin/aibs_content_host.exe',
                       self.root / 'engine/install/0.16.3/runtime-release/bin/aibs_content_host.exe',
                       self.root / 'engine/install/0.16.2/runtime-release/bin/aibs_content_host.exe',
                       self.root / 'engine/install/0.16.1/runtime-release/bin/aibs_content_host.exe',
                       self.root / 'engine/install/0.16.0/runtime-release/bin/aibs_content_host.exe',
                       self.root / 'engine/install/0.15.0/runtime-release/bin/aibs_content_host.exe',
                               self.root / 'engine/install/0.11.0/release/bin/aibs_content_host.exe',
                               self.root / 'engine/install/0.10.0/release/bin/aibs_content_host.exe',
                               self.root / 'engine/out/windows-msvc/Release/aibs_content_host.exe',
                               self.root / 'engine/install/release/bin/aibs_content_host.exe',
                               self.root / 'engine/out/windows-msvc/Debug/aibs_content_host.exe'))
            binary = next((path for path in candidates if path.is_file()), candidates[-2])
            cooker, _, sample = _asset_workspace_paths(self.root)
            opening_factory,opening_root=_opening_workspace_paths(self.root,binary)
            self.content_view = ContentView(binary, self._content_page, asset_cooker=cooker, sample_asset_pack=sample,
                opening_factory=opening_factory,opening_assets_root=opening_root)
            self.content_scroll=workspace_scroll(self.content_view,self._content_page)
            self._content_layout.addWidget(self.content_scroll)
            return
        if index != 1 or self.creator_view is not None:
            return
        from native_studio.game_engine.creator_view import CreatorView
        bundle = _bundle_root()
        candidates = ([bundle / 'game_assets/player/aibs_creator_host.exe'] if bundle else [])
        candidates.extend((self.root / 'engine/install/0.17.2/runtime-release/bin/aibs_creator_host.exe',
                           self.root / 'engine/install/0.17.1/runtime-release/bin/aibs_creator_host.exe',
                           self.root / 'engine/install/0.17.0/runtime-release/bin/aibs_creator_host.exe',
                           self.root / 'engine/install/0.16.6/runtime-release/bin/aibs_creator_host.exe',
                           self.root / 'engine/install/0.16.5/runtime-release/bin/aibs_creator_host.exe',
                       self.root / 'engine/install/0.16.4/runtime-release/bin/aibs_creator_host.exe',
                       self.root / 'engine/install/0.16.3/runtime-release/bin/aibs_creator_host.exe',
                       self.root / 'engine/install/0.16.2/runtime-release/bin/aibs_creator_host.exe',
                       self.root / 'engine/install/0.16.1/runtime-release/bin/aibs_creator_host.exe',
                       self.root / 'engine/install/0.16.0/runtime-release/bin/aibs_creator_host.exe',
                       self.root / 'engine/install/0.15.0/runtime-release/bin/aibs_creator_host.exe',
                           self.root / 'engine/install/release/bin/aibs_creator_host.exe',
                           self.root / 'engine/out/windows-msvc/Release/aibs_creator_host.exe'))
        binary = next((path for path in candidates if path.is_file()), candidates[-1])
        self.creator_view = CreatorView(binary, self._creator_page)
        self.creator_scroll=workspace_scroll(self.creator_view,self._creator_page)
        self._creator_layout.addWidget(self.creator_scroll)

    def prepare_close(self, callback=None):
        for view in (self.creator_view, self.content_view, self.asset_view):
            if view is not None and not view.prepare_close(lambda: self._resume_close(callback)):
                return False
        return True

    def _resume_close(self, callback):
        if self.prepare_close(callback) and callback:
            callback()

    def closeEvent(self, event):
        if not self.prepare_close(self.close):
            event.ignore()
            return
        super().closeEvent(event)
        self.timer.stop()

    def shutdown(self):
        self.timer.stop()
        for view in (self.creator_view, self.content_view):
            if view is not None:
                if hasattr(view,'opening_client'):view.opening_client.stop()
                view.client.stop()
        if self.asset_view is not None:
            self.asset_view.shutdown()

    def showEvent(self, event):
        super().showEvent(event)
        self.timer.start()
        self.refresh()

    def hideEvent(self, event):
        self.timer.stop()
        super().hideEvent(event)

    def refresh(self):
        self._update_launch_targets()
        if self.pending:
            return
        self.pending = True
        try:
            self.bus.submit(read_build_progress, self.root, on_result=self._render, on_error=self._error)
        except Exception as exc:
            self._error(str(exc))

    def _update_launch_targets(self):
        self.playground_path = _playground_path(self.root)
        self.playground_button.setEnabled(self.playground_path.is_file())
        self.native_player_path = _native_player_path(self.root)
        self.native_player_button.setEnabled(self.native_player_path.is_file())
        self.obstacle_course_button.setEnabled(self.native_player_path.is_file())
        self.durable_world_button.setEnabled(self.native_player_path.is_file())
        self.chapter_player_path = _chapter_player_path(self.root)
        self.chapter_button.setEnabled(self.chapter_player_path is not None)
        factory, assets = _opening_workspace_paths(self.root, self.chapter_player_path or self.native_player_path)
        self.warm_opening_button.setEnabled(factory is not None and assets is not None)

    def _open_warm_beginning(self):
        try:
            # Construct directly before selecting the tab, so a setup failure is
            # caught here rather than escaping a Qt currentChanged callback.
            self._workspace_changed(2)
            self.workspace_tabs.setCurrentIndex(2)
        except Exception as exc:
            self.launch_status.setText('Could not open Warm Beginning: ' + str(exc))
            return
        self.launch_status.setText('In Chapter creator, choose Create First Boot opening or open your existing opening, then Play saved chapter. Save edits before playing.')

    def _launch_native_player(self):
        self._start_native_player([], 'Native motherboard world')

    def _launch_obstacle_course(self):
        self._start_native_player(['--obstacle-course'], 'Native obstacle course')

    def _launch_durable_world(self):
        self._start_native_player(['--durable-world'], 'Native durable First Boot world')

    def _launch_chapter(self):
        self._start_native_player(['--durable-world', '--chapter'], 'First Boot chapter', chapter=True)

    def _start_native_player(self, arguments, label, *, chapter=False):
        self._update_launch_targets()
        binary = self.chapter_player_path if chapter else self.native_player_path
        if chapter and binary is None:
            self.launch_status.setText('The First Boot chapter has not been built or packaged for this player yet.')
            return
        if not binary.is_file():
            self.launch_status.setText('The native motherboard renderer has not been built or packaged yet.')
            return
        failure_label = 'the First Boot chapter' if chapter else 'the native motherboard renderer'
        try:
            result = QProcess.startDetached(str(binary), arguments, str(binary.parent))
        except Exception as exc:
            self.launch_status.setText('Could not start ' + failure_label + ': ' + str(exc))
            return
        started = result[0] if isinstance(result, tuple) else bool(result)
        self.launch_status.setText(label + ' launched.' if started else 'Could not start ' + failure_label + '.')

    def _error(self, message):
        self.pending = False
        self.summary.setText('Build progress unavailable: ' + message)
        self.warm_summary.setText('WARM BEGINNING — summary update unavailable; no current verification claim.')

    def _render(self, data):
        self.pending = False
        self._update_launch_targets()
        queue = data['milestone_queue']
        current = next((item for item in queue['milestones'] if item['id'] == queue.get('current_milestone')), None)
        milestone_summary = f"\nCurrent milestone: {current['id']}: {current['title']} [{current['status']}]" if current else ''
        changed = 'Source changed after this build; verification is stale.' if data['source_changed_since_build'] else ''
        self.summary.setText(f"Build: {data['status']} | {data.get('configuration', 'none')} | {data.get('stage', 'not run')}{milestone_summary}\n{changed}")
        checkpoint = data['checkpoint_verification']
        renderer = data['renderer_verification']
        world_scene = data['world_scene_verification']
        movement = data['movement_verification']
        obstacle_course = data['obstacle_course_verification']
        gameplay_store = data['gameplay_store_verification']
        registry_migration = data.get('registry_migration_verification', {'status': 'not_run', 'checks': []})
        durable_world = data.get('durable_world_verification', {'status': 'not_run', 'checks': []})
        chapter_proof = data.get('first_boot_chapter_verification', {'status': 'not_run', 'checks': []})
        hosting = data['hosting_verification']
        persistence = ('Checkpoint tests passed; see the recorded checks below.' if checkpoint['status'] == 'passed'
                       else f"Checkpoint verification: {checkpoint['status']}.")
        warm = data.get('warm_beginning_summary',{'status':'not_run','goal_complete':False})
        self.warm_summary.setText('\n'.join(_warm_beginning_lines(warm)))
        lines = _warm_beginning_lines(warm,detailed=True) + ['',
                 'HISTORICAL RECORDED EVIDENCE — CUSTOM ENGINE FOUNDATION',
                 'Retained verification reports describe their recorded scope; queue, storage and source observations are separately labeled.',
                 'Custom Windows PC engine, source SDK, world identity and checkpoints.',
                 'Optional Concept Playground opens in your browser; its simulated state does not use native checkpoints.',
                 persistence,
                 ('Persistent world edits and restart rendering verified.' if world_scene['status'] == 'passed'
                  else f"Persistent world-to-render verification: {world_scene['status']}."),
                 ('Grounded movement and collision checks passed; see recorded test scope below.' if movement['status'] == 'passed'
                  else f"Grounded movement verification: {movement['status']}."),
                 ('Obstacle course checks passed; see recorded traversal and restart scope below.' if obstacle_course['status'] == 'passed'
                  else f"Obstacle course verification: {obstacle_course['status']}."),
                 ('Native gameplay and durable restart checks passed; see recorded proof scope below.' if durable_world['status'] == 'passed'
                  else f"Native durable world verification: {durable_world['status']}."),
                 ('Native First Boot chapter checks passed; see recorded proof scope below.' if chapter_proof['status'] == 'passed'
                  else f"Native First Boot chapter verification: {chapter_proof['status']}."),
                 'Native motherboard renderer verified; current integration milestone: saved entities and visible edits.' if renderer['status'] == 'passed' and world_scene['status'] != 'passed'
                 else 'Native PC renderer and persistent scene integration verified.' if renderer['status'] == 'passed' and world_scene['status'] == 'passed'
                 else 'Current graphics milestone: native window and DX12 motherboard renderer; verification pending.',
                 '', 'LONG-TERM BUILD QUEUE', 'Declared plan; recorded runtime test reports remain the verification evidence.',
                 f"Queue: {queue['status']} | {queue.get('updated_at', 'not recorded')}"]
        if queue.get('error'):
            lines.append(queue['error'])
        if current:
            lines.append(f"Current: {current['id']}: {current['title']} [{current['status']}]")
            for gate in current.get('gates', []):
                lines.append(f"  {gate['id']}: {gate['status']} | {gate['description']}")
                if gate.get('evidence'):
                    lines.append('    Evidence references: ' + ', '.join(gate['evidence']))
        creator = data.get('creator_workspace_verification', {'status': 'not_run', 'checks': []})
        lines += ['', 'CREATOR WORKSPACE VERIFICATION',
                  f"Creator workspace: {creator['status']} | {creator.get('completed_at', 'no completed test run')}",
                  creator.get('origin', 'Source numeric authoring; native viewport and chapter tools remain unfinished.')]
        if creator.get('error'):
            lines.append(creator['error'])
        lines.extend('  ' + check for check in creator['checks'])
        viewport = data.get('creator_viewport_verification', {'status': 'not_run', 'checks': []})
        lines += ['', 'NATIVE CREATOR VIEWPORT VERIFICATION',
                  f"Native creator viewport: {viewport['status']} | {viewport.get('completed_at', 'no completed test run')}",
                  viewport.get('origin', 'Native preview has not been verified; chapter Play remains unfinished.')]
        if viewport.get('error'):
            lines.append(viewport['error'])
        lines.extend('  ' + check for check in viewport['checks'])
        content = data.get('first_boot_content_verification', {'status': 'not_run', 'checks': []})
        lines += ['', 'CHAPTER CONTENT / SAVE BINDING VERIFICATION',
                  f"Chapter content: {content['status']} | {content.get('completed_at', 'no completed test run')}",
                  content.get('origin', 'Content-aware chapter authoring has not been verified.')]
        if content.get('error'):
            lines.append(content['error'])
        lines.extend('  ' + check for check in content['checks'])
        typed = data.get('content_authoring_verification', {'status': 'not_run', 'checks': []})
        lines += ['', 'TYPED AUTHORING / STRUCTURED PROPOSAL VERIFICATION',
                  f"Typed authoring: {typed['status']} | {typed.get('completed_at', 'no completed test run')}",
                  typed.get('origin', 'Typed authoring has not been verified; no live AI connection is claimed.')]
        if typed.get('error'):
            lines.append(typed['error'])
        lines.extend('  ' + check for check in typed['checks'])
        chapter_creator = data.get('chapter_creator_verification', {'status': 'not_run', 'checks': []})
        chapter_play = data.get('chapter_play_verification', {'status': 'not_run', 'checks': []})
        ai_authoring = data.get('ai_authoring_verification', {'status': 'not_run', 'checks': []})
        lines += ['', 'CHAPTER CREATOR / PROPOSAL JOB VERIFICATION',
                  ('Native typed endpoint/client/GUI and proposal-job admission verified.'
                   if chapter_creator['status'] == 'passed'
                   else f"Chapter creator verification: {chapter_creator['status']}."),
                  f"Status: {chapter_creator['status']} | {chapter_creator.get('completed_at', 'no completed test run')}",
                  'Source: ' + str(self.root / 'engine/out/chapter_creator_verification.json'),
                  ('Live selected-model authoring evidence appears below; broader tools remain planned.'
                   if ai_authoring['status'] == 'passed'
                   else 'Live model-provider inference remains unfinished; native chapter preview/Play evidence appears below.'
                   if chapter_play['status'] == 'passed'
                   else 'Live model-provider inference and chapter viewport/Play integration remain unfinished.')]
        if chapter_creator.get('origin'):
            lines.append(chapter_creator['origin'])
        if chapter_creator.get('error'):
            lines.append(chapter_creator['error'])
        lines.extend('  ' + check for check in chapter_creator['checks'])
        if 'metrics' in chapter_creator:
            metrics_text = json.dumps(chapter_creator['metrics'], ensure_ascii=False, sort_keys=True)
            lines.append('Metrics: ' + (metrics_text if len(metrics_text) <= 8192
                         else metrics_text[:8192] + '… (display truncated)'))
        lines += ['', 'NATIVE CHAPTER EXPORT / PREVIEW / ISOLATED PLAY VERIFICATION',
                  ('Native chapter export/preview and isolated Play verified.' if chapter_play['status'] == 'passed'
                   else f"Native chapter preview/Play verification: {chapter_play['status']}."),
                  f"Status: {chapter_play['status']} | {chapter_play.get('completed_at', 'no completed test run')}",
                  'Source: ' + str(self.root / 'engine/out/chapter_play_verification.json'),
                  'Test gameplay resets when Play stops; creator edits remain.']
        if chapter_play.get('origin'):
            lines.append(chapter_play['origin'])
        if chapter_play.get('error'):
            lines.append(chapter_play['error'])
        lines.extend('  ' + check for check in chapter_play['checks'])
        if 'metrics' in chapter_play:
            metrics_text = json.dumps(chapter_play['metrics'], ensure_ascii=False, sort_keys=True)
            lines.append('Metrics: ' + (metrics_text if len(metrics_text) <= 8192
                         else metrics_text[:8192] + '… (display truncated)'))
        lines += ['', 'LIVE LOCAL AI AUTHORING VERIFICATION',
                  ('Live selected-model inference and field proposals verified.'
                   if ai_authoring['status'] == 'passed'
                   else f"AI authoring verification: {ai_authoring['status']}."),
                  f"Status: {ai_authoring['status']} | {ai_authoring.get('completed_at', 'no completed test run')}",
                  'Source: ' + str(self.root / 'engine/out/ai_authoring_verification.json'),
                  'Exposed text, number and boolean fields only. Native Preview and explicit Apply are required; Save is separate.',
                  'Model, endpoint and prompt provenance are session metadata; durable provenance remains planned.',
                  'Imported original memories remain preserved; generated wording is a draft, not recovered history.']
        if ai_authoring['status'] == 'passed':
            lines.append('Recorded live coverage: one selected installed local model; broader tool authoring remains planned.')
        if ai_authoring.get('origin'):
            lines.append(ai_authoring['origin'])
        if ai_authoring.get('error'):
            lines.append(ai_authoring['error'])
        lines.extend('  ' + check for check in ai_authoring['checks'])
        if 'metrics' in ai_authoring:
            metrics_text = json.dumps(ai_authoring['metrics'], ensure_ascii=False, sort_keys=True)
            lines.append('Metrics: ' + (metrics_text if len(metrics_text) <= 8192
                         else metrics_text[:8192] + '… (display truncated)'))
        assets = data.get('asset_pipeline_verification', {'status': 'not_run', 'checks': []})
        lines += ['', 'ASSET AND MATERIAL PIPELINE',
                  ('Cooked mesh/material rendering verified.' if assets['status'] == 'passed'
                   else f"Asset pipeline verification: {assets['status']}."),
                  f"Status: {assets['status']} | {assets.get('completed_at', 'no completed test run')}",
                  'Opaque base color and emission; visual-only imported mesh layer.',
                  'Texture maps and PBR remain planned. Persistent chapter placement evidence appears below.',
                  'Source: ' + str(self.root / 'engine/out/asset_pipeline_verification.json')]
        lines.extend('  ' + check for check in assets['checks'])
        if 'metrics' in assets:
            text = json.dumps(assets['metrics'], ensure_ascii=False, sort_keys=True)
            lines.append('Metrics: ' + (text if len(text) <= 8192 else text[:8192] + '… (display truncated)'))
        placement=data.get('persistent_placement_verification',{'status':'not_run','checks':[]})
        lines+=['','PERSISTENT ASSET PLACEMENT',
                ('Persistent chapter asset placements verified.' if placement['status']=='passed'
                 else f"Persistent placement verification: {placement['status']}."),
                f"Status: {placement['status']} | {placement.get('verified_at','no completed test run')}",
                f"SDK: {placement.get('sdk_version','not recorded')} | Studio: {placement.get('studio_version','not recorded')}",
                'Source: '+str(self.root/'engine/out/persistent_placement_verification.json')]
        if placement.get('error'):lines.append(placement['error'])
        lines.extend('  '+check for check in placement['checks'])
        lines.extend('Limitation: '+value for value in placement.get('limitations',[]))
        lines.extend('Proof: '+value for value in placement.get('proof_paths',[]))
        for key,label in (('metrics','Metrics'),('next_step','Next step'),('drive_checkpoint','Drive checkpoint')):
            if key in placement:
                value=placement[key] if type(placement[key]) is str else json.dumps(placement[key],ensure_ascii=False,sort_keys=True)
                lines.append(label+': '+(value if len(value)<=8192 else value[:8192]+'… (display truncated)'))
        lines += ['', 'NEXT THREE PENDING SLICES']
        pending_slices = [item for item in queue['next_slices'] if item['status'] != 'complete'][:3]
        lines.extend(f"{item['id']} [{item['status']}] {item['title']} ({item['milestone']})" for item in pending_slices)
        if not pending_slices:
            lines.append('No pending slices recorded in the queue.')
        lines += ['', 'BUILD OBSERVATIONS']
        if data.get('error'):
            lines.append(data['error'])
        for config, record in data.get('configurations', {}).items():
            lines.append(f"{config}: {record.get('status', 'unknown')} at {record.get('completed_at', 'unknown')}")
        lines += ['', 'NATIVE PC WINDOW / DX12 VERIFICATION',
                  f"Status: {renderer['status']} | {renderer.get('completed_at', 'no completed test run')}"]
        if renderer.get('error'):
            lines.append(renderer['error'])
        adapter = renderer.get('adapter', renderer.get('adapter_description', renderer.get('adapter_name')))
        if adapter is not None:
            lines.append('Adapter: ' + (json.dumps(adapter, ensure_ascii=False) if isinstance(adapter, dict) else str(adapter)))
        lines.extend(f"  {check}" for check in renderer['checks'])
        lines += ['', 'PERSISTENT WORLD / VISIBLE SCENE VERIFICATION',
                  f"Status: {world_scene['status']} | {world_scene.get('completed_at', 'no completed test run')}"]
        if world_scene.get('error'):
            lines.append(world_scene['error'])
        for field, label in (('world_id', 'World'), ('checkpoint_id', 'Checkpoint'),
                             ('revision', 'Revision'), ('restored_revision', 'Restored revision'),
                             ('entity_count', 'Entities'), ('object_count', 'Rendered objects'),
                             ('memory_events', 'Adam records')):
            if field in world_scene:
                lines.append(f"{label}: {world_scene[field]}")
        if world_scene.get('adapter') is not None:
            adapter = world_scene['adapter']
            lines.append('Scene adapter: ' + (json.dumps(adapter, ensure_ascii=False) if isinstance(adapter, dict) else str(adapter)))
        ids = world_scene.get('stable_ids', world_scene.get('entity_ids'))
        if ids:
            if isinstance(ids, dict):
                lines.extend(f"  {name}: {identity}" for name, identity in list(ids.items())[:10])
            else:
                lines.append('Stable entity IDs: ' + ', '.join(ids[:10]))
        if world_scene.get('metrics'):
            lines.append('Recorded scene metrics: ' + json.dumps(world_scene['metrics'], ensure_ascii=False))
        lines.extend(f"  {check}" for check in world_scene['checks'])
        lines += ['', 'MOVEMENT / COLLISION VERIFICATION',
                  f"Status: {movement['status']} | {movement.get('completed_at', 'no completed test run')}"]
        if movement.get('error'):
            lines.append(movement['error'])
        if movement.get('engine'):
            lines.append('Physics: ' + movement['engine'] + ' ' + movement.get('engine_version', ''))
        if 'fixed_hz' in movement:
            lines.append(f"Simulation: {movement['fixed_hz']} Hz fixed ticks")
        if movement.get('metrics'):
            lines.append('Recorded movement metrics: ' + json.dumps(movement['metrics'], ensure_ascii=False))
        lines.extend(f"  {check}" for check in movement['checks'])
        lines += ['', 'NATIVE OBSTACLE COURSE VERIFICATION',
                  f"Status: {obstacle_course['status']} | {obstacle_course.get('completed_at', 'no completed test run')}"]
        if obstacle_course.get('error'):
            lines.append(obstacle_course['error'])
        if obstacle_course.get('adapter') is not None:
            adapter = obstacle_course['adapter']
            lines.append('Course adapter: ' + (json.dumps(adapter, ensure_ascii=False) if isinstance(adapter, dict) else str(adapter)))
        for field, label in (('world_id', 'Course world'), ('checkpoint_id', 'Course checkpoint')):
            if field in obstacle_course:
                lines.append(f"{label}: {obstacle_course[field]}")
        if obstacle_course.get('metrics'):
            lines.append('Recorded course metrics: ' + json.dumps(obstacle_course['metrics'], ensure_ascii=False))
        lines.extend(f"  {check}" for check in obstacle_course['checks'])
        lines += ['', 'M2 SQLITE PROCESS RECOVERY',
                  'Headless storage proof; native gameplay evidence is reported separately.',
                  f"Status: {gameplay_store['status']} | {gameplay_store.get('completed_at', 'no completed test run')}"]
        if gameplay_store.get('error'):
            lines.append(gameplay_store['error'])
        if gameplay_store.get('world_id'):
            lines.append('Proof world: ' + gameplay_store['world_id'])
        if 'revision' in gameplay_store:
            lines.append(f"Proof revision: {gameplay_store['revision']}")
        if gameplay_store.get('metrics'):
            lines.append('Recorded store metrics: ' + json.dumps(gameplay_store['metrics'], ensure_ascii=False))
        lines.extend(f"  {check}" for check in gameplay_store['checks'])
        lines += ['', 'REGISTRY MIGRATION VERIFICATION',
                  'Recorded registry compatibility proof; this does not verify the native chapter or M3 completion.',
                  ('Registry migration checks passed; see recorded report scope.' if registry_migration['status'] == 'passed'
                   else f"Registry migration verification: {registry_migration['status']}."),
                  f"Status: {registry_migration['status']} | {registry_migration.get('completed_at', 'no completed test run')}",
                  'Source: ' + registry_migration.get('source_path', str(self.root / 'engine/out/registry_migration_verification.json'))]
        if registry_migration.get('error'):
            lines.append(registry_migration['error'])
        scope = registry_migration.get('scope', {})
        for field, label in (('project_id', 'Registry proof project'), ('world_id', 'Registry proof world'),
                             ('branch_id', 'Registry proof branch'), ('timeline_id', 'Registry proof timeline'),
                             ('context', 'Registry proof context')):
            if field in scope:
                lines.append(f"{label}: {scope[field]}")
        for field, label in (('revision', 'Preserved gameplay revision'),
                             ('original_checkpoint_id', 'Original checkpoint')):
            if field in registry_migration:
                lines.append(f"{label}: {registry_migration[field]}")
        metrics = registry_migration.get('metrics', {})
        if 'old_studio92_rejected' in metrics:
            lines.append('Retained Studio92 format2 rejection (optional compatibility observation): ' +
                         ('true' if metrics['old_studio92_rejected'] else 'false'))
        if metrics:
            lines.append('Recorded registry migration metrics: ' + json.dumps(metrics, ensure_ascii=False))
        lines.extend(f"  {check}" for check in registry_migration['checks'])
        lines += ['', 'M2 NATIVE DURABLE WORLD VERIFICATION',
                  'Recorded native input, GPU rendering, SQLite restart, live retry, close drain and original-import proof.',
                  f"Status: {durable_world['status']} | {durable_world.get('completed_at', 'no completed test run')}"]
        if durable_world.get('error'):
            lines.append(durable_world['error'])
        scope = durable_world.get('scope', {})
        for field, label in (('project_id', 'Native project'), ('world_id', 'Native world'),
                             ('branch_id', 'Branch'), ('timeline_id', 'Timeline'), ('context', 'Context')):
            if field in scope:
                lines.append(f"{label}: {scope[field]}")
        for field, label in (('revision', 'Durable revision'), ('durable_events', 'Durable events')):
            if field in durable_world:
                lines.append(f"{label}: {durable_world[field]}")
        if durable_world.get('metrics'):
            lines.append('Recorded native durable metrics: ' + json.dumps(durable_world['metrics'], ensure_ascii=False))
        lines.extend(f"  {check}" for check in durable_world['checks'])
        lines += ['', 'M3 NATIVE FIRST BOOT CHAPTER VERIFICATION',
                  'Recorded repair/bypass slice, actual player view and HUD, interactions, hazards and save continuity.',
                  f"Status: {chapter_proof['status']} | {chapter_proof.get('completed_at', 'no completed test run')}",
                  'Source: ' + chapter_proof.get('source_path', str(self.root / 'engine/out/first_boot_chapter_verification.json'))]
        if chapter_proof.get('error'):
            lines.append(chapter_proof['error'])
        for field, label in (('executablePath', 'Recorded executable'),
                             ('executableSha256', 'Recorded executable SHA-256'),
                             ('work_directory', 'Proof work directory')):
            if field in chapter_proof:
                lines.append(f"{label}: {chapter_proof[field]}")
        chapter_metrics = chapter_proof.get('metrics', {})
        if 'debug_layer' in chapter_metrics:
            lines.append('D3D12 debug layer observed: ' + ('true' if chapter_metrics['debug_layer'] else 'false'))
        if chapter_metrics:
            lines.append('Recorded native chapter metrics: ' + json.dumps(chapter_metrics, ensure_ascii=False))
        lines.extend(f"  {check}" for check in chapter_proof['checks'])
        lines += ['', 'PUBLISHED FIREBASE SITE (recorded verification; no background network polling)',
                  f"Status: {hosting['status']} | {hosting.get('verified_at', 'not verified')}"]
        if hosting.get('error'):
            lines.append(hosting['error'])
        if hosting.get('origin'):
            lines.append(f"{hosting['origin']}  {hosting.get('version', '')}")
        lines.extend(f"  {check}" for check in hosting['checks'])
        lines += ['', 'WORLD IDENTITY / CHECKPOINT VERIFICATION',
                  f"Status: {checkpoint['status']} | {checkpoint.get('completed_at', 'no completed test run')}"]
        if checkpoint.get('error'):
            lines.append(checkpoint['error'])
        lines.extend(f"  {check}" for check in checkpoint['checks'])
        lines += ['', 'CHECKPOINT ARTIFACTS (latest 20; file presence alone does not verify a save)']
        lines.extend(f"{item['path']}  {item['bytes']:,} bytes" for item in data['checkpoints'])
        if not data['checkpoints']:
            lines.append('No checkpoint artifacts observed.')
        if data['checkpoint_inventory_partial']:
            lines.append('Checkpoint inventory is partial; a scan limit or inaccessible path was encountered.')
        lines += ['', 'ENGINE OUTPUT STORAGE']
        for label, storage in data['engine_storage'].items():
            qualifier = ' (partial scan)' if storage['partial'] else ''
            lines.append(f"{label}: {storage['bytes'] / 1024**2:.2f} MiB / {storage['file_count']:,} files{qualifier}")
        lines += ['', 'LOCAL DRIVE SPACE (GiB)']
        for drive in data['drives']:
            warning = ' LOW SPACE' if drive['low_space'] else ''
            lines.append(f"{drive['drive']}  {drive['free_bytes'] / 1024**3:.2f} free / {drive['total_bytes'] / 1024**3:.2f} total{warning}")
        lines += ['Google Drive account quota is not available through this local monitor.', '', 'RECENT SOURCE / DESIGN UPDATES']
        lines.extend(item['path'] for item in data['recent_files'])
        lines += ['', 'BUILD EVENT HISTORY']
        lines.extend(f"{e.get('at', '')}  {e.get('configuration', '')}  {e.get('status', '')}  {e.get('stage', '')}" for e in data['events'][-20:] if isinstance(e, dict))
        lines += ['', 'LATEST VERIFICATION LOG', data['log'] or 'No verification log yet.']
        self.details.setPlainText('\n'.join(lines))
