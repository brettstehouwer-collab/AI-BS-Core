import os
import hashlib
import httpx
import chromadb
from pathlib import Path

EXTRACT_DIR = Path(
    r"c:\Users\footb\AI-BS_Matrix\sandbox_scratch\takeout_extract")
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


def chunk_text(text: str, delimiter='\n', max_len=1000):
    chunks = []
    current = ""
    for line in text.split(delimiter):
        line = line.strip()
        if not line:
            continue
        if len(current) + len(line) > max_len:
            if current:
                chunks.append(current)
            current = line
        else:
            current += (" " if current else "") + line
    if current:
        chunks.append(current)
    return chunks


def process_file(file_path: Path):
    chunks = []
    try:
        content = file_path.read_text(encoding="utf-8", errors="ignore")
        chunks = chunk_text(content, delimiter='\n', max_len=1000)
    except Exception as e:
        print(f"Failed to read {file_path}: {e}")
    return chunks


def main():
    if not EXTRACT_DIR.exists():
        print("Extraction directory not found.")
        return

    try:
        client = chromadb.HttpClient(host=CHROMA_HOST, port=CHROMA_PORT)
        collection = client.get_or_create_collection(COLLECTION_NAME)
    except Exception as e:
        print(f"Chroma connection failed: {e}")
        return

    total_files = 0
    total_success = 0
    total_chunks = 0

    for root, dirs, files in os.walk(EXTRACT_DIR):
        for f in files:
            file_path = Path(root) / f
            print(f"Processing: {f}")

            chunks = process_file(file_path)
            if not chunks:
                continue

            total_files += 1
            total_chunks += len(chunks)
            success = 0

            for i, chunk in enumerate(chunks):
                # Skip tiny noise chunks
                if len(chunk) < 15:
                    continue

                # Make relative path for source metadata
                rel_path = str(file_path.relative_to(EXTRACT_DIR))
                eid = hashlib.sha256(
                    (rel_path + chunk).encode()).hexdigest()[:24]

                vector = _embed(chunk)
                if not vector:
                    continue

                try:
                    collection.upsert(
                        ids=[eid],
                        documents=[chunk],
                        embeddings=[vector],
                        metadatas=[{"source": f"Takeout/{rel_path}", "chunk_index": i}]
                    )
                    success += 1
                except Exception as e:
                    print(f"  Upsert failed for {f} chunk {i}: {e}")

            print(f"  -> {success}/{len(chunks)} chunks ingested.")
            total_success += success

    print(
        f"\nCompleted GTake Ingestion! Ingested {total_success} chunks across {total_files} files.")


if __name__ == "__main__":
    main()
