import os
import glob
import sys
import uuid
import time
from chroma_storage import chroma_manager

RECOVERED_DIR = r"C:\AI-BS\backend\recovered_modules"

def main():
    print(f"Starting Recovered Modules Ingestion from {RECOVERED_DIR}...")
    log_files = glob.glob(os.path.join(RECOVERED_DIR, "*.log"))
    
    if not log_files:
        print("No .log files found in recovered_modules.")
        sys.exit(0)
        
    print(f"Found {len(log_files)} recovered chat log files. Parsing...")
    
    texts = []
    metadatas = []
    ids = []
    
    for filepath in log_files:
        try:
            with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
                if len(content) > 50:  # Skip empty or tiny noise files
                    texts.append(content)
                    metadatas.append({
                        "source": "recovered_modules",
                        "file_source": os.path.basename(filepath),
                        "role": "recovered_intelligence",
                        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
                    })
                    ids.append(f"recovered_{uuid.uuid4().hex[:8]}")
        except Exception as e:
            print(f"Error reading {filepath}: {e}")

    if not texts:
        print("No valid textual data found to ingest.")
        sys.exit(0)

    print(f"Prepared {len(texts)} chunks. Injecting into ChromaDB via NLP Parser...")

    batch_size = 10
    total_added = 0
    for i in range(0, len(texts), batch_size):
        batch_texts = texts[i:i+batch_size]
        batch_metas = metadatas[i:i+batch_size]
        batch_ids = ids[i:i+batch_size]

        try:
            chroma_manager.add_communication_styles_batch(
                batch_texts, batch_metas, batch_ids
            )
            total_added += len(batch_texts)
            print(f"Injected batch {i//batch_size + 1}... ({total_added}/{len(texts)})")
        except Exception as e:
            print(f"Failed to inject batch {i//batch_size + 1}: {e}")

    print(f"\nIngestion Complete! Successfully embedded {total_added} recovered logs into Stehouwer LLM memory.")

if __name__ == "__main__":
    main()
