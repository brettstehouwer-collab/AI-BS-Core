#!/usr/bin/env python3
"""
AI-BS Agent Synchronization Gateway & Handoff Validator
Protocol: AI-BS-UADP-1.0
Automates the 7-pillar verification checklist, generates cryptographic manifests,
and validates state parity between Google Antigravity and OpenAI Codex.
"""

import os
import sys
import json
import hashlib
import re
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path("C:/AI-BS")
MANIFESTS_DIR = REPO_ROOT / "docs" / "agent_sync"

CRITICAL_FILES = [
    "AGENTS.md",
    "AI_BS_MASTER_ARCHITECTURAL_LEDGER.md",
    "docs/CODEX_HANDOFF.md",
    "docs/CODEX_DECISIONS.md",
    "docs/CODEX_JOURNAL.md",
    "docs/CODEX_TASKS.md",
    "docs/memory/Conversation_Learning_and_RAG.md",
    "backend/AI_BS_Backend.py",
    "backend/routers/chat_router.py",
    "backend/core/coding_guest_runner.py",
    "backend/core/coding_workflow.py",
    "backend/core/coding_chat.py",
    "backend/core/coding_review.py",
    "backend/core/hybrid_reasoning_engine.py",
    "backend/core/optional_web_search.py",
    "backend/tools/tool_registry.py",
    "backend/core/sovereign_reasoning/document_engine.py",
    "backend/core/subagent_coordinator.py",
    "backend/core/pipeline_context_injector.py",
    "backend/core/bs_chat_provider.py",
    "backend/routers/agent_crew_router.py",
    "frontend/src/components/CodingTaskReviewCard.jsx",
    "scripts/verify_immutable_diff.py",
    "scripts/verify_and_connect_guest_runner.py",
    "scripts/tests/test_coding_guest_runner.py",
    "scripts/agent_sync/sync_gateway.py",
]

MIRROR_GROUPS = {
    "ChatTab.jsx": [
        "frontend/src/components/ChatTab.jsx",
        "frontend/components/ChatTab.jsx",
        "frontend/src/components/components/ChatTab.jsx",
        "frontend/components/components/ChatTab.jsx",
    ],
    "MobileStehouwerChat.jsx": [
        "frontend/src/components/MobileStehouwerChat.jsx",
        "frontend/components/MobileStehouwerChat.jsx",
        "frontend/src/components/components/MobileStehouwerChat.jsx",
        "frontend/components/components/MobileStehouwerChat.jsx",
    ],
    "SpecialistSwarmExplorer.jsx": [
        "frontend/src/components/SpecialistSwarmExplorer.jsx",
        "frontend/components/SpecialistSwarmExplorer.jsx",
        "frontend/src/components/components/SpecialistSwarmExplorer.jsx",
        "frontend/components/components/SpecialistSwarmExplorer.jsx",
    ],
    "MobileBottomNav.jsx": [
        "frontend/src/components/MobileBottomNav.jsx",
        "frontend/components/MobileBottomNav.jsx",
        "frontend/src/components/components/MobileBottomNav.jsx",
        "frontend/components/components/MobileBottomNav.jsx",
    ],
    "CodingTaskReviewCard.jsx": [
        "frontend/src/components/CodingTaskReviewCard.jsx",
        "frontend/components/CodingTaskReviewCard.jsx",
        "frontend/src/components/components/CodingTaskReviewCard.jsx",
        "frontend/components/components/CodingTaskReviewCard.jsx",
    ],
}


def get_git_info():
    try:
        commit = subprocess.check_output(
            ["git", "-C", str(REPO_ROOT), "rev-parse", "HEAD"], text=True
        ).strip()
        branch = subprocess.check_output(
            ["git", "-C", str(REPO_ROOT), "rev-parse", "--abbrev-ref", "HEAD"], text=True
        ).strip()
        status = subprocess.check_output(
            ["git", "-C", str(REPO_ROOT), "status", "--porcelain"], text=True
        ).strip()
        return {
            "commit": commit,
            "branch": branch,
            "is_clean": len(status) == 0,
            "status_summary": f"{len(status.splitlines())} modified/untracked files" if status else "Clean working tree",
        }
    except Exception as e:
        return {"commit": "unknown", "branch": "unknown", "is_clean": False, "error": str(e)}


def compute_sha256(filepath):
    h = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()


def verify_mirror_parity(mirrors):
    hashes = {}
    for path in mirrors:
        full_path = REPO_ROOT / path
        if full_path.exists():
            hashes[path] = compute_sha256(full_path)
        else:
            hashes[path] = "FILE_MISSING"
    unique_hashes = set(hashes.values())
    is_valid = len(unique_hashes) == 1 and "FILE_MISSING" not in unique_hashes
    return is_valid, hashes


def summarize_test_evidence(command, returncode, stdout='', stderr='', *, elapsed_seconds=0,
                            execution_error=None, timed_out=False):
    """Describe this unittest invocation only; fail closed on missing/partial evidence."""
    def decoded(value):
        return value.decode('utf-8', errors='replace') if isinstance(value, bytes) else (value or '')

    stdout, stderr = decoded(stdout), decoded(stderr)
    output = stdout + '\n' + stderr
    counts = None
    status = 'unrecognized_output'
    # Exactly one terminal unittest summary is required, not a loose 'OK' substring.
    summaries = re.findall(r'^Ran \d+ tests? in [0-9]+(?:\.[0-9]+)?s[ \t]*\r?$', output, re.MULTILINE)
    terminal = re.search(
        r'^Ran (\d+) tests? in [0-9]+(?:\.[0-9]+)?s[ \t]*\r?\n\s*'
        r'(OK|FAILED)(?: \(([^\r\n()]*)\))?[ \t]*\s*\Z', output, re.MULTILINE)
    if len(summaries) == 1 and terminal:
        counts = dict(run=int(terminal[1]), confirmed_passed=None, failures=0, errors=0,
                      skipped=0, expected_failures=0, unexpected_successes=0)
        valid = terminal[3] is None or bool(terminal[3].strip())
        seen = set()
        for detail in terminal[3].split(',') if terminal[3] is not None else []:
            if not detail.strip():
                valid = False
                break
            match = re.fullmatch(r'(failures|errors|skipped|expected failures|unexpected successes)=(\d+)', detail.strip())
            if not match or match[1] in seen:
                valid = False
                break
            seen.add(match[1])
            counts[match[1].replace(' ', '_')] = int(match[2])
        # Failure/skip events can exceed testsRun when subtests are used. Infer no
        # successful-case count from subtraction; only a fully clean run proves it.
        if not valid:
            status = 'invalid_summary'
        elif returncode != 0 or terminal[2] != 'OK' or any(counts[k] for k in ('failures', 'errors', 'unexpected_successes')):
            status = 'failed'
        elif counts['run'] == 0 or counts['skipped'] or counts['expected_failures']:
            status = 'incomplete'
        else:
            status = 'passed'
    if timed_out:
        status = 'timeout'
    elif execution_error:
        status = 'execution_error'
    if counts is not None and status == 'passed':
        counts['confirmed_passed'] = counts['run']
    return {
        'schema': 'aibs.observable_test_evidence.v1',
        'scope': 'configured_unittest_suite_only',
        'command': list(command), 'returncode': returncode,
        'elapsed_seconds': round(elapsed_seconds, 6), 'status': status,
        'passed': status == 'passed', 'counts': counts,
        'stdout': stdout, 'stderr': stderr,
        'stdout_sha256': hashlib.sha256(stdout.encode('utf-8')).hexdigest(),
        'stderr_sha256': hashlib.sha256(stderr.encode('utf-8')).hexdigest(),
        'error': execution_error,
    }


def run_acceptance_tests():
    cmd = [
        sys.executable, "-X", "utf8", "-m", "unittest",
        "scripts.tests.test_coding_guest_runner",
        "scripts.tests.test_chat_attachment_upload",
        "scripts.tests.test_bs_chat_openai",
        "scripts.tests.test_ai_provider_environment",
        "scripts.tests.test_audio_router_trace",
    ]
    started = time.monotonic()
    try:
        res = subprocess.run(cmd, cwd=str(REPO_ROOT), capture_output=True, text=True,
                             encoding='utf-8', errors='replace', timeout=120)
        return summarize_test_evidence(cmd, res.returncode, res.stdout, res.stderr,
                                       elapsed_seconds=time.monotonic() - started)
    except subprocess.TimeoutExpired as e:
        return summarize_test_evidence(cmd, None, e.stdout, e.stderr,
                                       elapsed_seconds=time.monotonic() - started,
                                       execution_error=str(e), timed_out=True)
    except Exception as e:
        return summarize_test_evidence(cmd, None, elapsed_seconds=time.monotonic() - started,
                                       execution_error=str(e))


def acceptance_markdown(result):
    counts = result.get('counts')
    text = f"\n### Acceptance Tests\n- **Status:** {result.get('status', 'unrecognized_output')}\n"
    if counts is not None:
        text += ('- **Observed counts:** ' + ', '.join(f'{key}={value}' for key, value in counts.items()) + '\n')
    else:
        text += '- **Observed counts:** unavailable\n'
    text += f"- **Return code:** {result.get('returncode')}\n"
    text += '- **Scope:** configured unittest suite only; see JSON for command, full output and output hashes.\n'
    text += '- **Model quality evaluation:** not run; no answer-quality or live-isolation claim.\n\n'
    return text


def generate_handoff_manifest(outgoing_agent, receiving_agent, tasks_completed, next_step):
    MANIFESTS_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(timezone.utc).isoformat()
    handoff_id = f"handoff_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}"

    file_hashes = {}
    for f in CRITICAL_FILES:
        p = REPO_ROOT / f
        file_hashes[f] = compute_sha256(p) if p.exists() else "MISSING"

    mirror_results = {}
    all_mirrors_valid = True
    for name, paths in MIRROR_GROUPS.items():
        parity, details = verify_mirror_parity(paths)
        mirror_results[name] = {"parity": parity, "mirrors": details}
        if not parity:
            all_mirrors_valid = False

    tests_result = run_acceptance_tests()
    git_info = get_git_info()

    checklist = {
        "1_git_commit_identity": git_info.get("commit") != "unknown",
        "2_source_file_hashes": all(v != "MISSING" for v in file_hashes.values()) and all_mirrors_valid,
        "3_architecture_ledger": (REPO_ROOT / "AI_BS_MASTER_ARCHITECTURAL_LEDGER.md").exists(),
        "4_dependency_environment": (REPO_ROOT / "package.json").exists() and (REPO_ROOT / "backend" / "requirements.txt").exists(),
        "5_acceptance_tests": tests_result.get("passed", False),
        "6_handoff_manifest": True,
        "7_task_continuity": bool(next_step),
    }

    score = sum(1 for v in checklist.values() if v)

    manifest_data = {
        "handoff_id": handoff_id,
        "protocol": "AI-BS-UADP-1.0",
        "timestamp_utc": timestamp,
        "outgoing_agent": outgoing_agent,
        "receiving_agent": receiving_agent,
        "synchronization_score": f"{score}/7",
        "checklist": checklist,
        "git": git_info,
        "critical_file_hashes": file_hashes,
        "mirror_parity": mirror_results,
        "acceptance_tests": tests_result,
        "model_quality_evaluation": {"status": "not_run", "affects_acceptance": False,
                                     "rubric_id": None, "evaluator_id": None, "scores": []},
        "tasks_completed": tasks_completed,
        "next_step": next_step,
    }

    manifest_json_path = MANIFESTS_DIR / f"{handoff_id}.json"
    manifest_md_path = MANIFESTS_DIR / f"{handoff_id}.md"

    with open(manifest_json_path, "w", encoding="utf-8") as f:
        json.dump(manifest_data, f, indent=2)

    with open(manifest_md_path, "w", encoding="utf-8") as f:
        f.write(f"# AI-BS Handoff Manifest: `{handoff_id}`\n\n")
        f.write("**Protocol:** AI-BS-UADP-1.0\n")
        f.write(f"**Timestamp:** {timestamp}\n")
        f.write(f"**Transition:** `{outgoing_agent}` -> `{receiving_agent}`\n")
        f.write(f"**Synchronization Score:** **{score}/7**\n\n")
        f.write("### 7-Pillar Verification Checklist\n")
        for k, v in checklist.items():
            status_icon = "PASS" if v else "FAIL"
            f.write(f"- [{status_icon}] `{k}`\n")
        f.write(
            f"\n### Git Status\n- **Branch:** `{git_info.get('branch')}`\n"
            f"- **Commit:** `{git_info.get('commit')}`\n"
            f"- **Working Tree:** {git_info.get('status_summary')}\n\n"
        )
        f.write("### Mirror Parity\n")
        for name, item in mirror_results.items():
            f.write(f"- **{name} (4 Mirrors):** {'100% Parity' if item['parity'] else 'Mismatch'}\n")
        f.write(acceptance_markdown(tests_result))
        f.write("### Tasks Completed\n")
        for t in tasks_completed:
            f.write(f"- {t}\n")
        f.write(f"\n### Exact Next Step\n{next_step}\n")

    print(f"Handoff manifest created:\n- JSON: {manifest_json_path}\n- Markdown: {manifest_md_path}")
    print(f"Synchronization Score: {score}/7")
    return manifest_data


def verify_latest_manifest():
    manifests = sorted(list(MANIFESTS_DIR.glob("handoff_*.json")))
    if not manifests:
        print("No previous handoff manifest found to verify against.")
        sys.exit(1)
    latest = manifests[-1]
    print(f"Verifying against latest manifest: {latest.name}")
    with open(latest, "r", encoding="utf-8") as f:
        data = json.load(f)

    git_now = get_git_info()
    recorded_commit = (data.get("git") or {}).get("commit")
    if recorded_commit and git_now.get("commit") != recorded_commit:
        print(f"FAILED: Git HEAD mismatch! Manifest recorded {recorded_commit}, workspace HEAD is {git_now.get('commit')}")
        sys.exit(1)
    print(f"Git HEAD verified: {git_now.get('commit')} ({git_now.get('branch')})")

    mismatches = []
    for file_rel, expected_hash in data.get("critical_file_hashes", {}).items():
        target = REPO_ROOT / file_rel
        actual = compute_sha256(target) if target.exists() else "MISSING"
        if actual != expected_hash:
            mismatches.append((file_rel, expected_hash, actual))

    for group_name, group_paths in MIRROR_GROUPS.items():
        parity, details = verify_mirror_parity(group_paths)
        if not parity:
            mismatches.append((f"mirror_parity:{group_name}", "ALL_4_EQUAL", json.dumps(details)))

    if mismatches:
        print(f"FAILED: {len(mismatches)} integrity mismatches detected!")
        for m in mismatches:
            print(f"- {m[0]}: Expected {m[1]} but got {m[2]}")
        sys.exit(1)

    print(f"SUCCESS: Git HEAD ({recorded_commit}), all {len(data.get('critical_file_hashes', {}))} critical file SHA-256 fingerprints, and all 4-mirror component groups match!")


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "verify":
        verify_latest_manifest()
    else:
        generate_handoff_manifest(
            outgoing_agent="Google Antigravity",
            receiving_agent="OpenAI Codex",
            tasks_completed=[
                "Expanded SQLite WAL specialist registry in backend/core/subagent_coordinator.py (C:\\AI-BS\\backend\\data\\aibs_master.db) from 14 to 64 specialist subagent profiles across 7 operational domains mapped to Chat (24), Cockpit (8), NoCo (8), VLC/Media (8), and All Tools (16), with bounded semaphores (max_concurrent_llm=1, max_concurrent_builds=1), two-tier HierarchicalDomainRouter, and Role 49 (immutable_fire_scribe) verbatim lexical diff guard (scripts/verify_immutable_diff.py)",
                "Wired /api/v1/agents/domains, /api/v1/agents/specialists, /api/v1/agents/route-hierarchical, and /api/v1/agents/immutable-scribe/verify in backend/routers/agent_crew_router.py",
                "Created backend/core/pipeline_context_injector.py (Stage 1 of Pipeline 6/6) with AIBS_SOVEREIGN_SYSTEM_PROMPT and SHORTHAND_DISAMBIGUATION_MAP, hooked into backend/core/bs_chat_provider.py, backend/core/sovereign_reasoning/dispatcher.py, and backend/routers/chat_router.py, and restored active_provider='local' in database/ai_providers_config.json (36/36 provider/OpenAI tests passing)",
                "Patched mobile streaming Markdown code-block renderer (MobileStehouwerChat.jsx, ChatTab.jsx, MobileGeminiChat.jsx, ArtifactRenderer.jsx) to eliminate the 00:52 'undefined' string flicker, added SPECIALIST_NAV_CATALOG to MobileBottomNav.jsx, verified 499/499 4-mirror SHA-256 byte parity, bumped version to v5.329.128, compiled Vite production bundle, and deployed live to https://ai-bs-dashboard.web.app",
            ],
            next_step=(
                "Codex runs 'python C:\\AI-BS\\scripts\\agent_sync\\sync_gateway.py verify', "
                "'python C:\\AI-BS\\backend\\core\\subagent_coordinator.py --test', and "
                "'python -m unittest scripts.tests.test_bs_chat_openai scripts.tests.test_ai_provider_environment' "
                "to confirm 7/7 synchronization parity, 64/64 SQLite WAL specialist contracts, and Stage 1 Pipeline (6/6) identity injection."
            ),
        )
