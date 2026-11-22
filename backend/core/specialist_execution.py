"""Bounded execution for registered, trusted host verification commands.

This is process containment, not VM isolation. It grants no inference or
untrusted-code authority and starts no background worker at import time.
"""
import hashlib
import json
import os
from pathlib import Path
import queue
import subprocess
import threading
import time
import uuid

from core.coding_locks import record_lock
from core.coding_process import run_bounded_check


def check_readiness(contract, command=None):
    """Inspect configuration without creating a missing workspace or running it."""
    argv = command if command is not None else contract.completion_check_cmd
    if not contract.active:
        return 'unconfigured_check', 'This specialist is inactive.'
    if not isinstance(argv, (list, tuple)) or not argv or any(not isinstance(a, str) or not a for a in argv):
        return 'unconfigured_check', 'No verification command is configured.'
    workspace = Path(contract.workspace_scope)
    if not workspace.is_dir():
        return 'unconfigured_check', 'The configured verification workspace is unavailable.'
    # Script operands are data paths, not executable shell fragments. Do not
    # interpret source passed to Python -c or any expression after it as a path.
    operands = []
    for index, arg in enumerate(argv[1:], 1):
        if argv[index - 1].lower() in ('-c', '-command', '-m'):
            continue
        if arg.lower().endswith(('.py', '.ps1', '.bat', '.cmd')):
            operands.append(arg)
    for arg in operands:
        script = Path(arg)
        if not script.is_absolute():
            script = workspace / script
        if not script.is_file():
            return 'unconfigured_check', 'The configured verification script is unavailable.'
    return 'configured', ''


class SpecialistExecutionCoordinator:
    """Priority admission shared by callers; OS lock serializes host gate jobs.

    enqueue_job preserves the existing CLI interface. A check becomes eligible
    when execute_verified_check is called; waiting caller threads are workers.
    No dormant or abandoned reservation blocks a ready check.
    """
    def __init__(self, db, max_queue_size=64, max_concurrent_llm=1,
                 max_concurrent_builds=1, process_runner=None):
        if max_queue_size < 1 or max_concurrent_builds != 1 or max_concurrent_llm != 1:
            raise ValueError('Verification uses one host gate slot and a positive bounded queue.')
        self.db = db
        self.job_queue = queue.PriorityQueue(maxsize=max_queue_size)
        self._condition = threading.Condition()
        self._pending = {}
        self._ready = set()
        self._cancelled = set()
        self._running = None
        self._reservation_limit = max_queue_size * 2
        self._runner = process_runner or run_bounded_check
        self._resource_path = Path(db.db_path).parent / 'specialist_runtime' / 'host-verification.lock'

    def enqueue_job(self, agent_id, task_prompt, priority=5):
        if isinstance(priority, bool) or not isinstance(priority, int) or not 1 <= priority <= 5:
            raise ValueError('Priority must be between 1 and 5.')
        spec = self.db.get_specialist(agent_id)
        if spec is None or not spec.active:
            raise ValueError('Specialist is unavailable or inactive.')
        with self._condition:
            self._expire_reservations()
            job = 'job_' + uuid.uuid4().hex[:10]
            ticket = (priority, time.monotonic(), job)
            self.job_queue.put_nowait(ticket)
            self._pending[job] = (ticket, agent_id)
            self._condition.notify_all()
            return job

    def _remove_ticket(self, job):
        retained = []
        while not self.job_queue.empty():
            item = self.job_queue.get_nowait()
            self.job_queue.task_done()
            if item[2] != job:
                retained.append(item)
        for item in retained:
            self.job_queue.put_nowait(item)

    def _expire_reservations(self):
        for job, (ticket, _) in list(self._pending.items()):
            if job not in self._ready and job != self._running and (
                time.monotonic() - ticket[1] > 1800 or
                (job in self._cancelled and len(self._pending) > self._reservation_limit)):
                self._remove_ticket(job)
                self._pending.pop(job, None)
                self._cancelled.discard(job)

    def cancel_job(self, job_id):
        with self._condition:
            if job_id in self._pending or job_id == self._running:
                self._cancelled.add(job_id)
                if job_id not in self._ready and job_id != self._running:
                    self._remove_ticket(job_id)
                self._condition.notify_all()

    def is_cancelled(self, job_id):
        with self._condition:
            return job_id in self._cancelled

    def execute_verified_check(self, job_id, contract, timeout_sec=600, override_cmd=None):
        if isinstance(timeout_sec, bool) or not isinstance(timeout_sec, (int, float)) or not 1 <= timeout_sec <= 1800:
            raise ValueError('Timeout must be between 1 and 1800 seconds.')
        argv = list(override_cmd or contract.completion_check_cmd)
        admitted = False
        with self._condition:
            ticket = self._pending.get(job_id)
            if ticket is None or ticket[1] != contract.agent_id or job_id in self._ready:
                raise ValueError('Verification job does not match its reservation.')
            started = ticket[0][1]
            deadline = started + timeout_sec
            self._ready.add(job_id)
        try:
            admission_status = None
            with self._condition:
                while True:
                    if job_id in self._cancelled:
                        admission_status = 'cancelled'
                        break
                    if time.monotonic() >= deadline:
                        admission_status = 'timeout'
                        break
                    candidates = [self._pending[j][0] for j in self._ready]
                    if self._running is None and candidates and min(candidates)[2] == job_id:
                        self._running = job_id
                        self._remove_ticket(job_id)
                        admitted = True
                        break
                    self._condition.wait(min(.05, max(.001, deadline - time.monotonic())))
            if admission_status:
                return self._record(job_id, contract, argv, started, admission_status,
                                    -99 if admission_status == 'cancelled' else -1, '',
                                    'Verification stopped while waiting for admission: ' + admission_status)
            status, reason = check_readiness(contract, argv)
            if status != 'configured':
                return self._record(job_id, contract, argv, started, status, -4, '', reason)
            while time.monotonic() < deadline and not self.is_cancelled(job_id):
                try:
                    with record_lock(self._resource_path):
                        if self.is_cancelled(job_id):
                            break
                        remaining = deadline - time.monotonic()
                        if remaining <= 0:
                            break
                        before = self._capture_command_state(contract, argv)
                        remaining = deadline - time.monotonic()
                        if remaining <= 0:
                            break
                        result = self._runner(argv, cwd=contract.workspace_scope, env=os.environ.copy(),
                            timeout_seconds=remaining, output_limit=1048576,
                            cancelled=lambda: self.is_cancelled(job_id))
                        error = result.get('error')
                        status = ('cancelled' if error == 'cancelled' else 'timeout' if error == 'timeout'
                                  else 'execution_error' if error else 'passed' if result.get('returncode') == 0 else 'failed')
                        rc = result.get('returncode')
                        rc = rc if isinstance(rc, int) and (not error or rc != 0) else -1
                        stderr = result.get('stderr') or ''
                        if error:
                            stderr = (stderr + '\n' + str(error)).strip()
                        return self._record(job_id, contract, argv, started, status, rc, result.get('stdout') or '', stderr, before)
                except ValueError as exc:
                    if 'holds the coding task or repository lock' not in str(exc):
                        raise
                    time.sleep(min(.025, max(.001, deadline - time.monotonic())))
            status = 'cancelled' if self.is_cancelled(job_id) else 'timeout'
            return self._record(job_id, contract, argv, started, status, -99 if status == 'cancelled' else -1,
                                '', 'Verification stopped before process admission: ' + status)
        except Exception as exc:
            return self._record(job_id, contract, argv, started, 'execution_error', -2, '', type(exc).__name__ + ': ' + str(exc))
        finally:
            with self._condition:
                if not admitted:
                    self._remove_ticket(job_id)
                if self._running == job_id:
                    self._running = None
                self._ready.discard(job_id)
                self._pending.pop(job_id, None)
                self._cancelled.discard(job_id)
                self._condition.notify_all()

    def _capture_command_state(self, contract, argv):
        revision = 'unknown'
        try:
            probe = subprocess.run(['git', 'rev-parse', 'HEAD'], cwd=contract.workspace_scope,
                                   capture_output=True, text=True, timeout=5)
            if probe.returncode == 0:
                revision = probe.stdout.strip()
        except (OSError, subprocess.SubprocessError):
            pass
        # These are pre-launch observations, not a frozen whole-project snapshot.
        pins = {'argv': argv, 'runtime_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}
        for value in argv:
            p = Path(value)
            if p.suffix.lower() in ('.py', '.ps1', '.bat', '.cmd'):
                if not p.is_absolute():
                    p = Path(contract.workspace_scope) / p
                if p.is_file():
                    pins[str(p)] = hashlib.sha256(p.read_bytes()).hexdigest()
        return revision, pins

    def _record(self, job, contract, argv, started, status, rc, stdout, stderr, before=None):
        duration = round(time.monotonic() - started, 3)
        revision, pins = before if before is not None else self._capture_command_state(contract, argv)
        _, after = self._capture_command_state(contract, argv) if before is not None else (revision, pins)
        drift = before is not None and pins != after
        if drift:
            status, rc = 'source_changed', -5
            stderr = (stderr + '\nCommand/runtime bytes changed during verification; result is unqualified.').strip()
        digest = hashlib.sha256(json.dumps(pins, sort_keys=True).encode()).hexdigest()
        evidence_revision = revision + ';command-runtime-sha256=' + digest
        self.db.record_evidence(job_id=job, agent_id=contract.agent_id,
            engine_target=contract.engine_target.value, source_revision=evidence_revision,
            command=argv, returncode=rc, stdout=stdout, stderr=stderr, duration=duration)
        return {'job_id': job, 'agent_id': contract.agent_id, 'status': status,
                'verified_pass': status == 'passed' and rc == 0, 'returncode': rc,
                'source_revision': evidence_revision, 'source_fingerprint_scope': 'prelaunch-command-and-on-disk-runtime-only',
                'source_changed_during_execution': drift,
                'duration_sec': duration, 'stdout': stdout, 'stderr': stderr}
