"""
agent_state.py — Step-level checkpoint manager for AI-BS Matrix multi-step workflows.

Guarantees:
- Any multi-step agent workflow persists step status to state.json.
- On restart, the agent can query resume_from() to skip already-completed steps.
- Failure diagnostics are persisted so trainer_daemon.py can learn from them.

Schema extension added to state.json
-------------------------------------
{
  "tasks": {
    "<task_id>": {
      "created_at": "...",
      "description": "...",
      "steps": {
        "<step_id>": {
          "status": "done" | "in_progress" | "failed" | "skipped",
          "description": "...",
          "started_at": "...",
          "completed_at": "...",
          "result": { ...ToolResult.to_dict() }  # populated on complete/fail
        }
      }
    }
  }
}

The pre-existing top-level keys (continuous_heuristic_integration,
last_sync_timestamp) are preserved and never modified.

Usage
-----
    state = AgentState("git_push_task")
    if state.resume_from():
        start_step = state.resume_from()
    else:
        start_step = "step_1"

    state.begin_step("step_1", "Create backup tag")
    result = run_git_backup_tag()
    if result.ok:
        state.complete_step("step_1", result)
    else:
        state.fail_step("step_1", result)
        raise RuntimeError("Cannot proceed — backup tag failed")
"""

from __future__ import annotations

import json
import logging
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

STATE_PATH = Path(__file__).parent / "state.json"
_lock = threading.Lock()


# ---------------------------------------------------------------------------
# Low-level state.json I/O (thread-safe)
# ---------------------------------------------------------------------------

def _read_state() -> Dict[str, Any]:
    """Read state.json, return empty dict on missing or corrupt file."""
    if not STATE_PATH.exists():
        return {}
    try:
        with STATE_PATH.open("r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError) as exc:
        logger.warning("agent_state: could not read state.json — %s", exc)
        return {}


def _write_state(data: Dict[str, Any]) -> None:
    """Atomically write state.json (write to .tmp then rename)."""
    tmp = STATE_PATH.with_suffix(".tmp")
    try:
        with tmp.open("w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        tmp.replace(STATE_PATH)
    except OSError as exc:
        logger.error("agent_state: failed to write state.json — %s", exc)
        tmp.unlink(missing_ok=True)


# ---------------------------------------------------------------------------
# AgentState
# ---------------------------------------------------------------------------

class AgentState:
    """
    Step-level checkpoint manager.

    Each instance is scoped to a single logical task (identified by task_id).
    Multiple tasks can coexist in state.json under the "tasks" key.

    Parameters
    ----------
    task_id : str
        Unique identifier for this agent workflow (e.g. "git_push_20260704").
    description : str
        Human-readable description of the task (stored for observability).
    """

    def __init__(self, task_id: str, description: str = "") -> None:
        self.task_id = task_id
        self.description = description
        self._ensure_task_exists()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def begin_step(self, step_id: str, description: str = "") -> None:
        """
        Record that a step is now in-progress.
        Call this immediately before executing the step.
        """
        with _lock:
            data = _read_state()
            task = data.setdefault(
                "tasks", {}).setdefault(
                self.task_id, self._new_task())
            task["steps"][step_id] = {
                "status": "in_progress",
                "description": description,
                "started_at": _now(),
                "completed_at": None,
                "result": None,
            }
            _write_state(data)
        logger.debug("agent_state [%s] begin_step: %s", self.task_id, step_id)

    def complete_step(self, step_id: str, result: Any = None) -> None:
        """
        Mark a step as successfully completed.

        Parameters
        ----------
        result : ToolResult or None
            If a ToolResult is provided its to_dict() is persisted.
        """
        self._update_step(step_id, "done", result)
        logger.info(
            "agent_state [%s] complete_step: %s ✓",
            self.task_id,
            step_id)

    def fail_step(self, step_id: str, result: Any = None) -> None:
        """
        Mark a step as failed and persist the ToolResult / DiagnosticTrace.
        """
        self._update_step(step_id, "failed", result)
        logger.warning(
            "agent_state [%s] fail_step: %s ✗",
            self.task_id,
            step_id)

    def skip_step(self, step_id: str, reason: str = "") -> None:
        """Mark a step as intentionally skipped (already completed in prior run)."""
        with _lock:
            data = _read_state()
            task = data.get("tasks", {}).get(self.task_id, {})
            task.setdefault("steps", {})[step_id] = {
                "status": "skipped",
                "description": reason,
                "started_at": None,
                "completed_at": _now(),
                "result": None,
            }
            _write_state(data)
        logger.info(
            "agent_state [%s] skip_step: %s (reason: %s)",
            self.task_id,
            step_id,
            reason)

    def resume_from(self) -> Optional[str]:
        """
        Return the step_id of the first step that is NOT 'done' or 'skipped'.
        Returns None if all steps are completed (or no steps have been recorded).

        Usage pattern
        -------------
            resume_point = state.resume_from()
            for step_id, fn in steps:
                if resume_point and step_id != resume_point:
                    state.skip_step(step_id, reason="prior run completed")
                    continue
                resume_point = None  # clear once we've caught up
                state.begin_step(step_id)
                result = fn()
                state.complete_step(step_id, result)
        """
        with _lock:
            data = _read_state()
            steps = data.get(
                "tasks",
                {}).get(
                self.task_id,
                {}).get(
                "steps",
                {})
        for step_id, meta in steps.items():
            if meta.get("status") not in ("done", "skipped"):
                logger.info(
                    "agent_state [%s] resume_from: step '%s' (status=%s)",
                    self.task_id, step_id, meta.get("status"),
                )
                return step_id
        return None

    def step_status(self, step_id: str) -> Optional[str]:
        """Return the current status of a step, or None if not recorded."""
        with _lock:
            data = _read_state()
            return (
                data.get("tasks", {})
                    .get(self.task_id, {})
                    .get("steps", {})
                    .get(step_id, {})
                    .get("status")
            )

    def all_done(self) -> bool:
        """Return True if every recorded step is 'done' or 'skipped'."""
        return self.resume_from() is None

    def clear_task(self) -> None:
        """
        Remove this task's checkpoint from state.json after successful completion.
        Call this at the end of a fully successful workflow.
        """
        with _lock:
            data = _read_state()
            data.get("tasks", {}).pop(self.task_id, None)
            _write_state(data)
        logger.info("agent_state [%s] cleared (task complete).", self.task_id)

    def task_summary(self) -> Dict[str, Any]:
        """Return a dict summary of this task's step statuses for observability."""
        with _lock:
            data = _read_state()
            return data.get("tasks", {}).get(self.task_id, {})

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _ensure_task_exists(self) -> None:
        with _lock:
            data = _read_state()
            tasks = data.setdefault("tasks", {})
            if self.task_id not in tasks:
                tasks[self.task_id] = self._new_task()
                _write_state(data)

    def _new_task(self) -> Dict[str, Any]:
        return {
            "created_at": _now(),
            "description": self.description,
            "steps": {},
        }

    def _update_step(self, step_id: str, status: str, result: Any) -> None:
        result_dict = None
        if result is not None:
            result_dict = result.to_dict() if hasattr(result, "to_dict") else str(result)
        with _lock:
            data = _read_state()
            step = (
                data.get("tasks", {})
                    .get(self.task_id, {})
                    .get("steps", {})
                    .get(step_id, {})
            )
            step["status"] = status
            step["completed_at"] = _now()
            step["result"] = result_dict
            # Ensure nested path exists in case begin_step was never called
            data.setdefault(
                "tasks",
                {}).setdefault(
                self.task_id,
                self._new_task())
            data["tasks"][self.task_id]["steps"][step_id] = step
            _write_state(data)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


# ---------------------------------------------------------------------------
# Convenience: list all active tasks from state.json
# ---------------------------------------------------------------------------

def list_active_tasks() -> List[str]:
    """Return task_ids that have at least one non-completed step."""
    data = _read_state()
    active = []
    for task_id, task in data.get("tasks", {}).items():
        steps = task.get("steps", {})
        if any(s.get("status") not in ("done", "skipped")
               for s in steps.values()):
            active.append(task_id)
    return active
