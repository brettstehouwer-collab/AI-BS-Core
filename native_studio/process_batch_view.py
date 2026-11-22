"""Shared native controls for registered, explicitly submitted process batches."""
from __future__ import annotations
import os
from pathlib import Path
import shutil

from PyQt6.QtWidgets import (QDialog, QFileDialog, QFormLayout, QHBoxLayout, QLabel,
    QPlainTextEdit, QPushButton, QSpinBox, QVBoxLayout, QWidget, QMessageBox, QTabWidget)

from native_studio.process_batch import BatchLimits, JobSpec, ProcessBatchController

ROOT = Path(os.environ.get('AI_BS_ROOT', r'C:\AI-BS')).resolve()
HOLDS = (('DRY_RUN', 'true'), ('HOLD_DISPATCH', 'true'),
         ('AIBS_PAYMENT_MODE', 'disabled'), ('AI_BS_BACKEND_MANAGE_DAEMONS', 'false'),
         ('AI_BS_BACKEND_BACKGROUND_ENABLED', 'false'),
         ('AI_BS_RECDEBUT_OUTBOUND_ENABLED', 'false'), ('RECDEBUT_SENDING_ENABLED', 'false'))


def shared_batch_controller(bus):
    controller = getattr(bus, '_process_batch_controller', None)
    if controller is None:
        controller = ProcessBatchController(bus)
        bus._process_batch_controller = controller
    return controller


def source_jobs(paths, root=ROOT):
    root = Path(root).resolve(strict=True)
    interpreter = root / 'runtime/recovery-20261110/Scripts/python.exe'
    checker = root / 'runtime/devtools/native_source_check.py'
    if not interpreter.is_file() or not checker.is_file():
        raise ValueError('The registered recovery Python/source-check tools are unavailable.')
    paths = tuple(paths)
    if not paths or len(paths) > 128:
        raise ValueError('Select between 1 and 128 Python source files.')
    admitted = []
    seen = set()
    for path in paths:
        path = Path(path).absolute()
        if not path.is_relative_to(root) or path.suffix.lower() != '.py' or not path.is_file():
            raise ValueError('Select Python files inside the canonical project.')
        for item in (path, *path.parents):
            if item.is_symlink() or (hasattr(item, 'is_junction') and item.is_junction()):
                raise ValueError('Redirected source paths are not admitted.')
            if item == root:
                break
        resolved = path.resolve(strict=True)
        if not resolved.is_relative_to(root):
            raise ValueError('Source escaped the canonical project.')
        if resolved in seen:
            continue
        seen.add(resolved)
        admitted.append(JobSpec('source-' + str(len(admitted) + 1), str(interpreter),
            ('-I', '-B', str(checker), '--root', str(root), '--path', str(resolved)),
            str(root), timeout_seconds=30, environment=HOLDS))
    return admitted


def version_job():
    node = shutil.which('node.exe')
    script = ROOT / 'scripts/release-version.cjs'
    if not node or not script.is_file():
        raise ValueError('The registered Node/version checker is unavailable.')
    return JobSpec('version-metadata', node, (str(script), 'check'), str(ROOT),
                   timeout_seconds=60, environment=HOLDS)


class ProcessBatchPanel(QWidget):
    def __init__(self, controller, parent=None, *, bus=None):
        super().__init__(parent)
        self.setStyleSheet('QSpinBox, QLineEdit, QComboBox, QPlainTextEdit {'
            'background: #111827; color: #e5e7eb; border: 1px solid #475569; padding: 3px;}')
        self.controller = controller
        self.bus = bus
        self.selected_paths = []
        layout = QVBoxLayout(self)
        description = QLabel('Background controls — shared by BS-Chat and System Health.\n'
            'Controls govern this app’s native task bus and registered child processes. External services keep their own controls.')
        description.setWordWrap(True)
        layout.addWidget(description)
        tabs = QTabWidget()
        process_settings = QWidget()
        process_layout = QVBoxLayout(process_settings)
        form = QFormLayout()
        self.workers = self._spin(1, 8, 1)
        self.batch_size = self._spin(1, 128, 8)
        self.interval = self._spin(0, 60000, 100)
        self.cooldown = self._spin(0, 60000, 250)
        for label, control in (('Maximum worker processes', self.workers),
                ('Jobs per batch', self.batch_size), ('Minimum start gap (milliseconds)', self.interval),
                ('Gap between batches (milliseconds)', self.cooldown)):
            form.addRow(label, control)
        process_layout.addLayout(form)
        apply = QPushButton('Apply limits')
        apply.clicked.connect(self.apply_limits)
        process_layout.addWidget(apply)
        tabs.addTab(process_settings, 'Process batches')
        if bus is not None:
            native_settings = QWidget()
            native_layout = QVBoxLayout(native_settings)
            native_form = QFormLayout()
            current = bus.admission_snapshot()
            self.native_workers = self._spin(1, 8, current['max_workers'])
            self.native_batch_size = self._spin(1, 128, current['batch_size'])
            self.native_interval = self._spin(0, 60000, current['start_interval_ms'])
            self.native_cooldown = self._spin(0, 60000, current['batch_cooldown_ms'])
            for label, control in (('Maximum background tasks', self.native_workers),
                    ('Tasks per batch', self.native_batch_size),
                    ('Minimum start gap (milliseconds)', self.native_interval),
                    ('Gap between batches (milliseconds)', self.native_cooldown)):
                native_form.addRow(label, control)
            native_layout.addLayout(native_form)
            native_buttons = QHBoxLayout()
            for title, callback in (('Apply task limits', self.apply_native_limits),
                    ('Pause new tasks', bus.pause_admission), ('Resume tasks', bus.resume_admission),
                    ('Cancel waiting tasks', bus.cancel_pending)):
                button = QPushButton(title)
                button.clicked.connect(callback)
                native_buttons.addWidget(button)
            native_layout.addLayout(native_buttons)
            self.native_status = QLabel()
            self.native_status.setWordWrap(True)
            native_layout.addWidget(self.native_status)
            bus.admission_changed.connect(self._native_changed)
            self._native_changed(bus.admission_snapshot())
            tabs.addTab(native_settings, 'Shared native tasks')
        layout.addWidget(tabs)
        self.selection_label = QLabel('No source files selected.')
        layout.addWidget(self.selection_label)
        actions = QHBoxLayout()
        for title, callback in (('Choose Python files', self.choose_files),
                ('Start source checks', self.start_sources), ('Check version metadata', self.start_versions)):
            button = QPushButton(title)
            button.clicked.connect(callback)
            actions.addWidget(button)
        layout.addLayout(actions)
        controls = QHBoxLayout()
        for title, callback in (('Pause queue', self.pause_processes), ('Resume queue', self.resume_processes),
                                ('Reset failure halt', lambda: self._attempt(controller.reset_failure_halt)),
                                ('Cancel queued/running jobs', self.cancel_processes)):
            button = QPushButton(title)
            button.clicked.connect(callback)
            controls.addWidget(button)
        layout.addLayout(controls)
        self.status = QLabel('Idle')
        self.status.setWordWrap(True)
        layout.addWidget(self.status)
        self.output = QPlainTextEdit()
        self.output.setReadOnly(True)
        self.output.setMaximumBlockCount(500)
        layout.addWidget(self.output, 1)
        note = QLabel('Source checks parse files in separate processes without running or rewriting them. '
            'No model requests, Git commits or rollbacks. Pause stops new starts; active work may finish. '
            'Native task controls cover work submitted through the shared task bus; already running servers '
            'and backend/provider schedulers retain their own limits. These are admission limits, not a hard CPU/GPU percentage cap.')
        note.setWordWrap(True)
        layout.addWidget(note)
        controller.changed.connect(self._changed)
        controller.log.connect(self.output.appendPlainText)
        controller.job_event.connect(self._job_event)
        self._changed(controller.snapshot())

    @staticmethod
    def _spin(minimum, maximum, value):
        control = QSpinBox()
        control.setRange(minimum, maximum)
        control.setValue(value)
        control.setMinimumHeight(28)
        return control

    def limits(self):
        return BatchLimits(workers=self.workers.value(), batch_size=self.batch_size.value(),
            start_interval_ms=self.interval.value(), batch_cooldown_ms=self.cooldown.value())

    def _attempt(self, action):
        try:
            action()
        except (OSError, ValueError, RuntimeError) as exc:
            QMessageBox.warning(self, 'Batch not started', str(exc))

    def apply_limits(self):
        def apply():
            limits = self.limits()
            self.controller.configure(limits)
            terminal = getattr(self.bus, '_native_terminal', None)
            if terminal is not None:
                terminal.configure_admission(start_interval_ms=limits.start_interval_ms,
                    batch_size=limits.batch_size, batch_cooldown_ms=limits.batch_cooldown_ms)
        self._attempt(apply)

    def pause_processes(self):
        self.controller.pause()
        terminal = getattr(self.bus, '_native_terminal', None)
        if terminal is not None:
            terminal.pause_admission()

    def resume_processes(self):
        self.controller.resume()
        terminal = getattr(self.bus, '_native_terminal', None)
        if terminal is not None:
            terminal.resume_admission()

    def cancel_processes(self):
        self.controller.cancel()
        terminal = getattr(self.bus, '_native_terminal', None)
        if terminal is not None:
            terminal.cancel_all()

    def apply_native_limits(self):
        self._attempt(lambda: self.bus.configure_admission(max_workers=self.native_workers.value(),
            start_interval_ms=self.native_interval.value(), batch_size=self.native_batch_size.value(),
            batch_cooldown_ms=self.native_cooldown.value()))

    def _native_changed(self, snapshot):
        self.native_status.setText('Native task queue: ' + ('paused' if snapshot.get('paused') else 'open') +
            f" · {snapshot.get('queued', 0)} waiting · {snapshot.get('active_threads', 0)} active threads. " +
            'Active tasks finish cooperatively; cancelling waiting tasks does not terminate running work.')

    def choose_files(self):
        paths, _ = QFileDialog.getOpenFileNames(self, 'Choose source files for read-only checks',
                                                str(ROOT), 'Python source (*.py)')
        if paths:
            try:
                source_jobs(paths)
            except (OSError, ValueError) as exc:
                QMessageBox.warning(self, 'Selection not admitted', str(exc))
                return
            # Admission is rechecked at Start. Selection itself never starts work.
            self.selected_paths = paths
            self.selection_label.setText(f'{len(paths)} source files selected.')

    def start_sources(self):
        def start():
            jobs = source_jobs(self.selected_paths)
            self.controller.configure(self.limits())
            self.controller.submit(jobs)
        self._attempt(start)

    def start_versions(self):
        def start():
            job = version_job()
            self.controller.configure(self.limits())
            self.controller.submit([job])
        self._attempt(start)

    def _changed(self, snapshot):
        jobs = snapshot.get('jobs', [])
        completed = sum(row.get('state') == 'passed' for row in jobs)
        failed = sum(row.get('state') in ('failed', 'timed_out', 'cleanup_failed') for row in jobs)
        cancelled = sum(row.get('state') == 'cancelled' for row in jobs)
        self.status.setText(f"Processes: {snapshot.get('running', 0)} running · "
            f"{snapshot.get('queued', 0)} waiting · {completed} passed · {failed} failed · {cancelled} cancelled" +
            (' · Queue paused' if snapshot.get('paused') else '') +
            (f" · HALTED: repeated exit {snapshot.get('last_error_code')}" if snapshot.get('failure_halted') else '') +
            (' · Cleanup not confirmed: session retained' if snapshot.get('drain_failed') else ''))

    def _job_event(self, event):
        if event.get('kind') == 'finished':
            self.output.appendPlainText(f"{event.get('job_id')}: {event.get('state')} "
                f"(exit {event.get('exit_code')})\n{event.get('output', '')[:4000]}")


def create_work_control_pages(bus, parent=None):
    controller = shared_batch_controller(bus)
    from native_studio.ai_bs_ide_terminal import AIBSTerminal
    terminal = AIBSTerminal(parent, cwd=str(ROOT))
    bus._native_terminal = terminal
    pages = QTabWidget(parent)
    pages.setMinimumHeight(620)
    pages.addTab(ProcessBatchPanel(controller, pages, bus=bus), 'Batch controls')
    pages.addTab(terminal, 'Terminal')
    from native_studio.local_refactor_view import LocalRefactorPanel
    pages.addTab(LocalRefactorPanel(bus, ROOT, pages), 'Local refactor')
    return pages


def open_batch_controls(bus, owner, *, section='batches'):
    # One shared queue and one window per application, independent of the task bus pool.
    controller = shared_batch_controller(bus)
    dialog = getattr(bus, '_process_batch_dialog', None)
    if dialog is None:
        dialog = QDialog(owner.window())
        dialog.setWindowTitle('AI-BS — Background batch controls')
        dialog.resize(820, 540)
        layout = QVBoxLayout(dialog)
        pages = create_work_control_pages(bus, dialog)
        dialog._batch_pages = pages
        from native_studio.responsive_layout import workspace_scroll
        scroll = workspace_scroll(pages, dialog)
        scroll.setAccessibleName('Scrollable native work controls')
        layout.addWidget(scroll)
        bus._process_batch_dialog = dialog
    dialog._batch_pages.setCurrentIndex(1 if section == 'terminal' else 0)
    dialog.show()
    dialog.raise_()
    dialog.activateWindow()
    return dialog
