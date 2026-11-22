"""Opt-in BS Chat coding panel, using EngineBus and server-owned records."""
from __future__ import annotations
import json
import uuid
from PyQt6.QtCore import QTimer, Qt
from PyQt6 import sip
from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel, QComboBox,
    QPlainTextEdit, QLineEdit, QPushButton, QTreeWidget, QTreeWidgetItem, QCheckBox)
from native_studio.coding_mode_service import CodingModeService, preparation_payload, identifier


class CodingModeView(QDialog):
    def __init__(self, bus, parent=None, *, service=None):
        super().__init__(parent)
        self.bus = bus
        self.service = service or CodingModeService()
        self._busy = False
        self._preview = None
        self._scope = None
        self._review = None
        self._record = {}
        self._history_cursor = None
        self._capability_owner = None
        self._coding_enabled = False
        self._trusted_local_available = False
        self._delivery_epoch = 0
        self._apply_review = None
        self.setWindowTitle('BS Chat · Coding')
        self.resize(900, 760)
        layout = QVBoxLayout(self)
        intro = QLabel('Plan → prepare a proposal → check → review. Original files require explicit application.')
        intro.setWordWrap(True); layout.addWidget(intro)
        self.project = QComboBox(); self.project.addItem('AI-BS', 'ai-bs')
        layout.addWidget(self.project)
        self.capabilities = QLabel('Checking local coding availability…'); self.capabilities.setWordWrap(True)
        layout.addWidget(self.capabilities)
        self.objective = QLineEdit(); self.objective.setPlaceholderText('Task objective')
        layout.addWidget(self.objective)
        self.file_fields = {}
        row = QHBoxLayout()
        for role in ('editable', 'verification', 'dependency'):
            column = QVBoxLayout(); label = QLabel(role.title() + ' files (one relative path per line)')
            label.setWordWrap(True); column.addWidget(label)
            edit = QPlainTextEdit(); edit.setMaximumHeight(100)
            column.addWidget(edit); row.addLayout(column); self.file_fields[role] = edit
        layout.addLayout(row)
        check_row = QHBoxLayout()
        self.check_fields = {}
        for profile, label in [('python_unittest', 'Python test modules'), ('node_test', 'Node test files'), ('npm_script', 'npm script names')]:
            column = QVBoxLayout(); caption = QLabel(label + ' (one per line)')
            caption.setWordWrap(True); column.addWidget(caption)
            field = QPlainTextEdit(); field.setMaximumHeight(65)
            column.addWidget(field); check_row.addLayout(column); self.check_fields[profile] = field
        layout.addLayout(check_row)
        ids = QHBoxLayout()
        self.request_id = QLineEdit(); self.request_id.setPlaceholderText('Preparation ID')
        self.plan_id = QLineEdit(); self.plan_id.setPlaceholderText('Plan ID')
        self.proposal_id = QLineEdit(); self.proposal_id.setPlaceholderText('Proposal ID')
        self.execution_id = QLineEdit(); self.execution_id.setPlaceholderText('Check record ID')
        for field in (self.request_id, self.plan_id, self.proposal_id): ids.addWidget(field)
        ids.addWidget(self.execution_id)
        for field in (self.request_id, self.plan_id, self.proposal_id, self.execution_id):
            field.textChanged.connect(self._clear_apply_review)
        layout.addLayout(ids)
        history_row = QHBoxLayout()
        self.history_kind = QComboBox(); self.history_kind.addItems(['Preparations', 'Plans', 'Proposals', 'Checks'])
        history_row.addWidget(self.history_kind)
        history_load = QPushButton('Load saved work'); history_load.clicked.connect(self.history); history_row.addWidget(history_load)
        capability_retry = QPushButton('Check service'); capability_retry.clicked.connect(self.check_service); history_row.addWidget(capability_retry)
        self.history_more = QPushButton('More checks'); self.history_more.setEnabled(False)
        self.history_more.clicked.connect(lambda: self.history(more=True)); history_row.addWidget(self.history_more)
        layout.addLayout(history_row)
        self.history_rows = QTreeWidget(); self.history_rows.setHeaderLabels(['Saved work', 'Status', 'Record'])
        self.history_rows.setMaximumHeight(110); self.history_rows.itemClicked.connect(self._select_history)
        layout.addWidget(self.history_rows)
        actions = QGridLayout()
        for index, (label, callback) in enumerate([('Preview scope', self.preview), ('Prepare', self.prepare), ('Plan', self.plan),
                                ('Review plan', self.review_plan), ('Implement proposal', self.implement),
                                ('Refresh', self.refresh), ('Recover', self.recover), ('Cancel', self.cancel), ('History', self.history)]):
            button = QPushButton(label); button.clicked.connect(callback); actions.addWidget(button, index // 3, index % 3)
        layout.addLayout(actions)
        execution_row = QHBoxLayout()
        execution_row.addWidget(QLabel('Check mode'))
        self.execution_mode = QComboBox()
        self.execution_mode.addItem('Isolated worker', 'isolated')
        self.execution_mode.addItem('Trusted local checks', 'trusted_host')
        self.execution_mode.currentIndexChanged.connect(self._execution_mode_changed)
        execution_row.addWidget(self.execution_mode)
        self.trusted_ack = QCheckBox('For this task: allow my account’s filesystem and network access; no VM isolation.')
        self.trusted_ack.setEnabled(False); execution_row.addWidget(self.trusted_ack)
        layout.addLayout(execution_row)
        checks_row = QHBoxLayout()
        for label, callback in [('Check candidate', self.check_candidate), ('Review changes', self.review_changes),
                                ('Refresh checks', self.refresh_checks), ('Recover checks', self.recover_checks),
                                ('Cancel checks', self.cancel_checks)]:
            button = QPushButton(label); button.clicked.connect(callback); checks_row.addWidget(button)
        self.apply_button = QPushButton('Apply reviewed changes')
        self.apply_button.setEnabled(False)
        self.apply_button.setToolTip('Review a verified candidate before explicitly applying its changes.')
        self.apply_button.clicked.connect(self.apply_changes)
        checks_row.addWidget(self.apply_button); layout.addLayout(checks_row)
        self.status = QLabel('No task started. Checks have not run.'); layout.addWidget(self.status)
        self.output = QPlainTextEdit(); self.output.setReadOnly(True); layout.addWidget(self.output, 1)
        self.evidence_button = QPushButton('Show evidence details'); self.evidence_button.setCheckable(True)
        self.evidence_button.toggled.connect(self._show_evidence); layout.addWidget(self.evidence_button)
        self.timer = QTimer(self); self.timer.setInterval(2000); self.timer.timeout.connect(self._poll)
        self.check_service()

    def _call(self, method, path, payload=None, done=None, concurrent=False):
        if method != 'GET' and (not self._coding_enabled or not self._capability_owner):
            self.status.setText('Coding actions are unavailable until this service confirms enabled access. Use Check service to retry.')
            return
        if self._busy and not concurrent:
            self.status.setText('An operation is active; its retained record can still be cancelled.'); return
        if method == 'POST' or '/mode/executions/' in path:
            self._clear_apply_review()
        if not concurrent: self._busy = True
        epoch = self._delivery_epoch
        def success(value):
            if sip.isdeleted(self) or epoch != self._delivery_epoch: return
            if not concurrent: self._busy = False
            self._record = value
            if '/mode/executions' in path and value.get('state') != 'RUNNING': self.timer.stop()
            self.status.setText(str(value.get('state', value.get('kind', 'Record loaded'))) + ' · ' + str(value.get('verification_status', 'checks not confirmed')))
            self._render(value)
            if done: done(value)
        def failure(_message):
            if sip.isdeleted(self) or epoch != self._delivery_epoch: return
            if not concurrent: self._busy = False
            self.status.setText('Operation not confirmed. Draft and IDs retained; inspect or recover before retrying.')
        try: self.bus.submit(self.service.request, method, path, payload, on_result=success, on_error=failure)
        except Exception: failure('')

    def _base(self):
        return '/preparations/' + identifier(self.request_id.text())

    def _selected(self):
        path = self._base()
        if self.plan_id.text(): path += '/plans/' + identifier(self.plan_id.text())
        if self.proposal_id.text():
            if not self.plan_id.text(): raise ValueError('Select the proposal’s plan.')
            path += '/proposals/' + identifier(self.proposal_id.text())
        return path

    def preview(self):
        try:
            self.request_id.setText(uuid.uuid4().hex); self.plan_id.clear(); self.proposal_id.clear(); self.execution_id.clear(); self._review = None
            self._scope = preparation_payload(self.request_id.text(), self.project.currentData(), self.objective.text(),
                {role: field.toPlainText() for role, field in self.file_fields.items()}, self._checks())
            self._preview = None
            self._call('POST', '/preparations/preview', self._scope, lambda value: setattr(self, '_preview', value))
        except (ValueError, TypeError): self.status.setText('Enter an objective, selected files and at least one check.')

    def prepare(self):
        if not self._preview or not self._scope:
            self.status.setText('Preview the scope before preparing.'); return
        try:
            current = preparation_payload(self.request_id.text(), self.project.currentData(), self.objective.text(),
                {role: field.toPlainText() for role, field in self.file_fields.items()}, self._checks())
            if current != self._scope: raise ValueError('Scope changed')
        except (ValueError, TypeError):
            self.status.setText('Scope changed; preview it again before preparing.'); return
        self._call('POST', '/preparations', {**self._scope, 'review_digest': self._preview['review_digest']})

    def plan(self):
        try:
            path = self._base(); self.plan_id.setText(uuid.uuid4().hex); self.proposal_id.clear(); self.execution_id.clear(); self._review = None
            self.timer.start(); self._call('POST', path + '/plans', {'plan_id': self.plan_id.text()})
        except ValueError: self.status.setText('Select a retained preparation first.')

    def review_plan(self):
        try:
            path = self._base() + '/plans/' + identifier(self.plan_id.text()) + '/proposal-review'
            self._review = None
            self._call('GET', path, done=lambda value: setattr(self, '_review', value))
        except ValueError: self.status.setText('Select a retained plan first.')

    def implement(self):
        if not self._review or self._review.get('plan_id') != self.plan_id.text() or self._review.get('request_id') != self.request_id.text():
            self.status.setText('Review the selected plan first.'); return
        path = self._base() + '/plans/' + identifier(self.plan_id.text()) + '/proposals'
        self.proposal_id.setText(uuid.uuid4().hex); self.execution_id.clear(); self.timer.start()
        self._call('POST', path, {'proposal_id': self.proposal_id.text(), 'reviewed_plan_sha256': self._review['reviewed_plan_sha256']})

    def refresh(self):
        try: self._call('GET', self._selected())
        except ValueError: self.status.setText('Enter valid retained IDs to inspect a task.')

    def recover(self):
        try: self._call('POST', self._selected() + '/recover')
        except ValueError: self.status.setText('Enter valid retained IDs to recover a task.')

    def cancel(self):
        try:
            if not self.plan_id.text(): raise ValueError('No generation selected')
            self._call('POST', self._selected() + '/cancel', concurrent=True)
        except ValueError: self.status.setText('Select a plan or proposal generation to cancel.')

    def check_service(self):
        self._coding_enabled = False; self._capability_owner = None
        self._trusted_local_available = False
        self.trusted_ack.setChecked(False); self.trusted_ack.setEnabled(False)
        self._clear_apply_review()
        self._call('GET', '/mode/capabilities', done=self._capabilities_loaded)

    def _capabilities_loaded(self, value):
        owner = value.get('owner')
        self._capability_owner = owner if isinstance(owner, str) and owner.strip() and len(owner) <= 512 else None
        enabled = value.get('enabled') is True and self._capability_owner is not None
        self._coding_enabled = enabled
        self._trusted_local_available = (enabled and value.get('trusted_local_available') is True and
                                        'trusted_host' in value.get('supported_execution_backends', []))
        self.trusted_ack.setChecked(False)
        self.trusted_ack.setEnabled(self.execution_mode.currentData() == 'trusted_host' and self._trusted_local_available)
        reason = value.get('blocked_reason') or 'Isolated checks require a qualified worker; trusted local checks require acknowledgement for each task.'
        self.capabilities.setText(('Coding mode enabled. ' if enabled else 'Coding mode disabled on this service. ') +
            'Python and JavaScript/React. ' + str(reason) +
            (' Trusted local checks are available with per-task acknowledgement.' if self._trusted_local_available else ''))
        if enabled: self.history()

    def history(self, _checked=False, *, more=False):
        try:
            kind = self.history_kind.currentText()
            path = '/preparations'
            if kind in {'Plans', 'Proposals'}:
                path = self._base() + '/plans'
            if kind == 'Proposals': path += '/' + identifier(self.plan_id.text()) + '/proposals'
            if kind == 'Checks':
                path = '/mode/executions?limit=20'
                if more and self._history_cursor: path += '&cursor=' + identifier(self._history_cursor)
            elif more: return
            self._call('GET', path, done=lambda value: self._history_loaded(value, kind, more))
        except ValueError: self.status.setText('Select a saved preparation or plan before loading its child work.')

    def _history_loaded(self, value, kind, append):
        if not append: self.history_rows.clear()
        for record in value.get('items', []):
            if not isinstance(record, dict): continue
            key = {'Preparations': 'request_id', 'Plans': 'plan_id', 'Proposals': 'proposal_id', 'Checks': 'execution_id'}[kind]
            identity = record.get(key, '')
            try: identifier(identity)
            except ValueError: continue
            item = QTreeWidgetItem([str(record.get('objective', kind[:-1])), str(record.get('state', 'Unknown')), identity])
            item.setData(0, Qt.ItemDataRole.UserRole, {**record, 'history_kind': kind})
            self.history_rows.addTopLevelItem(item)
        cursor = value.get('next_cursor')
        self._history_cursor = cursor if kind == 'Checks' and isinstance(cursor, str) and len(cursor) == 32 else None
        self.history_more.setEnabled(self._history_cursor is not None)
        self.history_rows.resizeColumnToContents(0); self.history_rows.resizeColumnToContents(1)

    def _select_history(self, item, _column):
        record = item.data(0, Qt.ItemDataRole.UserRole)
        if not isinstance(record, dict): return
        kind = record.get('history_kind')
        self._review = None; self._preview = None
        if record.get('request_id'): self.request_id.setText(record['request_id'])
        if kind == 'Preparations':
            self.plan_id.clear(); self.proposal_id.clear(); self.execution_id.clear()
        if kind in {'Plans', 'Proposals', 'Checks'} and record.get('plan_id'): self.plan_id.setText(record['plan_id'])
        if kind == 'Plans': self.proposal_id.clear(); self.execution_id.clear()
        if kind in {'Proposals', 'Checks'} and record.get('proposal_id'): self.proposal_id.setText(record['proposal_id'])
        if kind == 'Proposals': self.execution_id.clear()
        if kind == 'Checks':
            self.execution_id.setText(record['execution_id']); self.refresh_checks()
        else: self.refresh()

    def _checks(self):
        checks = []
        for profile, field in self.check_fields.items():
            targets = [line.strip() for line in field.toPlainText().splitlines() if line.strip()]
            if profile == 'npm_script':
                for index, target in enumerate(targets):
                    checks.append({'check_id': f'npm_{index}', 'profile': profile, 'targets': [target]})
            elif targets:
                checks.append({'check_id': profile, 'profile': profile, 'targets': targets})
        return checks

    def _show_evidence(self, checked):
        self.evidence_button.setText('Hide evidence details' if checked else 'Show evidence details')
        self._render(self._record)

    def _render(self, value):
        if self.evidence_button.isChecked():
            self.output.setPlainText(json.dumps(value, indent=2, ensure_ascii=False)); return
        lines = []
        if value.get('objective'): lines += [value['objective'], '']
        lines.append('Status: ' + str(value.get('state', 'Retained records')))
        if value.get('blocked_reason'): lines += ['', 'Checks blocked: ' + str(value['blocked_reason'])]
        lines.append('Verification: ' + str(value.get('verification_status', 'not run')))
        proposal = value.get('proposal', {})
        if isinstance(proposal, dict):
            if proposal.get('summary'): lines += ['', proposal['summary']]
            if proposal.get('diff'): lines += ['', str(proposal['diff'])]
            for step in proposal.get('steps', []): lines.append(str(step.get('path', '')) + ': ' + str(step.get('change', '')))
            for question in proposal.get('questions', []): lines.append('Question: ' + str(question))
        for item in value.get('files', []):
            lines += ['', str(item.get('path', item.get('relative_path', '')))]
            if item.get('diff'): lines.append(str(item['diff']))
        if value.get('diff'): lines += ['', str(value['diff'])]
        if value.get('review_diff'): lines += ['', str(value['review_diff'])]
        for check in value.get('static_checks', []):
            lines.append('Syntax: ' + str(check.get('path', '')) + ' · ' + str(check.get('status', 'not_run')))
        for check in value.get('checks', []):
            lines.append('Check: ' + str(check.get('check_id', check.get('argv', ''))) + ' · ' + str(check.get('returncode', 'not run')))
            for stream in ('stdout', 'stderr'):
                if check.get(stream): lines.append(str(check[stream]))
        for item in value.get('items', []):
            lines += ['', str(item.get('objective', 'Retained task')), str(item.get('request_id', '')), str(item.get('state', ''))]
        mode = value.get('execution_backend', value.get('execution_mode'))
        if mode: lines += ['', 'Check mode: ' + ('Trusted local — same-account filesystem and network access; not VM isolated.' if mode == 'trusted_host' else str(mode))]
        application = value.get('application')
        if isinstance(application, dict): application = application.get('state', application.get('status', 'Recorded; inspect evidence details'))
        lines += ['', 'Application: ' + str(application) if application else 'Original project files have not been applied by this operation.']
        self.output.setPlainText('\n'.join(lines))

    def check_candidate(self):
        try:
            mode = self.execution_mode.currentData()
            if mode == 'trusted_host' and not self._trusted_local_available:
                self.status.setText('Trusted local checks are unavailable on this service. Use Check service to refresh availability.'); return
            acknowledged = mode == 'trusted_host' and self.trusted_ack.isChecked()
            if mode == 'trusted_host' and not acknowledged:
                self.status.setText('Acknowledge same-account filesystem and network access for this task before running trusted local checks.'); return
            payload = {'execution_id': uuid.uuid4().hex, 'request_id': identifier(self.request_id.text()),
                       'plan_id': identifier(self.plan_id.text()), 'proposal_id': identifier(self.proposal_id.text()),
                       'execution_backend': mode, 'trusted_local_ack': acknowledged}
            self.execution_id.setText(payload['execution_id'])
            self.trusted_ack.setChecked(False)
            self.timer.start()
            self._call('POST', '/mode/executions', payload)
        except ValueError: self.status.setText('Select a retained proposal before checking its candidate.')

    def _execution_action(self, method, suffix=''):
        try: self._call(method, '/mode/executions/' + identifier(self.execution_id.text()) + suffix,
                        concurrent=suffix == '/cancel')
        except ValueError: self.status.setText('Select a retained check record first.')

    def _clear_apply_review(self, *_args):
        self._apply_review = None
        if hasattr(self, 'apply_button'): self.apply_button.setEnabled(False)

    def _execution_mode_changed(self, _index):
        self.trusted_ack.setChecked(False)
        self.trusted_ack.setEnabled(self.execution_mode.currentData() == 'trusted_host' and self._trusted_local_available)
        self._clear_apply_review()

    def review_changes(self):
        try:
            execution_id = identifier(self.execution_id.text())
            owner = self._capability_owner
            def reviewed(value):
                token = value.get('review_token')
                if (self.execution_id.text() == execution_id and self._capability_owner == owner and
                    value.get('owner') == owner and value.get('execution_id') == execution_id and
                    value.get('can_apply') is True and isinstance(token, str) and 0 < len(token) <= 4096):
                    self._apply_review = {'execution_id': execution_id, 'owner': owner, 'review_token': token}
                    self.apply_button.setEnabled(self._coding_enabled)
            self._call('POST', '/mode/executions/' + execution_id + '/review', done=reviewed)
        except ValueError: self.status.setText('Select a retained check record first.')

    def apply_changes(self):
        review = self._apply_review
        if (not review or review['execution_id'] != self.execution_id.text() or
            review['owner'] != self._capability_owner or not self._coding_enabled):
            self.status.setText('Review the current verified candidate before applying.'); return
        self._call('POST', '/mode/executions/' + review['execution_id'] + '/apply',
                   {'review_token': review['review_token']})

    def refresh_checks(self): self._execution_action('GET')
    def recover_checks(self): self._execution_action('POST', '/recover')
    def cancel_checks(self): self._execution_action('POST', '/cancel')

    def _poll(self):
        if self._busy: return
        if self.execution_id.text():
            if self._record.get('state') != 'RUNNING': self.timer.stop()
            self.refresh_checks()
        else:
            self.timer.stop(); self.refresh()

    def closeEvent(self, event):
        self.timer.stop()
        self._delivery_epoch += 1
        self._busy = False
        self._coding_enabled = False; self._capability_owner = None
        self._trusted_local_available = False
        self._clear_apply_review()
        self.trusted_ack.setChecked(False)
        # Closing the panel never cancels/replays an owned server task.
        super().closeEvent(event)
