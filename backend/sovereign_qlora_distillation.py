import json
import os
import sqlite3
import time
from datetime import datetime
from pathlib import Path

WORKSPACE_ROOT = Path(r"C:\AI-BS")
DATABASE_DIR = WORKSPACE_ROOT / "database"
DATABASE_DIR.mkdir(parents=True, exist_ok=True)

CHROMA_SQLITE = WORKSPACE_ROOT / "backend" / "stehouwer_vector_memory" / "chroma.sqlite3"
AIBS_MASTER_DB = WORKSPACE_ROOT / "backend" / "aibs_master.db"
LEARNING_DB = DATABASE_DIR / "learning_data.db"
TRACES_DB = DATABASE_DIR / "reasoning_traces_pending.db"

OUTPUT_DATASET = DATABASE_DIR / "Sovereign_Distillation_Dataset_v1.jsonl"
OUTPUT_CONFIG = DATABASE_DIR / "sovereign_qlora_4090_config.json"


SYSTEM_PROMPT = (
    "You are Stehouwer LLM, the sovereign cognitive engine and executive controller of the AI-BS ecosystem (C:\\AI-BS). "
    "You possess direct authority over 43 supervised modules, 18 collision-free ports, multi-shell host execution (/ps, /cmd, /wsl, /run), "
    "and universal file systems with automatic .bak backup discipline. Answer accurately, decisively, and idiomatically."
)


def extract_from_chroma():
    """Pulls high-value conversational context and memory chunks from local Chroma SQLite database."""
    items = []
    if not CHROMA_SQLITE.exists():
        return items

    try:
        conn = sqlite3.connect(str(CHROMA_SQLITE))
        c = conn.cursor()
        c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='embeddings'")
        if c.fetchone():
            c.execute("SELECT document FROM embeddings WHERE document IS NOT NULL AND length(document) > 50 LIMIT 500")
            for row in c.fetchall():
                doc = row[0].strip()
                if "user:" in doc.lower() and "assistant:" in doc.lower():
                    items.append(doc)
        conn.close()
    except Exception as e:
        print(f"[WARN] Chroma extraction notice: {e}")
    return items


def extract_from_learning_data():
    """Extracts accepted patterns, reasoning traces, and user-approved code edits."""
    pairs = []
    if LEARNING_DB.exists():
        try:
            conn = sqlite3.connect(str(LEARNING_DB))
            c = conn.cursor()
            tables = [r[0] for r in c.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()]
            for tbl in tables:
                cols = [r[1] for r in c.execute(f"PRAGMA table_info({tbl})").fetchall()]
                if "prompt" in cols and "response" in cols:
                    c.execute(f"SELECT prompt, response FROM {tbl} WHERE length(prompt) > 10 AND length(response) > 10 LIMIT 300")
                    for p, r in c.fetchall():
                        pairs.append({"prompt": str(p).strip(), "response": str(r).strip()})
            conn.close()
        except Exception as e:
            print(f"[WARN] Learning DB notice: {e}")
    return pairs


def generate_sovereign_curricula():
    """Synthesizes high-leverage architectural curricula reflecting C:\\AI-BS realities."""
    curricula = [
        {
            "prompt": "What are the core rules of the AI-BS Native Windows Desktop Architecture?",
            "response": (
                "The AI-BS Native Windows Desktop Architecture strictly mandates:\n"
                "1. Zero Browser Engines: No Electron, Chromium, WebView2, or browser tabs for native desktop apps.\n"
                "2. Zero Local Web Servers for Desktop UI: Desktop software interfaces must run genuine native toolkits (PyQt6/PySide6, Dear PyGui, Win32/C++, WPF).\n"
                "3. Real-Time Latency Prevention: Decouple GUI event loops via QThread/ThreadPool, route audio through WASAPI/ASIO with MMCSS 'Pro Audio' thread priority 15, and use pre-allocated lock-free ring buffers.\n"
                "4. Standalone Binaries: Compile to standalone .exe binaries with Authenticode SHA-256 code signing."
            )
        },
        {
            "prompt": "How does the AI-BS Executive Multi-Runtime Router handle script execution across shells?",
            "response": (
                "The Executive Router (/api/executive/run) dynamically routes scripts based on runtime type:\n"
                "- PowerShell: Executed directly via powershell.exe -NoProfile -ExecutionPolicy Bypass.\n"
                "- Command Prompt: Dispatched via cmd.exe /c.\n"
                "- WSL2 / Bash: Bridged directly into Ubuntu/Ubuntu-24.04 via wsl.exe -d <distro> -e bash -c.\n"
                "- Native runtimes (Python, Node.js, TS, Go, Rust, C/C++, SQL): Dispatched to local toolchains (pyppeteer_env, tsx, go run, rustc, g++, duckdb) with automatic .bak backup preservation."
            )
        },
        {
            "prompt": "How does the Autonomous Self-Healing Execution Loop debug failing code blocks?",
            "response": (
                "When a script exits with returncode != 0 or an active stderr traceback in BS-Chat:\n"
                "1. The CodeBlock catches the stderr traceback and original source code.\n"
                "2. If Auto-Heal is enabled, it sends {code, stderr, runtime_type} to /api/executive/auto-heal.\n"
                "3. The backend invokes local qwen2.5-coder with grammar-constrained JSON mode (format: 'json') to guarantee a schema-locked {root_cause, fix_explanation, fixed_code} payload.\n"
                "4. BS-Chat hot-swaps the syntax view with the repaired code and re-runs the script autonomously (up to 3 retry attempts)."
            )
        },
        {
            "prompt": "Explain the AST Blast-Radius Engine (/blast & /graph) in AI-BS.",
            "response": (
                "The AST Blast-Radius Engine indexes all 78 FastAPI routers and 193 React frontend components into SQLite tables (blast_radius_nodes and blast_radius_edges) in aibs_master.db. "
                "Running /blast <target> computes both upstream dependencies (which UI components or API callers depend on this route) and downstream impacts (what routes or child components break if modified), assigning risk tiers: LOW, MEDIUM, or CRITICAL."
            )
        },
        {
            "prompt": "What is the port topology of the supervised AI-BS daemons?",
            "response": (
                "AI-BS operates an 18-port collision-free ecosystem supervised by shm_heartbeat_supervisor.go and daemon_supervisor:\n"
                "- Port 8000: Go API Gateway\n"
                "- Port 8080: FastAPI Core Ecosystem Daemon\n"
                "- Port 8001: ChromaDB Vector Memory Vault\n"
                "- Port 11434: Local Ollama Neural Engine (Primary GPU, NVIDIA RTX 4090 24GB)\n"
                "- Port 11435: Shadow Ollama Engine (CPU Fallback)\n"
                "- Port 3001: Frontend React Matrix UI"
            )
        }
    ]
    return curricula


def build_distillation_dataset():
    """Compiles ShareGPT / Alpaca JSONL dataset for QLoRA fine-tuning."""
    total_records = 0
    curricula = generate_sovereign_curricula()
    learned_pairs = extract_from_learning_data()
    chroma_chunks = extract_from_chroma()

    with open(OUTPUT_DATASET, "w", encoding="utf-8") as f:
        # 1. High-leverage architecture curricula
        for item in curricula:
            record = {
                "messages": [
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": item["prompt"]},
                    {"role": "assistant", "content": item["response"]}
                ]
            }
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
            total_records += 1

        # 2. Learned vault pairs
        for pair in learned_pairs:
            record = {
                "messages": [
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": pair["prompt"]},
                    {"role": "assistant", "content": pair["response"]}
                ]
            }
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
            total_records += 1

        # 3. Supplemental persona turns if available
        base_persona = DATABASE_DIR / "Unified_Stehouwer_Persona_v3.jsonl"
        if base_persona.exists():
            with open(base_persona, "r", encoding="utf-8", errors="ignore") as pf:
                for line in pf:
                    l = line.strip()
                    if l:
                        f.write(l + "\n")
                        total_records += 1

    # 4. Generate Unsloth / PEFT RTX 4090 24GB Training Configuration
    config = {
        "pipeline_name": "AI-BS Sovereign Nightly QLoRA Distillation",
        "timestamp": datetime.now().isoformat(),
        "hardware": {
            "device": "NVIDIA GeForce RTX 4090",
            "vram_gb": 24.0,
            "target_headroom_vram_gb": 13.5
        },
        "model_spec": {
            "base_model": "Qwen/Qwen2.5-Coder-7B-Instruct",
            "load_in_4bit": True,
            "quant_type": "nf4",
            "compute_dtype": "bfloat16",
            "max_seq_length": 4096
        },
        "lora_config": {
            "r": 16,
            "lora_alpha": 32,
            "lora_dropout": 0.05,
            "bias": "none",
            "target_modules": ["q_proj", "k_proj", "v_proj", "o_proj", "gate_proj", "up_proj", "down_proj"]
        },
        "training_hyperparameters": {
            "batch_size_per_device": 2,
            "gradient_accumulation_steps": 4,
            "learning_rate": 2e-4,
            "lr_scheduler_type": "cosine",
            "weight_decay": 0.01,
            "warmup_ratio": 0.05,
            "optimizer": "adamw_8bit",
            "max_steps": 100,
            "save_steps": 50,
            "logging_steps": 10
        },
        "dataset_path": str(OUTPUT_DATASET),
        "total_training_examples": total_records,
        "export_target": {
            "format": "GGUF_Q5_K_M",
            "ollama_tag": "stehouwer_llm:sovereign_distilled",
            "output_directory": r"E:\AI_BS_Resources\Sovereign_LoRA_Distillation"
        }
    }

    with open(OUTPUT_CONFIG, "w", encoding="utf-8") as cf:
        json.dump(config, cf, indent=2)

    return {
        "status": "success",
        "dataset_path": str(OUTPUT_DATASET),
        "config_path": str(OUTPUT_CONFIG),
        "total_records": total_records
    }


if __name__ == "__main__":
    res = build_distillation_dataset()
    print("DISTILLATION DATASET RESULT:", res)
