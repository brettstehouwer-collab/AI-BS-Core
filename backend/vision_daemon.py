import os
import time
import base64
import sqlite3
import hashlib
import httpx
import chromadb
from pathlib import Path

TARGET_DIRS = [
    r"S:\Google phtos download from drive 2013",
    r"F:\Local_Vault\Media_Assets",
]
ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}

# Chroma & Ollama Config
CHROMA_HOST = "localhost"
CHROMA_PORT = 8001
COLLECTION_NAME = "ai_bs_context_memory"

OLLAMA_GENERATE_URL = "http://127.0.0.1:11434/api/generate"
OLLAMA_EMBED_URL = os.environ.get("OLLAMA_EMBED_URL", "http://127.0.0.1:11435/api/embeddings")
VISION_MODEL = "llava"
EMBED_MODEL = "nomic-embed-text"

# SQLite State DB
STATE_DB = "vision_sync_state.db"
PROMPT = (
    "Describe this image in detail. Extract and output any visible text or writing."
)


def init_db():
    conn = sqlite3.connect(STATE_DB)
    try:
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA synchronous=NORMAL;")
    except Exception:
        pass
    c = conn.cursor()
    c.execute("""CREATE TABLE IF NOT EXISTS processed_images (
                    filepath TEXT PRIMARY KEY,
                    processed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    client_id TEXT DEFAULT 'stehouwer_publishing'
                 )""")
    conn.commit()
    return conn


def is_processed(conn, filepath):
    c = conn.cursor()
    c.execute("SELECT 1 FROM processed_images WHERE filepath=?", (filepath,))
    return c.fetchone() is not None


def mark_processed(conn, filepath):
    c = conn.cursor()
    c.execute(
        "INSERT OR IGNORE INTO processed_images (filepath) VALUES (?)", (filepath,)
    )
    conn.commit()


def generate_caption(image_path):
    try:
        with open(image_path, "rb") as f:
            b64_img = base64.b64encode(f.read()).decode("utf-8")

        with httpx.Client(timeout=120.0) as client:
            payload = {
                "model": VISION_MODEL,
                "prompt": PROMPT,
                "images": [b64_img],
                "stream": False,
            }
            r = client.post(OLLAMA_GENERATE_URL, json=payload)
            r.raise_for_status()
            return r.json().get("response", "").strip()
    except Exception as e:
        print(f"Error generating caption for {image_path}: {e}")
        return None


def generate_embedding(text):
    try:
        with httpx.Client(timeout=30.0) as client:
            r = client.post(
                OLLAMA_EMBED_URL, json={"model": EMBED_MODEL, "prompt": text}
            )
            r.raise_for_status()
            return r.json().get("embedding", [])
    except Exception as e:
        print(f"Error generating embedding: {e}")
        return None


def process_directory(conn, collection, directory):
    if not os.path.exists(directory):
        print(f"Directory not found: {directory}")
        return

    print(f"Scanning {directory}...")
    for root, dirs, files in os.walk(directory):
        for f in files:
            file_path = str(Path(root) / f)
            ext = os.path.splitext(f)[1].lower()
            if ext not in ALLOWED_EXTENSIONS:
                continue

            if is_processed(conn, file_path):
                continue

            print(f"Processing: {f}")
            caption = generate_caption(file_path)
            if not caption:
                continue

            print(f"  Caption generated: {caption[:60]}...")

            # Embed the caption
            vector = generate_embedding(caption)
            if not vector:
                continue

            eid = hashlib.sha256(file_path.encode()).hexdigest()[:24]
            try:
                collection.upsert(
                    ids=[eid],
                    documents=[caption],
                    embeddings=[vector],
                    metadatas=[
                        {
                            "source": file_path,
                            "type": "image_caption",
                            "client_id": "stehouwer_publishing",
                        }
                    ],
                )
                mark_processed(conn, file_path)
                print("  -> Saved to ChromaDB.")
            except Exception as e:
                print(f"  Upsert failed: {e}")


def _run():
    print("Starting Vision Daemon...")
    conn = init_db()
    try:
        client = chromadb.HttpClient(host=CHROMA_HOST, port=CHROMA_PORT)
        collection = client.get_or_create_collection(COLLECTION_NAME)
    except Exception as e:
        print(f"Failed to connect to ChromaDB: {e}")
        return

    while True:
        for directory in TARGET_DIRS:
            process_directory(conn, collection, directory)

        print("Sleeping for 60 seconds before next scan loop...")
        time.sleep(60)


if __name__ == "__main__":
    _run()
