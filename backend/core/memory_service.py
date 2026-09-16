"""
memory_service.py
━━━━━━━━━━━━━━━━
Manages all interactions with the ChromaDB vector store served by
chroma_daemon on localhost:8001.

Two collections are queried for maximum learning coverage:
  • ai_bs_context_memory  — runtime session context & conversation history
  • heuristics            — skill-development heuristics, fire-writing rules,
                            chroma-router classifications, and merged agent data
"""

import asyncio
from typing import Any, Dict, List, Optional

from chromadb import HttpClient

import os

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
CHROMA_HOST = os.getenv("CHROMA_HOST", "localhost")
CHROMA_PORT = int(os.getenv("CHROMA_PORT", 8001))

# Primary collection — session context written by memory_daemon
CONTEXT_COLLECTION = "ai_bs_context_memory"

# Secondary collection — heuristics, skill routing, fire-writing patterns
HEURISTICS_COLLECTION = "heuristics"


class MemoryService:
    """
    Singleton service for all vector store interactions.
    Connects to the chroma_daemon HTTP API (port 8001).
    Gracefully degrades when the daemon is not yet running.
    """

    def __init__(self, host: str = CHROMA_HOST, port: int = CHROMA_PORT):
        print(f"[MemoryService] Initializing ChromaDB HttpClient at {host}:{port}")
        self.client: Optional[HttpClient] = None
        self.collection = None  # ai_bs_context_memory
        self.heuristics_collection = None  # heuristics
        self.play_collection = None  # theatrical_play_memory (Isolated Context)

        try:
            self.client = HttpClient(host=host, port=port)
            self.collection = self.client.get_or_create_collection(
                name=CONTEXT_COLLECTION
            )
            self.heuristics_collection = self.client.get_or_create_collection(
                name=HEURISTICS_COLLECTION
            )
            self.play_collection = self.client.get_or_create_collection(
                name="theatrical_play_memory"
            )
            print(f"[MemoryService] Connected — " f"{CONTEXT_COLLECTION}: {
                    self.collection.count()} docs, " f"{HEURISTICS_COLLECTION}: {
                    self.heuristics_collection.count()} docs, " f"theatrical_play_memory: {
                    self.play_collection.count()} docs")
        except Exception as e:
            print(f"[MemoryService] WARNING: ChromaDB offline ({e})")
            self.client = None
            self.collection = None
            self.heuristics_collection = None
            self.play_collection = None

    def get_client_collection(self, client_id: str):
        """Dynamically gets or creates an isolated collection for a specific client."""
        if not self.client:
            return None
        try:
            return self.client.get_or_create_collection(
                name=f"client_{client_id}_memory"
            )
        except Exception as e:
            print(f"[MemoryService] Failed to get client collection {client_id}: {e}")
            return None

    # -----------------------------------------------------------------------
    # Internal async helper
    # -----------------------------------------------------------------------
    async def _run_sync(self, func, *args, **kwargs):
        """Run a synchronous ChromaDB call in a thread to avoid blocking asyncio."""
        loop = asyncio.get_running_loop()
        import functools

        return await loop.run_in_executor(
            None, functools.partial(func, *args, **kwargs)
        )

    @property
    def is_online(self) -> bool:
        return self.client is not None

    # -----------------------------------------------------------------------
    # Context memory (ai_bs_context_memory)
    # -----------------------------------------------------------------------
    async def add_document(
        self,
        documents: List[str],
        metadatas: List[Dict[str, Any]],
        embeddings: List[List[float]],
    ):
        """Add session context embeddings to the primary collection."""
        if not self.collection:
            return
        await self._run_sync(
            self.collection.add,
            embeddings=embeddings,
            documents=documents,
            metadatas=metadatas,
        )

    async def retrieve_context(
        self,
        query_embedding: List[float],
        n_results: int = 5,
    ) -> Dict[str, Any]:
        """
        Semantic search against session history memory.
        Returns top-n results from ai_bs_context_memory.
        """
        if not self.collection:
            return {"ids": [], "documents": [], "metadatas": []}
        try:
            return await self._run_sync(
                self.collection.query,
                query_embeddings=[query_embedding],
                n_results=min(n_results, max(self.collection.count(), 1)),
            )
        except Exception as e:
            print(f"[MemoryService ERROR] retrieve_context failed: {e}")
            return {"ids": [], "documents": [], "metadatas": []}

    # -----------------------------------------------------------------------
    # Heuristics / skill development (heuristics collection)
    # -----------------------------------------------------------------------
    async def retrieve_heuristics(
        self,
        query_embedding: List[float],
        n_results: int = 5,
        source_filter: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Query the heuristics collection — returns skill-routing patterns,
        fire-writing classifications, and merged agent skill data.

        Args:
            query_embedding: embedding vector of the query
            n_results:       number of results to return
            source_filter:   optional 'source' metadata value to filter by
                             (e.g. 'fire_writing', 'media_studio', 'chroma_router_skill')
        """
        if not self.heuristics_collection:
            return {"ids": [], "documents": [], "metadatas": []}
        try:
            kwargs: Dict[str, Any] = dict(
                query_embeddings=[query_embedding],
                n_results=min(n_results, max(self.heuristics_collection.count(), 1)),
            )
            if source_filter:
                kwargs["where"] = {"source": source_filter}
            return await self._run_sync(self.heuristics_collection.query, **kwargs)
        except Exception as e:
            print(f"[MemoryService ERROR] retrieve_heuristics failed: {e}")
            return {"ids": [], "documents": [], "metadatas": []}

    async def add_heuristic(
        self,
        documents: List[str],
        metadatas: List[Dict[str, Any]],
        ids: List[str],
        embeddings: Optional[List[List[float]]] = None,
    ):
        """
        Store a new heuristic, skill routing result, or fire-writing
        classification into the heuristics collection.
        """
        if not self.heuristics_collection:
            return
        kwargs: Dict[str, Any] = dict(documents=documents, metadatas=metadatas, ids=ids)
        if embeddings:
            kwargs["embeddings"] = embeddings
        await self._run_sync(self.heuristics_collection.upsert, **kwargs)

    # -----------------------------------------------------------------------
    # Combined retrieval — used by LLM context enrichment
    # -----------------------------------------------------------------------
    async def retrieve_combined(
        self,
        query_embedding: List[float],
        n_results: int = 5,
    ) -> Dict[str, Any]:
        """
        Query BOTH collections and merge results ranked by distance.
        Provides maximum coverage — session context + skill heuristics.
        """
        context_results, heuristic_results = await asyncio.gather(
            self.retrieve_context(query_embedding, n_results),
            self.retrieve_heuristics(query_embedding, n_results),
        )

        # Extract the inner lists (ChromaDB returns list of lists for queries)
        c_ids = (
            context_results.get("ids", [[]])[0] if context_results.get("ids") else []
        )
        c_docs = (
            context_results.get("documents", [[]])[0]
            if context_results.get("documents")
            else []
        )
        c_metas = (
            context_results.get("metadatas", [[]])[0]
            if context_results.get("metadatas")
            else []
        )
        c_dists = (
            context_results.get("distances", [[]])[0]
            if context_results.get("distances")
            else []
        )

        h_ids = (
            heuristic_results.get("ids", [[]])[0]
            if heuristic_results.get("ids")
            else []
        )
        h_docs = (
            heuristic_results.get("documents", [[]])[0]
            if heuristic_results.get("documents")
            else []
        )
        h_metas = (
            heuristic_results.get("metadatas", [[]])[0]
            if heuristic_results.get("metadatas")
            else []
        )
        h_dists = (
            heuristic_results.get("distances", [[]])[0]
            if heuristic_results.get("distances")
            else []
        )

        # Zip each set into a list of tuples: (distance, id, document,
        # metadata, source)
        combined_items = []
        for i in range(len(c_ids)):
            combined_items.append(
                (c_dists[i], c_ids[i], c_docs[i], c_metas[i], "context")
            )
        for i in range(len(h_ids)):
            combined_items.append(
                (h_dists[i], h_ids[i], h_docs[i], h_metas[i], "heuristics")
            )

        # Sort by distance (lower is closer/better in Euclidean/Cosine distance
        # space)
        combined_items.sort(key=lambda x: x[0])

        # Slice to top n_results overall
        top_items = combined_items[:n_results]

        # Re-pack into ChromaDB standard format (single list of results inside
        # the outer list)
        merged = {
            "ids": [[item[1] for item in top_items]],
            "documents": [[item[2] for item in top_items]],
            "metadatas": [[item[3] for item in top_items]],
            "distances": [[item[0] for item in top_items]],
            "sources": [[item[4] for item in top_items]],
        }
        return merged

    # -----------------------------------------------------------------------
    # Stats
    # -----------------------------------------------------------------------
    async def stats(self) -> Dict[str, Any]:
        """Return collection counts for both managed collections."""
        if not self.is_online:
            return {"online": False}
        context_count = (
            await self._run_sync(self.collection.count) if self.collection else 0
        )
        heuristic_count = (
            await self._run_sync(self.heuristics_collection.count)
            if self.heuristics_collection
            else 0
        )
        return {
            "online": True,
            CONTEXT_COLLECTION: context_count,
            HEURISTICS_COLLECTION: heuristic_count,
            "total": context_count + heuristic_count,
        }

    # -----------------------------------------------------------------------
    # Cleanup
    # -----------------------------------------------------------------------
    async def delete_context(self, ids: List[str]):
        """Delete specific context memories by ID."""
        if not self.collection or not ids:
            return
        await self._run_sync(self.collection.delete, ids=ids)
        print(f"[MemoryService] Deleted {len(ids)} context items.")

    # -----------------------------------------------------------------------
    # Isolated Context (Theatrical Play "AI Bible")
    # -----------------------------------------------------------------------
    async def add_isolated_play_document(
        self,
        documents: List[str],
        metadatas: List[Dict[str, Any]],
        ids: List[str],
        embeddings: Optional[List[List[float]]] = None,
    ):
        """Add script or 'AI Bible' document to the isolated play collection."""
        if not self.play_collection:
            return
        kwargs: Dict[str, Any] = dict(documents=documents, metadatas=metadatas, ids=ids)
        if embeddings:
            kwargs["embeddings"] = embeddings
        await self._run_sync(self.play_collection.upsert, **kwargs)

    async def retrieve_isolated_play(
        self,
        query_embedding: List[float],
        n_results: int = 5,
    ) -> Dict[str, Any]:
        """
        Query ONLY the isolated play collection for the live performance.
        Ignores all global context memory and heuristics.
        """
        if not self.play_collection:
            return {"ids": [], "documents": [], "metadatas": []}
        try:
            return await self._run_sync(
                self.play_collection.query,
                query_embeddings=[query_embedding],
                n_results=min(n_results, max(self.play_collection.count(), 1)),
            )
        except Exception as e:
            print(f"[MemoryService ERROR] retrieve_isolated_play failed: {e}")
            return {"ids": [], "documents": [], "metadatas": []}

    # -----------------------------------------------------------------------
    # Isolated Client Memory (CRM)
    # -----------------------------------------------------------------------
    async def add_client_note(
        self, client_id: str, document: str, metadata: Dict[str, Any], doc_id: str
    ):
        """Saves a secure note to the client's isolated ChromaDB collection."""
        collection = self.get_client_collection(client_id)
        if not collection:
            return False

        try:
            # Upsert into the client's specific isolated collection
            await self._run_sync(
                collection.upsert,
                documents=[document],
                metadatas=[metadata],
                ids=[doc_id],
            )
            return True
        except Exception as e:
            print(f"[MemoryService ERROR] add_client_note failed: {e}")
            return False

    async def retrieve_client_notes(self, client_id: str, limit: int = 100):
        """Retrieves all notes stored in the client's isolated collection."""
        collection = self.get_client_collection(client_id)
        if not collection:
            return {"ids": [], "documents": [], "metadatas": []}

        try:
            # If collection is empty or small, get them all
            count = await self._run_sync(collection.count)
            if count == 0:
                return {"ids": [], "documents": [], "metadatas": []}

            results = await self._run_sync(collection.get, limit=limit)
            return results
        except Exception as e:
            print(f"[MemoryService ERROR] retrieve_client_notes failed: {e}")
            return {"ids": [], "documents": [], "metadatas": []}


# ---------------------------------------------------------------------------
# Singleton pattern — one connection per backend process
# ---------------------------------------------------------------------------
_memory_service_instance: Optional[MemoryService] = None


def get_memory_service() -> MemoryService:
    """FastAPI dependency — returns the singleton MemoryService instance."""
    global _memory_service_instance
    if _memory_service_instance is None:
        _memory_service_instance = MemoryService()
    return _memory_service_instance
