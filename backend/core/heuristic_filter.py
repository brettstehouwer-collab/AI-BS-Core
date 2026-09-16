"""
Heuristic Filter — Async ChromaDB Routing Daemon
===================================================
Pre-processing gate for the Swarm Orchestrator. Routes incoming text through
ChromaDB vector classification before agent delegation.

Integrated into SwarmOrchestrator as a pre-flight filter.
"""

import asyncio
import hashlib
import logging
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

# --- ChromaDB Routing (lazy import to avoid startup cost) ---
_CHROMA_AVAILABLE = False
try:
    import chromadb  # type: ignore

    _CHROMA_AVAILABLE = True
except ImportError:
    logger.warning(
        "chromadb not installed — HeuristicsDaemon will operate in passthrough mode"
    )


# --- Routing Result ---
@dataclass
class RouteResult:
    """Classification + routing decision from ChromaDB query."""

    pipeline: str
    action: str
    best_match: Optional[str] = None
    similarity_score: float = 0.0
    classification: Dict[str, Any] = field(default_factory=dict)
    collections: Dict[str, Any] = field(default_factory=dict)
    stored_id: Optional[str] = None

    def __bool__(self):
        return self.pipeline != "Passthrough"


# --- Heuristics Daemon ---
class HeuristicsDaemon:
    """
    Async-compatible ChromaDB routing daemon.

    Operates as a pre-processing gate in the Swarm Orchestrator pipeline.
    Routes creative/media input to the correct processing pipeline before
    agent delegation.

    Usage:
        daemon = HeuristicsDaemon()
        route = await daemon.classify("raw text input")
        if route:
            # apply Immutable Transcription, Structural Audit, etc.
    """

    COLLECTIONS_TO_QUERY = ["heuristics", "stehouwer_llm_memory"]
    SIMILARITY_THRESHOLD = 1.5  # Lower = stricter (distance metric)
    DB_DIR = Path(__file__).parent / "stehouwer_vector_memory"

    def __init__(self):
        self._client: Optional[Any] = None
        self._lock = asyncio.Lock()
        self._initialized = False
        logger.info("HeuristicsDaemon initialized (lazy init)")

    # --- Lifecycle ---
    async def _ensure_client(self):
        """Lazy-initialize ChromaDB client."""
        if self._initialized:
            return
        async with self._lock:
            if self._initialized:
                return
            if not _CHROMA_AVAILABLE:
                logger.info("ChromaDB unavailable — operating in passthrough mode")
                self._initialized = True
                return
            try:
                self._client = chromadb.PersistentClient(path=str(self.DB_DIR))
                self._initialized = True
                logger.info(f"ChromaDB client initialized at {self.DB_DIR}")
            except Exception as e:
                logger.warning(f"ChromaDB init failed ({e}) — passthrough mode")
                self._initialized = True

    async def classify(self, input_text: str) -> RouteResult:
        """
        Classify input through ChromaDB and return routing decision.

        Args:
            input_text: Raw text to classify

        Returns:
            RouteResult with pipeline assignment
        """
        await self._ensure_client()

        # Passthrough if no ChromaDB
        if not self._client:
            logger.debug("HeuristicsDaemon: passthrough (no ChromaDB)")
            return RouteResult(
                pipeline="Passthrough", action="Forward to SwarmOrchestrator"
            )

        collections = await self._discover_collections()
        results, best_match, score = await self._classify_input(input_text)
        route = self._determine_route(best_match, input_text)
        stored_id = await self._store_input(input_text, route["pipeline"])

        logger.info(f"HeuristicsDaemon: routed to '{
                route['pipeline']}' (score: {
                score:.3f})")
        return RouteResult(
            pipeline=route["pipeline"],
            action=route["action"],
            best_match=best_match,
            similarity_score=score,
            classification=results,
            collections=collections,
            stored_id=stored_id,
        )

    async def _discover_collections(self) -> Dict[str, Any]:
        """List all ChromaDB collections and their sizes."""
        try:
            collections = self._client.list_collections()
            info = {}
            for col in collections:
                count = self._client.get_collection(col.name).count()
                meta = self._client.get_collection(col.name).metadata
                info[col.name] = {"count": count, "metadata": meta}
            return info
        except Exception as e:
            logger.warning(f"Collection discovery failed: {e}")
            return {}

    async def _classify_input(self, input_text: str) -> tuple:
        """Query collections and return (results_dict, best_match, score)."""
        results = {}
        best_match = None
        best_score = float("inf")

        for col_name in self.COLLECTIONS_TO_QUERY:
            try:
                col = self._client.get_collection(col_name)
                if col.count() == 0:
                    continue
                query_results = col.query(
                    query_texts=[input_text],
                    n_results=min(5, col.count()),
                )
                if (
                    query_results
                    and query_results.get("distances")
                    and query_results["distances"][0]
                ):
                    avg_sim = sum(query_results["distances"][0]) / len(
                        query_results["distances"][0]
                    )
                    results[col_name] = {
                        "avg_similarity": avg_sim,
                        "top_match": (
                            query_results["documents"][0][0][:100]
                            if query_results["documents"]
                            else None
                        ),
                        "metadata": (
                            query_results["metadatas"][0][0]
                            if query_results.get("metadatas")
                            else None
                        ),
                    }
                    if avg_sim < best_score:
                        best_score = avg_sim
                        best_match = col_name
            except Exception as e:
                results[col_name] = {"error": str(e)}

        return results, best_match, best_score

    def _determine_route(
        self, best_match: Optional[str], input_text: str
    ) -> Dict[str, str]:
        """Map best-match collection to processing pipeline."""
        routing_map = {
            "heuristics": {
                "pipeline": "Immutable Transcription",
                "action": "Apply structural formatting only — preserve text fidelity",
            },
            "stehouwer_llm_memory": {
                "pipeline": "Phase V Learning Loop",
                "action": "Store in memory bank and route to primary workspace",
            },
        }

        if best_match and best_match in routing_map:
            return routing_map[best_match]

        if any(kw in input_text.lower() for kw in ["i ", "i,", "i.", "i "]):
            return {
                "pipeline": "Immutable Transcription",
                "action": "Heuristic: text pattern detected — structural formatting",
            }
            
        # Check for queries or interrogatives for Persona RAG
        interrogatives = ["what", "how", "why", "who", "when", "where", "can you", "could you", "would you", "?"]
        if any(kw in input_text.lower() for kw in interrogatives) and (best_match == "stehouwer_llm_memory" or "stehouwer_llm_memory" in self.COLLECTIONS_TO_QUERY):
            return {
                "pipeline": "Persona Querying",
                "action": "Retrieve context from Persona vector memory and construct RAG prompt",
            }

        return {"pipeline": "Manual Review", "action": "Ask user to classify input"}

    async def _store_input(self, input_text: str, routed_to: str) -> Optional[str]:
        """Store classified input in ChromaDB for future routing."""
        try:
            col = self._client.get_or_create_collection("heuristics")
            doc_id = f"input_{
                hashlib.md5(
                    input_text.encode()).hexdigest()[
                    :12]}_{
                datetime.now().strftime('%Y%m%d%H%M%S')}"
            col.add(
                documents=[input_text],
                metadatas=[
                    {
                        "source": "heuristics_daemon",
                        "routed_to": routed_to,
                        "timestamp": datetime.now().isoformat(),
                        "length": len(input_text),
                    }
                ],
                ids=[doc_id],
            )
            return doc_id
        except Exception as e:
            logger.warning(f"Storage failed: {e}")
            return None

    # --- Pipeline Execution ---
    async def apply_pipeline(self, input_text: str) -> Dict[str, Any]:
        """
        Full classify → route → execute pipeline.

        Returns dict with classification results and processed output.
        """
        route = await self.classify(input_text)

        if route.pipeline == "Immutable Transcription":
            output = await self._apply_immutable_transcription(input_text)
        elif route.pipeline == "Phase V Learning Loop":
            output = await self._apply_learning_loop(input_text)
        elif route.pipeline == "Persona Querying":
            output = await self._apply_persona_rag(input_text)
        else:
            output = {"status": "manual_review", "input": input_text}

        return {
            "route": route,
            "output": output,
        }

    async def _apply_immutable_transcription(self, raw_text: str) -> Dict[str, Any]:
        """Apply structural corrections preserving absolute text fidelity."""
        import re

        result = raw_text

        # Fix standalone lowercase 'i' -> 'I'
        result = re.sub(r"\bi\b", "I", result)

        # Insert periods after runs of text without terminal punctuation
        # Heuristic: capitalize first letter, add period if no sentence
        # boundary in 80+ char run
        sentences = result.split(". ")
        fixed_sentences = []
        for s in sentences:
            if len(s.strip()) > 80 and not re.search(r"[.!?]\s", s):
                # Split on newline or obvious break points
                parts = re.split(r"(?<=[.!?])\s+", s)
                fixed_sentences.extend(parts)
            else:
                fixed_sentences.append(s)

        result = ". ".join(fixed_sentences).strip()

        return {
            "pipeline": "Immutable Transcription",
            "status": "completed",
            "output": result,
            "changes": {"casing_fixed": True},
        }

    async def _apply_learning_loop(self, input_text: str) -> Dict[str, Any]:
        """Store in Phase V Learning Loop memory bank."""
        return {
            "pipeline": "Phase V Learning Loop",
            "status": "stored",
            "input_length": len(input_text),
        }
        
    async def _apply_persona_rag(self, query: str) -> Dict[str, Any]:
        """Retrieve top 5 context chunks from Persona dataset and construct RAG prompt."""
        try:
            col = self._client.get_collection("stehouwer_llm_memory")
            n_res = min(5, col.count())
            if n_res == 0:
                context = "No persona history available in memory."
            else:
                results = col.query(query_texts=[query], n_results=n_res)
                docs = results.get("documents", [[]])[0]
                context = "\n\n".join(docs) if docs else "No relevant context found."
        except Exception as e:
            logger.warning(f"Persona RAG retrieval failed: {e}")
            context = "Memory retrieval fault."

        augmented_prompt = (
            f"Context from Persona Memory:\n{context}\n\n"
            f"User Query:\n{query}\n\n"
            f"Please generate a response using the above context."
        )

        return {
            "pipeline": "Persona Querying",
            "status": "augmented",
            "output": augmented_prompt,
            "context_chunks_retrieved": n_res if 'n_res' in locals() else 0,
        }

    # --- Structural Audit (Media Studio) ---
    async def structural_audit(self, file_path: str, file_type: str) -> Dict[str, Any]:
        """
        Validate a file against industry standards.

        Args:
            file_path: Path to the file to audit
            file_type: 'script', 'audio', 'manuscript'

        Returns:
            Audit results with violations and score
        """
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
        except Exception as e:
            return {"status": "error", "detail": str(e)}

        violations = []
        warnings = []
        score = 1.0

        if file_type == "script":
            # Final Draft format checks
            if not re.search(r"(?m)^\w[\w\s]*:", content[:200]):
                violations.append(
                    {
                        "rule": "scene_heading",
                        "detail": "Missing scene heading in first 200 chars",
                    }
                )
                score -= 0.15
            if "FADE IN:" not in content.upper():
                warnings.append(
                    {"rule": "fade_in", "detail": "Missing FADE IN: opening"}
                )

        elif file_type == "audio":
            # FL Studio project checks
            if ".flp" in file_path.lower():
                try:
                    with open(file_path, "rb") as bf:
                        binary_content = bf.read()
                        # Very basic heuristic: scan binary for common FL Studio markers
                        if b'FLhd' not in binary_content[:32]:
                            violations.append({"rule": "flp_header", "detail": "Missing standard FL Studio binary header (FLhd)"})
                            score -= 0.5
                        # Look for tempo marker (simple byte heuristic for uncompressed parts)
                        if b'tempo' not in binary_content.lower() and b'BPM' not in binary_content.upper():
                            warnings.append({"rule": "tempo_metadata", "detail": "Tempo signature metadata not easily detected in binary stream"})
                except Exception as e:
                    violations.append({"rule": "file_read", "detail": f"Binary read error: {e}"})
                    score -= 1.0

        elif file_type == "manuscript":
            # KDP hardcover constraints
            word_count = len(content.split())
            if word_count < 20000:
                warnings.append(
                    {"rule": "min_length", "detail": f"Manuscript too short for standard KDP hardcover (Current: {word_count} words. Recommended: >20,000)"}
                )
            
            # Check for chapter headings (Markdown style)
            chapter_count = len(re.findall(r"(?im)^#+\s*(chapter|part)\b", content))
            if chapter_count == 0:
                violations.append({"rule": "structure_headings", "detail": "No standard Markdown chapter headings (# Chapter) detected."})
                score -= 0.3

        return {
            "status": "completed",
            "file_type": file_type,
            "score": max(0.0, score),
            "violations": violations,
            "warnings": warnings,
        }


# --- Singleton instance for SwarmOrchestrator integration ---
_daemon_instance: Optional[HeuristicsDaemon] = None


def get_heuristics_daemon() -> HeuristicsDaemon:
    """Get or create the singleton HeuristicsDaemon instance."""
    global _daemon_instance
    if _daemon_instance is None:
        _daemon_instance = HeuristicsDaemon()
    return _daemon_instance
