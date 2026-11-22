import os
import hashlib
import httpx
import chromadb
from pathlib import Path
import fitz  # PyMuPDF
from docx import Document

TARGET_DRIVES = ["G:\\", "S:\\"]

# Must be lowercase for case-insensitive matching
EXCLUDED_DIRS = {
    "windows",
    "windows boot",
    "windowsapps",
    "wpsystem",
    "mobiunlockcache",
    ".gradle",
    ".android",
    ".gemini",
    ".antigravity-ide",
    ".ollama",
    ".config",
    ".securecoder",
    "program files",
    "program files (x86)",
    "programs",
    "steamlibrary",
    "xboxgames",
    "battle net",
    "ea games",
    "gog games",
    "msi afterburner",
    "rivatuner statistics server",
    "google phtos download from drive 2013",
    "$recycle.bin",
    "system volume information",
    "appdata",
    "cache",
    "temp",
    "tmp"}

ALLOWED_EXTENSIONS = {
    '.md',
    '.txt',
    '.csv',
    '.html',
    '.pdf',
    '.docx',
    '.json',
    '.py'}

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
    except Exception:
        # print(f"Embedding error: {e}")
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


def extract_pdf_text(file_path):
    text = ""
    try:
        doc = fitz.open(file_path)
        for page in doc:
            text += page.get_text("text") + "\n"
    except Exception:
        pass
    return text


def extract_docx_text(file_path):
    text = ""
    try:
        doc = Document(file_path)
        for para in doc.paragraphs:
            text += para.text + "\n"
    except Exception:
        pass
    return text


def process_file(file_path: Path):
    chunks = []
    content = ""
    ext = file_path.suffix.lower()

    if ext == '.pdf':
        content = extract_pdf_text(file_path)
    elif ext == '.docx':
        content = extract_docx_text(file_path)
    else:
        try:
            content = file_path.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            pass

    if content:
        chunks = chunk_text(content, delimiter='\n', max_len=1000)
    return chunks


def main():
    try:
        client = chromadb.HttpClient(host=CHROMA_HOST, port=CHROMA_PORT)
        collection = client.get_or_create_collection(COLLECTION_NAME)
    except Exception as e:
        print(f"Chroma connection failed: {e}")
        return

    total_files = 0
    total_success = 0
    total_chunks = 0

    for drive in TARGET_DRIVES:
        if not os.path.exists(drive):
            print(f"Drive not found: {drive}")
            continue

        print(f"\nScanning {drive}...")
        for root, dirs, files in os.walk(drive):
            # Actively modify dirs in-place to prevent os.walk from entering
            # excluded directories
            dirs[:] = [d for d in dirs if d.lower() not in EXCLUDED_DIRS]

            for f in files:
                file_path = Path(root) / f
                if file_path.suffix.lower() not in ALLOWED_EXTENSIONS:
                    continue

                chunks = process_file(file_path)
                if not chunks:
                    continue

                total_files += 1
                total_chunks += len(chunks)
                success = 0

                print(f"Processing: {file_path}")

                for i, chunk in enumerate(chunks):
                    # Skip tiny noise chunks
                    if len(chunk) < 15:
                        continue

                    rel_path = str(file_path).replace("\\", "/")
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
                            metadatas=[{"source": f"DriveScan/{rel_path}", "chunk_index": i}]
                        )
                        success += 1
                    except Exception:
                        pass

                # print(f"  -> {success}/{len(chunks)} chunks ingested.")
                total_success += success

    print(
        f"\nCompleted Drive Ingestion! Ingested {total_success} chunks across {total_files} files.")


if __name__ == "__main__":
    main()
