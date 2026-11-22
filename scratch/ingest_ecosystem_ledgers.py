import os
import re
import hashlib
import httpx
import chromadb
from pathlib import Path

WORKSPACE_ROOT = Path(r"C:\AI-BS\Ecosystem_Ledgers")
CHROMA_HOST = "localhost"
CHROMA_PORT = 8001
COLLECTION_NAME = "stehouwer_vector_memory"
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

def chunk_text(text: str):
    chunks = re.split(r'(?=\n#+ )', text)
    final_chunks = []
    for c in chunks:
        c = c.strip()
        if len(c) > 10:
            # If a heading block is too massive, sub-chunk it to prevent OOM / 500 errors
            if len(c) > 4000:
                sub_chunks = [c[i:i+4000] for i in range(0, len(c), 4000)]
                final_chunks.extend(sub_chunks)
            else:
                final_chunks.append(c)
    return final_chunks

def main():
    try:
        client = chromadb.HttpClient(host=CHROMA_HOST, port=CHROMA_PORT)
        collection = client.get_or_create_collection(COLLECTION_NAME)
    except Exception as e:
        print(f"Chroma connection failed: {e}")
        return

    docs_to_ingest = []
    for ext in ['*.md', '*.txt']:
        docs_to_ingest.extend(WORKSPACE_ROOT.glob(ext))

    # Pre-parse to get exact chunk count
    all_chunks = []
    for file_path in docs_to_ingest:
        filename = file_path.name
        try:
            content = file_path.read_text(encoding="utf-8", errors="ignore")
        except Exception as e:
            print(f"Failed to read {filename}: {e}")
            continue
        chunks = chunk_text(content)
        for i, c in enumerate(chunks):
            all_chunks.append({"filename": filename, "chunk_index": i, "text": c})
            
    total_chunks = len(all_chunks)
    print(f"--- PRE-FLIGHT CHECK ---")
    print(f"Total files to process: {len(docs_to_ingest)}")
    print(f"Total heading-boundary chunks generated: {total_chunks}")
    print(f"--- BEGINNING LONG-RUNNING EMBEDDING PROCESS ---")

    # Embed loop
    success = 0
    for item in all_chunks:
        filename = item["filename"]
        chunk = item["text"]
        i = item["chunk_index"]
        eid = hashlib.sha256((filename + chunk).encode()).hexdigest()[:24]
        vector = _embed(chunk)
        if not vector:
            continue
        try:
            collection.upsert(
                ids=[eid],
                documents=[chunk],
                embeddings=[vector],
                metadatas=[{"source": filename, "chunk_index": i}]
            )
            success += 1
            if success % 100 == 0:
                print(f"Ingested {success}/{total_chunks} chunks...")
        except Exception as e:
            pass

    print(f"\nCompleted: Ingested {success}/{total_chunks} total chunks into {COLLECTION_NAME}.")



if __name__ == "__main__":
    main()
