import os
import json

try:
    import tiktoken

    _ENCODER = tiktoken.get_encoding("cl100k_base")  # OpenAI / Ollama compatible
    HAS_TIKTOKEN = True
except ImportError:
    HAS_TIKTOKEN = False


class TokenBudgetEstimator:
    def __init__(self, target_limit=3700, max_limit=4000):
        self.target_limit = target_limit
        self.max_limit = max_limit
        # Use workspace-relative path with env override
        self.archive_path = os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            os.getenv("ARCHIVE_PATH", "session_history_archive.json"),
        )

    def estimate_string_tokens(self, text: str) -> int:
        """Estimate tokens using tiktoken (BPE-accurate) or fallback heuristic."""
        if not text:
            return 0

        if HAS_TIKTOKEN:
            return len(_ENCODER.encode(text))

        # Fallback: character-based estimate (less accurate, no external dep)
        char_count = len(text)
        return max(int(char_count * 0.25), int(len(text.split()) * 1.3))

    def estimate_history_tokens(self, history_list: list) -> int:
        """Sum estimated tokens across a message history."""
        return sum(
            self.estimate_string_tokens(m.get("content", "")) for m in history_list
        )

    def execute_eviction_matrix(
        self, history_list: list, inbound_prompt_tokens: int, chroma_client=None
    ) -> list:
        """Evict oldest messages when budget is exceeded."""
        if (
            self.estimate_history_tokens(history_list) + inbound_prompt_tokens
            <= self.target_limit
        ):
            return history_list

        evicted = []
        while (
            self.estimate_history_tokens(history_list) + inbound_prompt_tokens
        ) > self.target_limit:
            if not history_list:
                break
            evicted.append(history_list.pop(0))

        if evicted:
            self._write_to_archive_json(evicted)
            if chroma_client:
                self._push_to_chroma_matrix(evicted, chroma_client)

        return history_list

    def _write_to_archive_json(self, records: list):
        existing = []
        if os.path.exists(self.archive_path):
            try:
                with open(self.archive_path, "r", encoding="utf-8") as f:
                    existing = json.load(f)
            except Exception:
                existing = []
        existing.extend(records)
        with open(self.archive_path, "w", encoding="utf-8") as f:
            json.dump(existing, f, indent=2)

    def _push_to_chroma_matrix(self, records: list, chroma_client):
        """Placeholder for passing context logs directly into stehouwer_llm_memory vector index."""
        try:
            # Assumes an active wrapper collection interface passes into here
            collection = chroma_client.get_or_create_collection("stehouwer_llm_memory")
            for idx, record in enumerate(records):
                text_payload = f"[{record.get('role',
                                              'unknown')}]: {record.get('content',
                                                                        '')}"
                collection.add(
                    documents=[text_payload],
                    metadatas=[
                        {"source": "eviction_daemon", "role": record.get("role")}
                    ],
                    ids=[f"evict_{os.getpid()}_{idx}_{hash(text_payload)}"],
                )
        except Exception:
            # Silent fallback to prevent core execution crash if ChromaDB is
            # offline
            pass
