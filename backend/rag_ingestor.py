import os
import glob
from PyPDF2 import PdfReader
import chromadb
import uuid

RESOURCE_DIR = "E:\\AI_BS_Resources"
CHROMA_DIR = os.path.join(RESOURCE_DIR, "ChromaDB")
DATASETS_DIR = os.path.join(RESOURCE_DIR, "Datasets")

# Map folder names to the precise ChromaDB collection keys we already established
FOLDER_TO_COLLECTION_MAP = {
    "Medical": "rag_medical",
    "DeepTech": "rag_quantum" # Mapping DeepTech to quantum for now, or we can use aerospace etc.
}

def chunk_text(text, chunk_size=1000, overlap=200):
    chunks = []
    start = 0
    while start < len(text):
        end = min(start + chunk_size, len(text))
        chunks.append(text[start:end])
        start += chunk_size - overlap
    return chunks

def ingest_pdfs():
    client = chromadb.PersistentClient(path=CHROMA_DIR)
    
    for folder, collection_name in FOLDER_TO_COLLECTION_MAP.items():
        folder_path = os.path.join(DATASETS_DIR, folder)
        os.makedirs(folder_path, exist_ok=True)
        
        pdf_files = glob.glob(os.path.join(folder_path, "*.pdf"))
        if not pdf_files:
            print(f"No PDFs found in {folder_path}. Drop some files there.")
            continue
            
        print(f"Processing {len(pdf_files)} PDFs in {folder_path} for collection {collection_name}...")
        collection = client.get_or_create_collection(name=collection_name)
        
        for pdf_path in pdf_files:
            print(f" - Ingesting: {os.path.basename(pdf_path)}")
            try:
                reader = PdfReader(pdf_path)
                full_text = ""
                for page in reader.pages:
                    text = page.extract_text()
                    if text:
                        full_text += text + "\n"
                        
                chunks = chunk_text(full_text)
                
                documents = []
                metadatas = []
                ids = []
                
                for i, chunk in enumerate(chunks):
                    doc_id = f"{os.path.basename(pdf_path)}_{uuid.uuid4().hex[:8]}_{i}"
                    documents.append(chunk)
                    metadatas.append({"source": os.path.basename(pdf_path), "page_chunk": i})
                    ids.append(doc_id)
                
                if documents:
                    # Upsert handles inserting or updating
                    collection.upsert(
                        documents=documents,
                        metadatas=metadatas,
                        ids=ids
                    )
                    print(f"   -> Inserted {len(documents)} chunks.")
            except Exception as e:
                print(f"   [!] Failed to parse {pdf_path}: {e}")

if __name__ == "__main__":
    print("Starting AI-BS RAG Ingestion Pipeline...")
    ingest_pdfs()
    print("Ingestion complete.")
