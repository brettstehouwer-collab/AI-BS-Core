import hashlib
import httpx
import chromadb
from pathlib import Path

WORKSPACE_ROOT = Path(r"c:\Users\footb\AI-BS_Matrix")
DOCS_TO_INGEST = [
    "AI-BS_Technical_Architecture_Report_v1.2.md",
    "AI-BS Technical Architecture Report — Brett Adam Stehouwer.md",
    "heuristics-daemon.agent.md",
    "imagegen-agent.agent.md",
    "IMAGE_GENERATION_README.md",
    "ReAct_Agent_Architecture.md",
    "write this as a directive to eveluate and decide....md"
]
CHROMA_HOST = "localhost"
CHROMA_PORT = 8001
COLLECTION_NAME = "ai_bs_context_memory"
EMBED_MODEL = "nomic-embed-text"
OLLAMA_EMBED_URL = "http://127.0.0.1:11434/api/embeddings"


def _embed(text: str):
    try:
        with httpx.Client(timeout=30.0) as client:
            r = client.post(
                OLLAMA_EMBED_URL,
                json={
                    "model": EMBED_MODEL,
                    "prompt": text})
            r.raise_for_status()
            return r.json().get("embedding", [])
    except Exception as e:
        print(f"Embedding error: {e}")
        return None


def chunk_text(text: str, delimiter='\n\n'):
    return [c.strip() for c in text.split(delimiter) if len(c.strip()) > 10]


def main():
    try:
        client = chromadb.HttpClient(host=CHROMA_HOST, port=CHROMA_PORT)
        collection = client.get_or_create_collection(COLLECTION_NAME)
    except Exception as e:
        print(f"Chroma connection failed: {e}")
        return

    total_chunks = 0
    total_success = 0

    for filename in DOCS_TO_INGEST:
        file_path = WORKSPACE_ROOT / filename
        if not file_path.exists():
            print(f"File not found: {filename}")
            continue

        print(f"Processing: {filename}")
        content = file_path.read_text(encoding="utf-8", errors="ignore")
        chunks = chunk_text(content)
        total_chunks += len(chunks)

        success = 0
        for i, chunk in enumerate(chunks):
            eid = hashlib.sha256((filename + chunk).encode()).hexdigest()[:24]
            vector = _embed(chunk)
            if not vector:
                print(
                    f"  Skipping chunk {i} of {filename}: Failed to get embedding")
                continue

            try:
                collection.upsert(
                    ids=[eid],
                    documents=[chunk],
                    embeddings=[vector],
                    metadatas=[{"source": filename, "chunk_index": i}]
                )
                success += 1
            except Exception as e:
                print(f"  Failed to upsert chunk {i}: {e}")

        print(f"  -> Ingested {success}/{len(chunks)} chunks.")
        total_success += success

    print(
        f"\nCompleted: Ingested {total_success}/{total_chunks} total chunks into {COLLECTION_NAME}.")


if __name__ == "__main__":
    main()
