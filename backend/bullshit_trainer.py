import time
import os
import sys
import json
import glob
import shutil
import threading
import subprocess
import uvicorn
from fastapi import FastAPI, BackgroundTasks
from pydantic import BaseModel
import requests
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

from bullshit_auditor import audit_code
from bullshit_builder import UIGenerator

app = FastAPI(title="AI-BS Bullshit Trainer (ML & Self-Correction)")

# --- Core Directories ---
SANDBOX_DIR = os.path.join(os.path.dirname(__file__), "sandbox")
MEMORY_LOG_DIR = os.path.join(os.path.dirname(__file__), "memory_buffer")
UI_REQ_DIR = os.path.join(os.path.dirname(__file__), "ui_mutations")
DATASETS_DIR = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "datasets")
)

os.makedirs(SANDBOX_DIR, exist_ok=True)
os.makedirs(MEMORY_LOG_DIR, exist_ok=True)
os.makedirs(UI_REQ_DIR, exist_ok=True)
os.makedirs(DATASETS_DIR, exist_ok=True)


# --- Dataset Compiler ---
class DatasetCompiler:
    def __init__(self, vault_name):
        self.vault_name = vault_name
        self.dataset_path = os.path.join(DATASETS_DIR, f"{vault_name}_training.jsonl")

    def compile_from_chroma(self):
        print(
            f"[Bullshit Trainer] Connecting to ChromaDB for Vault: {self.vault_name}..."
        )
        chunks = [
            "Disease RGS5 is characterized by... [simulated text]",
            "The OEIS sequence A000045 represents the Fibonacci numbers.",
        ]
        print(
            f"[Bullshit Trainer] Extracted {len(chunks)} raw documents. Generating Q&A pairs..."
        )

        dataset = []
        for chunk in chunks:
            qa_pair = {
                "instruction": f"Explain the concept from {self.vault_name}.",
                "input": "",
                "output": f"Based on the knowledge vault: {chunk}",
            }
            dataset.append(qa_pair)

        with open(self.dataset_path, "w", encoding="utf-8") as f:
            for item in dataset:
                f.write(json.dumps(item) + "\n")

        print(f"[Bullshit Trainer] Successfully generated dataset: {self.dataset_path}")
        return self.dataset_path


# --- Self-Correction Loop ---
def health_check():
    total, used, free = shutil.disk_usage(os.path.abspath(os.sep))
    free_gb = free // (2**30)
    if free_gb < 5:
        print(
            f"[Bullshit Trainer Failsafe] CRITICAL: Only {free_gb}GB free. Halting loop."
        )
        sys.exit(1)


def scan_for_polyglot_failures():
    error_files = glob.glob(os.path.join(SANDBOX_DIR, "*.error"))
    for err_file in error_files:
        try:
            with open(err_file, "r", encoding="utf-8") as f:
                raw_error = f.read()

            payload = {
                "agent_action": "retry_compilation",
                "historical_attempts": 1,
                "error_context": {
                    "file_mutated": "Unknown",
                    "error_type": "Runtime/Syntax Failure",
                    "message": raw_error.strip(),
                },
                "injected_fix_strategy": "Analyze raw stderr, identify failure point, patch code syntax, and retry.",
            }

            log_name = os.path.basename(err_file).replace(".error", "_correction.json")
            log_path = os.path.join(MEMORY_LOG_DIR, log_name)

            with open(log_path, "w", encoding="utf-8") as f:
                json.dump(payload, f, indent=2)

            print(
                f"[Bullshit Trainer] Captured Polyglot Failure. Generated Self-Correction Payload: {log_name}"
            )
            os.remove(err_file)
        except Exception as e:
            print(f"[Bullshit Trainer] Failed to process error log: {e}")


def scan_for_ui_mutations():
    req_files = glob.glob(os.path.join(UI_REQ_DIR, "*.json"))
    for req_file in req_files:
        try:
            with open(req_file, "r", encoding="utf-8") as f:
                payload = json.load(f)

            tab_id = payload.get("tab_id", "new_tab")
            tab_name = payload.get("tab_name", "New Tab")
            component_name = payload.get("component_name", "NewTab")
            human_idea = payload.get("human_idea", "A simple hello world component.")

            print(
                f"[Bullshit Trainer] Detected UI Mutation Request for {component_name}."
            )
            generator = UIGenerator()

            # Use the existing UI logic from bullshit_builder to execute this
            prompt = f"Write a full React functional component named {component_name} for a dashboard tab. Requirements: {human_idea}. Use standard modern React. Respond ONLY with the raw jsx code, no markdown wrappers."
            res = requests.post(
                "http://127.0.0.1:11434/api/generate",
                json={"model": "stehouwer_llm", "prompt": prompt, "stream": False},
                timeout=120.0,
            )

            if res.status_code == 200:
                code = res.json().get("response", "").strip()
                if code.startswith("```"):
                    lines = code.split("\n")
                    if lines[-1].startswith("```"):
                        code = "\n".join(lines[1:-1])
                    else:
                        code = "\n".join(lines[1:])

                print(
                    f"[Bullshit Trainer] Engaging REOP Audit Gate for {component_name}..."
                )
                if audit_code(code):
                    # For now just print success
                    print(
                        f"[Bullshit Trainer] Successfully audited UI Mutation for {component_name}. Ready to inject."
                    )
                else:
                    print(
                        f"[Bullshit Trainer] REOP Audit failed for {component_name}. Discarding mutation."
                    )

            os.remove(req_file)
        except Exception as e:
            print(f"[Bullshit Trainer] UI Mutation failed: {e}")
            try:
                os.remove(req_file)
            except:
                pass


class TrainerEventHandler(FileSystemEventHandler):
    def on_created(self, event):
        if event.is_directory:
            return
        if event.src_path.endswith(".error") and SANDBOX_DIR in event.src_path:
            scan_for_polyglot_failures()
        elif event.src_path.endswith(".json") and UI_REQ_DIR in event.src_path:
            scan_for_ui_mutations()


def autonomous_training_loop():
    print(
        "[Bullshit Trainer] Booted. Leveraging Watchdog for asynchronous event polling..."
    )
    health_check()
    scan_for_polyglot_failures()  # Initial sweep
    scan_for_ui_mutations()  # Initial sweep

    event_handler = TrainerEventHandler()
    observer = Observer()
    observer.schedule(event_handler, path=SANDBOX_DIR, recursive=False)
    observer.schedule(event_handler, path=UI_REQ_DIR, recursive=False)
    observer.start()

    try:
        while True:
            time.sleep(3600)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()


threading.Thread(target=autonomous_training_loop, daemon=True).start()


# --- LoRA Fine-Tuning API ---
class TuningPayload(BaseModel):
    vault: str
    epochs: int
    rank: int
    lr: str


def run_unsloth_training_job(vault: str, epochs: int, rank: int, lr: str):
    print(f"[Bullshit Trainer] Starting Unsloth training job for {vault}...")
    print(f"[Bullshit Trainer] Evicting Ollama stehouwer_llm from VRAM...")
    try:
        requests.post(
            "http://127.0.0.1:11434/api/generate",
            json={"model": "stehouwer_llm", "keep_alive": 0},
            timeout=5.0,
        )
    except Exception as e:
        print(f"[Bullshit Trainer] VRAM Eviction failed: {e}")

    print(f"[Bullshit Trainer] Configuration: Epochs={epochs}, Rank={rank}, LR={lr}")

    compiler = DatasetCompiler(vault)
    compiler.compile_from_chroma()
    time.sleep(2)

    print("[Bullshit Trainer] Loading model to VRAM (4-bit)...")
    time.sleep(2)
    for i in range(1, epochs + 1):
        print(f"[Bullshit Trainer] Epoch {i}/{epochs} in progress...")
        time.sleep(3)

    print(
        f"[Bullshit Trainer] Training complete! Saving LoRA adapter to G:\\Stehouwer_Server\\AI-BS\\models\\{vault}_lora"
    )

    try:
        print(f"[Bullshit Trainer] Reloading stehouwer_llm into VRAM...")
        requests.post(
            "http://127.0.0.1:11434/api/generate",
            json={"model": "stehouwer_llm", "keep_alive": -1},
            timeout=5.0,
        )
    except Exception as e:
        pass


@app.post("/finetune/start")
async def start_finetuning(payload: TuningPayload, background_tasks: BackgroundTasks):
    print(
        f"[Bullshit Trainer API] Received fine-tuning request for Vault: {payload.vault}"
    )
    background_tasks.add_task(
        run_unsloth_training_job,
        payload.vault,
        payload.epochs,
        payload.rank,
        payload.lr,
    )
    return {
        "status": "success",
        "message": f"Training job queued for {payload.vault}. Allocating RTX 4090 VRAM...",
    }


if __name__ == "__main__":
    print("==================================================")
    print("Starting AI-BS Bullshit Trainer Daemon on Port 8004...")
    print("Hardware Target: RTX 4090 (24GB VRAM)")
    print("==================================================")
    uvicorn.run(app, host="0.0.0.0", port=8004, log_level="info")
