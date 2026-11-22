"""
reasoning_logger.py — Post-task ChromaDB embedder for AI-BS Matrix.

After every successful or failed agent task, this logger embeds the full
reasoning trace (prompt → decision steps → outcome) into the 'reasoning_traces'
ChromaDB collection.

This is what makes the Infinite Learning Memory actually grow:
- Success traces teach the system what good decision paths look like.
- Failure traces (with DiagnosticTrace) teach trainer_daemon.py what to avoid.

Collection: 'reasoning_traces' (separate from 'heuristics' routing data so
routing classification is not polluted by execution traces).

Embedding Model: nomic-embed-text via Ollama (same pipeline as memory_daemon).

Usage
-----
    from reasoning_logger import ReasoningLogger
    from tool_result import ok, DiagnosticTrace

    rl = ReasoningLogger()

    # After a successful workflow
    rl.log_success(
        task_id="git_push_20260704",
        prompt="Push current branch to Vercel remote",
        decision_steps=[
            "1. Fetch remote heads to verify branch exists",
            "2. Create backup tag before overwrite",
            "3. Run npm build — exit 0",
            "4. Push with --force-with-lease",
        ],
        outcome=ok(tool_name="git_push"),
    )

    # After a failure
    rl.log_failure(
        task_id="npm_build_fail_20260704",
        prompt="Build frontend for production",
        diagnostics=DiagnosticTrace(
            error_type="BuildError",
            message="vite not found in PATH",
            suggested_fix="Run npm ci before npm run build",
        ),
    )
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

WORKSPACE_ROOT = Path(__file__).parent.resolve()

# Paths for fallback storage
REASONING_TRACES_PENDING = WORKSPACE_ROOT / "reasoning_traces_pending.jsonl"
REASONING_TRACES_DB = WORKSPACE_ROOT / "reasoning_traces_pending.db"

# Ensure SQLite DB and table exist


def _init_reasoning_db():
    conn = sqlite3.connect(REASONING_TRACES_DB)
    try:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS pending (
                id TEXT PRIMARY KEY,
                document TEXT NOT NULL,
                metadata TEXT NOT NULL
            )
            """
        )
        conn.commit()
    finally:
        conn.close()


_init_reasoning_db()

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

COLLECTION_NAME = "reasoning_traces"
OLLAMA_EMBED_URL = os.getenv(
    "OLLAMA_EMBED_URL",
    "http://127.0.0.1:11434/api/embed")
EMBED_MODEL = os.getenv("MEMORY_EMBED_MODEL", "nomic-embed-text")
CHROMA_HOST = os.getenv("MEMORY_CHROMA_HOST", "localhost")
CHROMA_PORT = int(os.getenv("MEMORY_CHROMA_PORT", "8001"))
DB_DIR = WORKSPACE_ROOT / "stehouwer_vector_memory"

# ---------------------------------------------------------------------------
# Lazy imports — daemon still boots if deps are missing
# ---------------------------------------------------------------------------

try:
    import httpx
    _HTTPX_AVAILABLE = True
except ImportError:
    _HTTPX_AVAILABLE = False
    logger.warning("httpx not installed — ReasoningLogger will skip embedding")

try:
    import chromadb  # type: ignore
    _CHROMA_AVAILABLE = True
except ImportError:
    _CHROMA_AVAILABLE = False
    logger.warning(
        "chromadb not installed — ReasoningLogger will skip vector storage")


# ---------------------------------------------------------------------------
# ReasoningLogger
# ---------------------------------------------------------------------------

class ReasoningLogger:
    """
    Embeds agent reasoning traces into ChromaDB after task completion.

    Uses the persistent local ChromaDB client (same path as memory_daemon)
    so no additional server is required.

    Thread-safety: each call opens/closes the HTTP client and ChromaDB
    connection independently. Safe for concurrent daemon use.
    """

    def __init__(self) -> None:
        self._collection = None
        self._init_collection()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def log_success(
        self,
        task_id: str,
        prompt: str,
        decision_steps: List[str],
        outcome: Any,  # ToolResult
    ) -> bool:
        """
        Embed a successful reasoning trace into 'reasoning_traces'.

        Parameters
        ----------
        task_id : str
            Unique workflow identifier (e.g. "git_push_20260704").
        prompt : str
            The original user prompt or orchestrator instruction.
        decision_steps : List[str]
            Ordered list of decisions made during the workflow.
        outcome : ToolResult
            The final ToolResult of the completed workflow.

        Returns
        -------
        bool
            True if the trace was successfully embedded and stored.
        """
        text = self._build_success_text(prompt, decision_steps, outcome)
        metadata = {
            "task_id": task_id,
            "outcome": "success",
            "timestamp": _now(),
            "status": getattr(outcome, "status", 200),
            "tool_name": getattr(outcome, "tool_name", "unknown"),
        }
        return self._embed_and_store(
            task_id=task_id, text=text, metadata=metadata)

    def log_failure(
        self,
        task_id: str,
        prompt: str,
        diagnostics: Any,  # DiagnosticTrace
    ) -> bool:
        """
        Embed a failure trace into 'reasoning_traces'.

        Parameters
        ----------
        task_id : str
            Unique workflow identifier.
        prompt : str
            The original user prompt or orchestrator instruction.
        diagnostics : DiagnosticTrace
            The structured failure record from the failed ToolResult.

        Returns
        -------
        bool
            True if the trace was successfully embedded and stored.
        """
        text = self._build_failure_text(prompt, diagnostics)
        metadata = {
            "task_id": task_id,
            "outcome": "failure",
            "timestamp": _now(),
            "error_type": getattr(diagnostics, "error_type", "Unknown"),
            "suggested_fix": getattr(diagnostics, "suggested_fix", ""),
        }
        return self._embed_and_store(
            task_id=f"{task_id}_fail", text=text, metadata=metadata
        )

    # ------------------------------------------------------------------
    # Internal: text assembly
    # ------------------------------------------------------------------

    @staticmethod
    def _build_success_text(
            prompt: str,
            steps: List[str],
            outcome: Any) -> str:
        steps_text = "\n".join(f"  {i + 1}. {s}" for i, s in enumerate(steps))
        outcome_str = getattr(outcome, "stdout", str(outcome))[:300]
        return (
            f"[SUCCESS TRACE]\n"
            f"Prompt: {prompt}\n"
            f"Decision steps:\n{steps_text}\n"
            f"Outcome (stdout): {outcome_str}"
        )

    @staticmethod
    def _build_failure_text(prompt: str, diagnostics: Any) -> str:
        error_type = getattr(diagnostics, "error_type", "Unknown")
        message = getattr(diagnostics, "message", str(diagnostics))
        fix = getattr(diagnostics, "suggested_fix", "No fix suggested")
        context = getattr(diagnostics, "context", {})
        return (
            f"[FAILURE TRACE]\n"
            f"Prompt: {prompt}\n"
            f"Error type: {error_type}\n"
            f"Message: {message}\n"
            f"Context: {json.dumps(context)}\n"
            f"Suggested fix: {fix}"
        )

    # ------------------------------------------------------------------
    # Internal: embedding + ChromaDB upsert
    # ------------------------------------------------------------------

    def _embed_and_store(
        self, task_id: str, text: str, metadata: Dict[str, Any]
    ) -> bool:
        vector = self._embed(text)
        doc_id = _make_id(task_id, text)

        if self._collection is not None and vector is not None:
            try:
                self._collection.upsert(
                    ids=[doc_id],
                    documents=[text],
                    embeddings=[vector],
                    metadatas=[metadata],
                )
                logger.info(
                    "ReasoningLogger: stored trace '%s' → collection '%s'",
                    doc_id, COLLECTION_NAME,
                )
                return True
            except Exception as exc:
                logger.warning(
                    "ReasoningLogger: ChromaDB upsert failed — %s", exc)

        elif self._collection is None or vector is None:
            # Fallback: write to JSONL and SQLite so memory_daemon can pick it
            # up later
            self._write_fallback_jsonl(doc_id, text, metadata)
            return True

        return False

    def _embed(self, text: str) -> Optional[List[float]]:
        if not _HTTPX_AVAILABLE:
            return None
        try:
            with httpx.Client(timeout=30.0) as client:
                r = client.post(
                    OLLAMA_EMBED_URL,
                    json={"model": EMBED_MODEL, "input": text},
                )
                r.raise_for_status()
                return r.json().get("embeddings", [[]])[0]
        except Exception as exc:
            logger.warning("ReasoningLogger: embedding failed — %s", exc)
            return None

    def _init_collection(self) -> None:
        if not _CHROMA_AVAILABLE:
            return
        try:
            # Prefer persistent local client over HTTP client
            # (no separate ChromaDB server required)
            import chromadb  # type: ignore
            client = chromadb.PersistentClient(path=str(DB_DIR))
            self._collection = client.get_or_create_collection(COLLECTION_NAME)
            logger.info(
                "ReasoningLogger: connected to collection '%s' (%d docs)",
                COLLECTION_NAME, self._collection.count(),
            )
        except Exception as exc:
            logger.warning(
                "ReasoningLogger: could not connect to ChromaDB — %s. "
                "Traces will be written to fallback JSONL.",
                exc,
            )

    def _write_fallback_jsonl(
        self, doc_id: str, text: str, metadata: Dict[str, Any]
    ) -> None:
        """Write trace to a JSONL file and SQLite DB so memory_daemon can ingest it later."""
        # Write JSONL (existing behavior)
        fallback_path = REASONING_TRACES_PENDING
        entry = {
            "id": doc_id,
            "document": text,
            "metadata": metadata,
            "timestamp": _now(),
        }
        try:
            with fallback_path.open("a", encoding="utf-8") as f:
                f.write(json.dumps(entry) + "\n")
            logger.info(
                "ReasoningLogger: wrote fallback trace to %s",
                fallback_path)
        except OSError as exc:
            logger.error("ReasoningLogger: fallback write failed — %s", exc)

        # Write to SQLite for efficient ingestion
        try:
            conn = sqlite3.connect(REASONING_TRACES_DB)
            with conn:
                conn.execute(
                    "INSERT OR REPLACE INTO pending (id, document, metadata) VALUES (?, ?, ?)",
                    (doc_id, text, json.dumps(metadata)),
                )
        except sqlite3.Error as exc:
            logger.error("ReasoningLogger: SQLite insert failed — %s", exc)


# ---------------------------------------------------------------------------
# Module-level singleton
# ---------------------------------------------------------------------------

reasoning_logger = ReasoningLogger()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _make_id(task_id: str, text: str) -> str:
    """Create a deterministic, collision-resistant document ID."""
    digest = hashlib.sha256(text.encode()).hexdigest()[:16]
    return f"{task_id}_{digest}"
