import os
import json

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
HOT_DB_PATH = os.path.join(BASE_DIR, "stehouwer_vector_memory")


class ChromaStorageManager:
    def __init__(self):
        self.client = None
        self.collection = None
        try:
            import chromadb

            self.client = chromadb.PersistentClient(path=HOT_DB_PATH)
            self.collection = self.client.get_or_create_collection(
                name="heuristic_resolutions"
            )
            self.communication_collection = self.client.get_or_create_collection(
                name="communication_styles"
            )
        except Exception as e:
            print(f"[ChromaStorageManager] Fallback mode: {e}")

    def query(self, text: str, n_results: int = 5):
        if self.collection:
            try:
                return self.collection.query(query_texts=[text], n_results=n_results)
            except Exception as e:
                print(f"[ChromaStorageManager] Query error: {e}")
        return {"documents": [], "metadatas": []}
        
    def _enrich_metadata_with_spacy(self, text: str, metadata: dict) -> dict:
        enriched = dict(metadata) if metadata else {}
        try:
            import sys
            import os
            # Ensure backend is in path
            sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
            from backend.aibs_reasoning_engine import AIBSHybridNLPParser
            
            parsed = AIBSHybridNLPParser.parse_text(text)
            if parsed:
                # ChromaDB metadata must be primitive types
                root_verbs = ",".join(parsed.get("root_verbs", []))
                entities = ",".join(list(set([n["label"] for n in parsed.get("nodes", []) if n.get("is_entity")])))
                if root_verbs: enriched["spacy_root_verbs"] = root_verbs
                if entities: enriched["spacy_entities"] = entities
        except Exception:
            pass # Silent fallback
        return enriched

    def add_communication_style(self, text: str, metadata: dict, doc_id: str):
        if self.communication_collection:
            try:
                enriched = self._enrich_metadata_with_spacy(text, metadata)
                self.communication_collection.add(
                    documents=[text],
                    metadatas=[enriched],
                    ids=[doc_id]
                )
            except Exception as e:
                print(f"[ChromaStorageManager] Error adding communication style: {e}")

    def add_communication_styles_batch(self, texts: list, metadatas: list, ids: list):
        if self.communication_collection:
            try:
                enriched_metadatas = [self._enrich_metadata_with_spacy(t, m) for t, m in zip(texts, metadatas)]
                self.communication_collection.add(
                    documents=texts,
                    metadatas=enriched_metadatas,
                    ids=ids
                )
            except Exception as e:
                print(f"[ChromaStorageManager] Error adding batch communication styles: {e}")


chroma_manager = ChromaStorageManager()
