import hashlib
import httpx
import chromadb
from pathlib import Path

WORKSPACE_ROOT = Path(r"c:\Users\footb\AI-BS_Matrix")
FILE_PATH = WORKSPACE_ROOT / "windows_commands_reference.md"
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


def main():
    if not FILE_PATH.exists():
        print(f"File not found: {FILE_PATH}")
        return

    content = FILE_PATH.read_text(encoding="utf-8")

    # Split by empty lines to create meaningful semantic chunks
    raw_chunks = content.split('\n\n')
    chunks = [c.strip() for c in raw_chunks if c.strip()]

    print(f"Found {len(chunks)} chunks to process.")

    try:
        client = chromadb.HttpClient(host=CHROMA_HOST, port=CHROMA_PORT)
        collection = client.get_or_create_collection(COLLECTION_NAME)
    except Exception as e:
        print(f"Chroma connection failed: {e}")
        return

    success = 0
    for i, chunk in enumerate(chunks):
        eid = hashlib.sha256(chunk.encode()).hexdigest()[:24]

        vector = _embed(chunk)
        if not vector:
            print(f"Skipping chunk {i}: Failed to get embedding")
            continue

        try:
            collection.upsert(
                ids=[eid],
                documents=[chunk],
                embeddings=[vector],
                metadatas=[{"source": "windows_commands_reference.md", "chunk_index": i}]
            )
            success += 1
            print(f"Upserted chunk {i + 1}/{len(chunks)}")
        except Exception as e:
            print(f"Failed to upsert chunk {i}: {e}")

    print(
        f"\nSuccessfully ingested {success}/{len(chunks)} chunks into {COLLECTION_NAME}.")


if __name__ == "__main__":
    main()
