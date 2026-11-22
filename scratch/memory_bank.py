import os
import chromadb
import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s")

DB_DIR = os.path.join(
    os.path.dirname(
        os.path.abspath(__file__)),
    "stehouwer_vector_memory")

try:
    client = chromadb.PersistentClient(path=DB_DIR)
    collection = client.get_or_create_collection(name="heuristics")
    cases_collection = client.get_or_create_collection(name="cases")
except Exception as e:
    logging.error(f"Failed to initialize ChromaDB: {e}")
    collection = None
    cases_collection = None


def store_heuristic(heuristic_text: str, metadata: dict = None):
    """Stores a learned heuristic in ChromaDB."""
    if not collection:
        logging.warning("ChromaDB not available, skipping storage.")
        return

    if metadata is None:
        metadata = {}

    doc_id = str(hash(heuristic_text))

    try:
        collection.add(
            documents=[heuristic_text],
            metadatas=[metadata],
            ids=[doc_id]
        )
        logging.info(
            f"[MEMORY BANK] Stored heuristic: {heuristic_text[:50]}...")
    except Exception as e:
        logging.error(f"Failed to store heuristic: {e}")


def add_memory(memory_text: str, metadata: dict = None):
    """Stores a general memory / solution."""
    store_heuristic(memory_text, metadata)


def store_case_resolution(
        error_trace: str,
        resolution_patch: str,
        metadata: dict = None):
    """Stores a historical error resolution trace in the Case Library."""
    if not cases_collection:
        logging.warning("ChromaDB not available, skipping case storage.")
        return

    if metadata is None:
        metadata = {}

    metadata["error_trace"] = error_trace
    doc_id = str(hash(error_trace + resolution_patch))

    try:
        cases_collection.add(
            documents=[resolution_patch],
            metadatas=[metadata],
            ids=[doc_id]
        )
        logging.info(
            f"[CASE LIBRARY] Stored resolution for error trace: {error_trace[:50]}...")
    except Exception as e:
        logging.error(f"Failed to store case resolution: {e}")


def query_similar_cases(current_error_trace: str, n_results: int = 3):
    """Queries the Case Library for similar past errors and their resolutions."""
    if not cases_collection:
        logging.warning("ChromaDB not available, skipping case query.")
        return []

    try:
        results = cases_collection.query(
            query_texts=[current_error_trace],
            n_results=n_results
        )
        return results
    except Exception as e:
        logging.error(f"Failed to query cases: {e}")
        return []


if __name__ == "__main__":
    logging.info("Memory bank initialized.")
    store_heuristic("Initial boot sequence validated.", {"source": "init"})
