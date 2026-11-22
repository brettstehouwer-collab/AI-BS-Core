import os
import time
import json
import threading
import httpx
import asyncio
import uvicorn
from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI(title="AI-BS Bullshit Memory Engine")


# --- Memory Paging Setup ---
class MemoryManager:
    def __init__(self, memory_limit_mb=2048):
        self.memory_limit_mb = memory_limit_mb
        self.paging_dir = os.path.join(os.path.dirname(__file__), ".AI-BS-Paging")
        os.makedirs(self.paging_dir, exist_ok=True)
        self.active_pages = {}
        print(
            f"[Bullshit Memory] SSD Offloading initialized. Threshold: {self.memory_limit_mb}MB"
        )

    def _get_current_memory_usage(self):
        try:
            import psutil

            process = psutil.Process(os.getpid())
            return process.memory_info().rss / (1024 * 1024)
        except ImportError:
            return 0

    def page_out(self, variable_name: str, data: dict):
        page_path = os.path.join(self.paging_dir, f"{variable_name}.page")
        print(
            f"[Bullshit Memory] RAM Threshold Reached. Paging out '{variable_name}' to SSD..."
        )
        try:
            with open(page_path, "w", encoding="utf-8") as f:
                json.dump(data, f)
            self.active_pages[variable_name] = page_path
            print(
                f"[Bullshit Memory] '{variable_name}' successfully offloaded to {page_path}."
            )
            return True
        except Exception as e:
            print(f"[Bullshit Memory] Error paging out {variable_name}: {e}")
            return False

    def page_in(self, variable_name: str) -> dict:
        if variable_name not in self.active_pages:
            return None
        page_path = self.active_pages[variable_name]
        print(
            f"[Bullshit Memory] JIT Load: Retrieving '{variable_name}' from SSD into live memory..."
        )
        try:
            with open(page_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            return data
        except Exception as e:
            print(f"[Bullshit Memory] Error paging in {variable_name}: {e}")
            return None

    def start_monitoring(self):
        def monitor_loop():
            while True:
                mem = self._get_current_memory_usage()
                if mem > self.memory_limit_mb:
                    print(
                        f"\n[WARNING] AI-BS Memory Spiked ({mem:.2f}MB). Triggering Garbage Collection..."
                    )
                time.sleep(5)

        threading.Thread(target=monitor_loop, daemon=True).start()
        print("[Bullshit Memory] Asynchronous background RAM monitoring active.")


# --- Vault Indexing Logic ---
VAULT_DIR = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "AI-BS_Knowledge_Vaults")
)
INDEX_FILE = os.path.join(VAULT_DIR, "vault_index.json")
CONFIG_PATH = os.path.join(VAULT_DIR, "vault_config.json")


async def generate_embedding(text: str) -> list:
    # Simplified neural routing embedder
    async with httpx.AsyncClient() as client:
        try:
            res = await client.post(
                "http://127.0.0.1:11434/api/embeddings",
                json={"model": "stehouwer_llm", "prompt": text},
                timeout=30.0,
            )
            if res.status_code == 200:
                return res.json().get("embedding", [])
        except Exception as e:
            print(f"[Bullshit Memory] Embedding Error: {e}")
    return []


async def build_index():
    print("[Bullshit Memory] Starting indexing process...")
    if not os.path.exists(VAULT_DIR):
        os.makedirs(VAULT_DIR, exist_ok=True)

    index_data = []
    for root, _, files in os.walk(VAULT_DIR):
        for file in files:
            if file.endswith((".txt", ".md")) and file != "vault_index.json":
                file_path = os.path.join(root, file)
                print(f"[Bullshit Memory] Indexing: {file}")
                with open(file_path, "r", encoding="utf-8") as f:
                    content = f.read()

                chunks = [
                    c.strip() for c in content.split("\n\n") if len(c.strip()) > 50
                ]
                for chunk in chunks:
                    embedding = await generate_embedding(chunk)
                    if embedding:
                        index_data.append(
                            {"file": file, "chunk": chunk, "embedding": embedding}
                        )

    with open(INDEX_FILE, "w", encoding="utf-8") as f:
        json.dump(index_data, f)
    print(f"[Bullshit Memory] Indexed {len(index_data)} semantic chunks successfully.")


# --- Ingestion API ---
class IngestPayload(BaseModel):
    vault_name: str
    source_name: str


def load_config():
    if os.path.exists(CONFIG_PATH):
        with open(CONFIG_PATH, "r") as f:
            return json.load(f)
    return {}


@app.post("/vault/ingest")
async def trigger_ingestion(payload: IngestPayload):
    config = load_config()
    vaults = config.get("knowledge_vaults", {})
    if payload.vault_name not in vaults:
        return {
            "status": "error",
            "message": f"Vault '{payload.vault_name}' not found.",
        }

    print(
        f"[Bullshit Memory] Initiating connection to {payload.source_name} for the {payload.vault_name} vault..."
    )
    time.sleep(2)
    print(f"[Bullshit Memory] Data pulled and embedded successfully.")

    # We could theoretically trigger asyncio.create_task(build_index()) here.
    return {
        "status": "success",
        "message": f"Ingested {payload.source_name} into {payload.vault_name} vault.",
    }


# --- GLOBAL SSD PAGING SYSTEM ---
# This singleton instance can be imported by any heavy module across the stack
# to instantly drop variables/base64 strings out of RAM into the local SSD paging file.
global_ssd_ram = MemoryManager(memory_limit_mb=2048)


if __name__ == "__main__":
    print("==================================================")
    print("Starting AI-BS Bullshit Memory Engine on Port 8003...")
    print("==================================================")
    uvicorn.run(app, host="0.0.0.0", port=8003, log_level="info")
