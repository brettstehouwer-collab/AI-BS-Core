"""Pure response formatting; importing this module performs no operational I/O."""


def mission_response(mission: dict, field: str = "mission") -> dict:
    """Expose the actual outcome, with success requiring completed task records."""
    if field not in ("mission", "result"):
        raise ValueError("Unsupported mission response field")
    if not isinstance(mission, dict):
        return {"status": "error", "message": "Mission engine returned an invalid result."}

    state = mission.get("status")
    if state == "completed":
        tasks = mission.get("tasks")
        valid = (
            isinstance(tasks, list) and bool(tasks)
            and type(mission.get("total_tasks")) is int
            and type(mission.get("completed_tasks")) is int
            and mission["completed_tasks"] == mission["total_tasks"] == len(tasks)
            and all(isinstance(task, dict) and task.get("status") == "completed" for task in tasks)
        )
        if valid:
            return {"status": "success", field: mission}
        message = "Mission completion was reported without matching completed task records."
    elif state in ("failed", "blocked", "unimplemented", "planned", "running"):
        return {"status": state, field: mission}
    else:
        message = "Mission engine returned an unrecognized state."

    # Preserve the claimed status while ensuring the UI cannot display a false
    # completion badge for a contradictory or malformed response.
    actual = {**mission, "reported_status": state, "status": "failed", "error": message}
    return {"status": "error", field: actual, "message": message}
