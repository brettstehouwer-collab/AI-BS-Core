"""AI-BS Native Service Orchestrator & On-Demand Lifecycle Manager.

Ensures all subsystems, generative AI backends, vector vaults, databases,
and low-latency audio/video pipelines execute strictly on-demand in pure native Win32 form:
- ComfyUI Ultra-HD Generative Studio (Port 8189) auto-spawn & AST workflow dispatch
- Ollama Neural Fleet (Port 11434 / 11435) auto-spawn & streaming bridge
- Broadcast Kernel NVENC (Port 8088), VST3 (Port 8013)
- ChromaDB Vector Vaults (in-process SQLite & remote Port 8002)
- SQLite Master Vaults ('stehouwer_vault.db' 139,512 records)
- Demucs CUDA 4-Stem Audio Isolation on RTX 4090
"""

from __future__ import annotations

import json
import os
import random
import socket
import sqlite3
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

import httpx

AI_BS_ROOT = Path(r"C:\AI-BS")
COMFY_DIR = AI_BS_ROOT / "ComfyUI"
COMFY_PYTHON = COMFY_DIR / "python_embeded" / "python.exe"
COMFY_MAIN = COMFY_DIR / "ComfyUI" / "main.py"
COMFY_HOST = "http://127.0.0.1:8189"
OLLAMA_HOST = "http://127.0.0.1:11434"
FASTAPI_HOST = "http://127.0.0.1:8080"


def probe_port(port: int, host: str = "127.0.0.1", timeout: float = 0.5) -> bool:
    """Fast non-blocking socket probe to check if a local service is listening."""
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except (socket.timeout, ConnectionRefusedError, OSError):
        return False


def ensure_comfyui_online(
    timeout_s: float = 25.0,
    status_cb: Optional[Callable[[str], None]] = None,
) -> Tuple[bool, str]:
    """Ensures ComfyUI on Port 8189 is active. Auto-launches on demand if offline."""
    if probe_port(8189):
        return True, "ComfyUI is already online on Port 8189"

    if status_cb:
        status_cb("⚡ [COMFYUI ON-DEMAND]: Port 8189 is offline. Spawning ComfyUI renderer with RTX 4090 acceleration...")

    # Validate ComfyUI installation files
    if not COMFY_PYTHON.exists() or not COMFY_MAIN.exists():
        err_msg = f"ComfyUI executable or main.py not found at {COMFY_PYTHON}"
        if status_cb:
            status_cb(f"❌ [COMFYUI ERROR]: {err_msg}")
        return False, err_msg

    # Build launch command
    cmd = [
        str(COMFY_PYTHON),
        "-s",
        str(COMFY_MAIN),
        "--port", "8189",
        "--highvram",
        "--dont-print-server",
    ]

    log_path = AI_BS_ROOT / "logs" / "comfyui_ondemand.log"
    log_path.parent.mkdir(parents=True, exist_ok=True)

    flags = 0
    if sys.platform == "win32":
        flags = subprocess.CREATE_NEW_PROCESS_GROUP | 0x08000000  # CREATE_NO_WINDOW

    try:
        log_file = open(log_path, "a", encoding="utf-8")
        subprocess.Popen(
            cmd,
            cwd=str(COMFY_DIR),
            stdout=log_file,
            stderr=subprocess.STDOUT,
            creationflags=flags,
        )
    except Exception as e:
        err_msg = f"Failed to spawn ComfyUI process: {e}"
        if status_cb:
            status_cb(f"❌ [COMFYUI ERROR]: {err_msg}")
        return False, err_msg

    # Poll port 8189 until ready
    start_t = time.time()
    while time.time() - start_t < timeout_s:
        if probe_port(8189):
            # Verify HTTP endpoint responds
            try:
                r = httpx.get(f"{COMFY_HOST}/system_stats", timeout=1.5)
                if r.status_code == 200:
                    msg = "✅ ComfyUI is now ONLINE on Port 8189 (RTX 4090 VRAM ready)!"
                    if status_cb:
                        status_cb(f"⚡ [COMFYUI ON-DEMAND]: {msg}")
                    return True, msg
            except Exception:
                pass
        time.sleep(1.0)

    err_msg = f"Timed out waiting for ComfyUI to bind to Port 8189 ({timeout_s}s)."
    if status_cb:
        status_cb(f"⚠️ [COMFYUI WARNING]: {err_msg}")
    return False, err_msg


def ensure_ollama_online(
    timeout_s: float = 12.0,
    status_cb: Optional[Callable[[str], None]] = None,
) -> Tuple[bool, str]:
    """Ensures Dual-Port Ollama Swarm (11434 GPU / 11435 CPU Embeddings) is active."""
    p11434 = probe_port(11434)
    p11435 = probe_port(11435)
    if p11434 and p11435:
        return True, "Ollama Dual-Port Swarm is online (11434 GPU & 11435 CPU Embeddings)"

    if status_cb:
        status_cb("🧠 [OLLAMA ON-DEMAND]: Spawning sovereign Dual-Port Ollama swarm (11434 GPU / 11435 CPU AVX-512)...")

    try:
        from backend.aibs_ecosystem_spawner import activate_all_daemons
        activate_all_daemons(verbose=False)
    except Exception:
        pass

    start_t = time.time()
    while time.time() - start_t < timeout_s:
        if probe_port(11434) and probe_port(11435):
            msg = "✅ Ollama Dual-Port Swarm is now ONLINE (11434 GPU & 11435 CPU Embeddings)!"
            if status_cb:
                status_cb(f"🧠 [OLLAMA ON-DEMAND]: {msg}")
            return True, msg
        time.sleep(0.8)

    if probe_port(11434):
        return True, "Ollama GPU Node (11434) is online"

    return False, f"Timed out waiting for Ollama Swarm ({timeout_s}s)."


def ensure_broadcast_suite_online(
    status_cb: Optional[Callable[[str], None]] = None,
) -> Tuple[bool, str]:
    """Request the existing native broadcast and VST3 service batch."""
    bat_path = AI_BS_ROOT / "Launch_Studio_Suite_OnDemand.bat"
    if bat_path.exists():
        if status_cb:
            status_cb("📡 [BROADCAST ON-DEMAND]: Requesting Broadcast Kernel (Port 8088) and VST3 Bridge (Port 8013)...")
        try:
            flags = subprocess.CREATE_NEW_PROCESS_GROUP | 0x08000000 if sys.platform == "win32" else 0
            subprocess.Popen(["cmd.exe", "/c", str(bat_path)], cwd=str(AI_BS_ROOT), creationflags=flags)
            return True, "Broadcast suite daemons engaged"
        except Exception as e:
            return False, f"Broadcast launch error: {e}"
    return False, "Launch_Studio_Suite_OnDemand.bat not found"


def dispatch_comfy_generation(
    prompt: str,
    kind: str = "image",
    tier: str = "4K",
    aspect: str = "16:9",
    negative_prompt: str = "blurry, low quality, distorted, bad anatomy, deformed",
    status_cb: Optional[Callable[[str], None]] = None,
) -> Dict[str, Any]:
    """Auto-spawns ComfyUI on demand, generates AST workflow, submits to Port 8189, and tracks output."""
    ok, msg = ensure_comfyui_online(timeout_s=30.0, status_cb=status_cb)
    if not ok:
        return {"status": "error", "message": f"Could not launch ComfyUI: {msg}"}

    # Import AST graph builders
    try:
        from backend.core.comfy_workflow_builders import (
            build_sdxl_txt2img_graph,
            build_sd15_txt2img_graph,
            build_wan21_t2v_graph,
            build_ltx_video_graph,
        )
    except Exception as e:
        return {"status": "error", "message": f"Failed to import ComfyUI workflow builders: {e}"}

    seed = random.randint(1000000000, 9999999999)
    if kind == "video":
        if status_cb:
            status_cb(f"🎬 [WAN2.1/LTX]: Building high-temporal motion graph for: '{prompt}'...")
        try:
            graph = build_wan21_t2v_graph(prompt=prompt, negative_prompt=negative_prompt, seed=seed)
        except Exception:
            graph = build_sdxl_txt2img_graph(prompt=prompt, negative_prompt=negative_prompt, target_tier=tier, aspect_ratio=aspect, seed=seed)
    else:
        if status_cb:
            status_cb(f"🎨 [COMFYUI]: Building {tier} {aspect} Ultra-HD AST workflow graph for: '{prompt}'...")
        graph = build_sdxl_txt2img_graph(
            prompt=prompt,
            negative_prompt=negative_prompt,
            target_tier=tier,
            aspect_ratio=aspect,
            seed=seed,
        )

    # Submit to ComfyUI Port 8189
    try:
        with httpx.Client(timeout=15.0) as client:
            res = client.post(f"{COMFY_HOST}/prompt", json={"prompt": graph})
            if res.status_code != 200:
                return {"status": "error", "message": f"ComfyUI rejected prompt ({res.status_code}): {res.text}"}
            data = res.json()
            prompt_id = data.get("prompt_id")
            if not prompt_id:
                return {"status": "error", "message": "No prompt_id returned by ComfyUI"}

        if status_cb:
            status_cb(f"🚀 [COMFYUI RUNNING]: Dispatched to RTX 4090 GPU! Prompt ID: {prompt_id}\nRendering {tier} Master...")

        # Poll history for finished generation
        output_images = []
        poll_start = time.time()
        with httpx.Client(timeout=5.0) as client:
            while time.time() - poll_start < 120.0:
                try:
                    h_res = client.get(f"{COMFY_HOST}/history/{prompt_id}")
                    if h_res.status_code == 200:
                        h_data = h_res.json()
                        if prompt_id in h_data:
                            outputs = h_data[prompt_id].get("outputs", {})
                            for node_id, node_out in outputs.items():
                                if "images" in node_out:
                                    for img in node_out["images"]:
                                        fn = img.get("filename")
                                        subfolder = img.get("subfolder", "")
                                        full_p = COMFY_DIR / "output" / subfolder / fn if subfolder else COMFY_DIR / "output" / fn
                                        output_images.append(str(full_p))
                                if "gifs" in node_out or "videos" in node_out:
                                    vids = node_out.get("gifs", []) + node_out.get("videos", [])
                                    for vid in vids:
                                        fn = vid.get("filename")
                                        output_images.append(str(COMFY_DIR / "output" / fn))
                            if output_images:
                                break
                except Exception:
                    pass
                time.sleep(1.5)

        if output_images:
            if status_cb:
                status_cb(f"🎉 [COMFYUI COMPLETE]: Rendered {len(output_images)} asset(s)!\nFile: {output_images[0]}")
            return {"status": "ok", "prompt_id": prompt_id, "outputs": output_images}

        # Staged successfully even if async rendering continues
        return {
            "status": "queued",
            "prompt_id": prompt_id,
            "message": f"Job active in ComfyUI queue (Prompt ID: {prompt_id}). Output will save to {COMFY_DIR / 'output'}",
        }

    except Exception as e:
        return {"status": "error", "message": f"Network error during prompt dispatch: {e}"}


def query_sqlite_vault(query_text: str, limit: int = 10) -> List[Dict[str, Any]]:
    """Direct native SQLite querying into stehouwer_vault.db (139,512 records)."""
    db_path = AI_BS_ROOT / "backend" / "stehouwer_vault.db"
    if not db_path.exists():
        db_path = AI_BS_ROOT / "stehouwer_vault.db"
    if not db_path.exists():
        return [{"error": f"Database not found: {db_path}"}]

    results = []
    try:
        conn = sqlite3.connect(f"{db_path.as_uri()}?mode=ro", uri=True, timeout=3.0)
        conn.execute("PRAGMA query_only = ON")
        cur = conn.cursor()

        # Find tables
        tables = cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'").fetchall()
        for (tname,) in tables:
            # Get text columns
            cols_info = cur.execute(f"PRAGMA table_info(\"{tname}\")").fetchall()
            text_cols = [c[1] for c in cols_info if any(t in str(c[2]).upper() for t in ("TEXT", "CHAR", "VARCHAR", ""))]
            if not text_cols:
                continue

            where_clauses = [f"\"{col}\" LIKE ?" for col in text_cols]
            sql = f"SELECT * FROM \"{tname}\" WHERE {' OR '.join(where_clauses)} LIMIT ?"
            params = [f"%{query_text}%"] * len(text_cols) + [limit]
            try:
                rows = cur.execute(sql, params).fetchall()
                for r in rows:
                    col_names = [c[1] for c in cols_info]
                    rec = dict(zip(col_names, r))
                    rec["_table"] = tname
                    results.append(rec)
                    if len(results) >= limit:
                        break
            except Exception:
                pass
            if len(results) >= limit:
                break
        conn.close()
    except Exception as e:
        return [{"error": str(e)}]

    return results


def query_chroma_vectors(query_text: str, n_results: int = 5) -> List[Dict[str, Any]]:
    """Queries ChromaDB vector embeddings across Port 8001 / Port 8002 / in-process, ranking across all 768-dim and 384-dim collections."""
    os.environ["ORT_LOGGING_LEVEL"] = "3"
    chroma_dir = Path(r"E:\AI_BS_Resources\ChromaDB") if Path(r"E:\AI_BS_Resources\ChromaDB").exists() else (AI_BS_ROOT / "chroma_db")
    candidates: List[Dict[str, Any]] = []

    # Extract meaningful query keywords for hybrid lexical + semantic ranking
    import re
    q_tokens = [t for t in re.findall(r"[\w\-]{4,}", query_text) if t.lower() not in {"what", "where", "when", "which", "search", "query", "find", "from", "with", "that", "this", "about"}]

    # Get 768-dim embedding from Ollama nomic-embed-text (Port 11435 CPU AVX-512 or 11434 GPU)
    vec_768 = None
    for port in (11435, 11434):
        try:
            with httpx.Client(timeout=3.0) as client:
                r = client.post(f"http://127.0.0.1:{port}/api/embeddings", json={"model": "nomic-embed-text", "prompt": query_text})
                if r.status_code == 200:
                    vec_768 = r.json().get("embedding")
                    if vec_768:
                        break
        except Exception:
            pass

    def _score_and_collect(col_name: str, q_res: dict, port_num: Any) -> None:
        if not q_res or not q_res.get("documents") or not q_res["documents"][0]:
            return
        docs = q_res["documents"][0]
        metas = (q_res.get("metadatas") or [[]])[0]
        dists = (q_res.get("distances") or [[1.0] * len(docs)])[0]
        for idx, d in enumerate(docs):
            if not d:
                continue
            m = metas[idx] if idx < len(metas) else {}
            dist = float(dists[idx]) if idx < len(dists) and dists[idx] is not None else 1.0
            d_low = d.lower()
            # Hybrid score: lower distance is better; exact token hits subtract from distance score
            kw_hits = sum(1 for tok in q_tokens if tok.lower() in d_low)
            rank_score = dist - (kw_hits * 50.0)
            if col_name == "ai_bs_context_memory":
                rank_score -= 10.0  # slight boost for user's actively offloaded 1M RAG files
            candidates.append({
                "collection": col_name,
                "document": d,
                "metadata": m,
                "distance": round(dist, 4),
                "kw_hits": kw_hits,
                "_rank": rank_score,
                "port": port_num,
            })

    # 1. Try HTTP Port 8001 (Primary) or Port 8002
    for p in (8001, 8002):
        if probe_port(p):
            try:
                import chromadb
                client = chromadb.HttpClient(host="127.0.0.1", port=p)
                all_col_names = {c.name for c in client.list_collections()}

                # 768-dim collections (nomic-embed-text)
                cols_768 = [
                    name for name in [
                        "ai_bs_context_memory",
                        "stehouwer_vector_memory",
                        "screenplay_thejudgemadehimgo",
                        "screenplay_echoeswithin",
                        "screenplay_judge",
                        "market_intelligence",
                        "research_intelligence",
                    ] if name in all_col_names
                ]

                for c_name in cols_768:
                    try:
                        col = client.get_collection(c_name, embedding_function=None)
                        if col.count() == 0:
                            continue
                        # Exact token filter check first for needle-in-a-haystack precision
                        for tok in q_tokens[:2]:
                            if len(tok) >= 6:
                                try:
                                    exact_res = col.get(where_document={"$contains": tok}, limit=3)
                                    if exact_res and exact_res.get("documents"):
                                        _score_and_collect(
                                            c_name,
                                            {
                                                "documents": [exact_res["documents"]],
                                                "metadatas": [exact_res.get("metadatas") or [{} for _ in exact_res["documents"]]],
                                                "distances": [[0.01 for _ in exact_res["documents"]]],
                                            },
                                            p,
                                        )
                                except Exception:
                                    pass
                        if vec_768:
                            q_res = col.query(query_embeddings=[vec_768], n_results=min(n_results, 3), include=["documents", "metadatas", "distances"])
                            _score_and_collect(c_name, q_res, p)
                    except Exception:
                        pass

                # 384-dim collections (stehouwer_llm_memory [39K], rag_root_knowledge [7.7K], industry_knowledge_vault [5.8K])
                cols_384 = [
                    name for name in [
                        "stehouwer_llm_memory",
                        "rag_root_knowledge",
                        "industry_knowledge_vault",
                        "ai_bs_master_history",
                    ] if name in all_col_names
                ]
                for c_name in cols_384:
                    try:
                        col = client.get_collection(c_name, embedding_function=None)
                        for tok in q_tokens[:2]:
                            if len(tok) >= 5:
                                exact_res = col.get(where_document={"$contains": tok}, limit=2)
                                if exact_res and exact_res.get("documents"):
                                    _score_and_collect(
                                        c_name,
                                        {
                                            "documents": [exact_res["documents"]],
                                            "metadatas": [exact_res.get("metadatas") or [{} for _ in exact_res["documents"]]],
                                            "distances": [[0.05 for _ in exact_res["documents"]]],
                                        },
                                        p,
                                    )
                    except Exception:
                        pass

                if candidates:
                    # Deduplicate by full document text and sort by best rank_score
                    candidates.sort(key=lambda x: x["_rank"])
                    deduped = []
                    seen_docs = set()
                    for item in candidates:
                        sig = item["document"]
                        if sig not in seen_docs:
                            seen_docs.add(sig)
                            item.pop("_rank", None)
                            deduped.append(item)
                            if len(deduped) >= n_results:
                                break
                    return deduped
            except Exception:
                pass

    # 2. Try in-process persistent client fallback
    try:
        import chromadb
        client = chromadb.PersistentClient(path=str(chroma_dir))
        for col_ref in client.list_collections()[:4]:
            try:
                col = client.get_collection(col_ref.name, embedding_function=None)
                if vec_768:
                    q_res = col.query(query_embeddings=[vec_768], n_results=min(n_results, 2), include=["documents", "metadatas", "distances"])
                    _score_and_collect(col_ref.name, q_res, "local")
            except Exception:
                pass
        if candidates:
            candidates.sort(key=lambda x: x["_rank"])
            for c in candidates:
                c.pop("_rank", None)
            return candidates[:n_results]
    except Exception:
        pass

    return [{"message": f"Vector search scanned '{chroma_dir}': 0 matching embeddings for '{query_text}'"}]


def audit_zombie_nodes_native() -> Dict[str, Any]:
    """Audits running processes and returns zombie/orphan count and details."""
    try:
        from backend.zombie_node_cleaner import audit_zombie_nodes
        return audit_zombie_nodes()
    except Exception as e:
        return {"count": 0, "total_reclaimable_mb": 0.0, "zombies": [], "error": str(e)}


def sweep_zombie_nodes_native(dry_run: bool = False) -> Dict[str, Any]:
    """Executes safe sweep of zombie nodes and returns reclaimed memory metrics."""
    try:
        from backend.zombie_node_cleaner import sweep_zombie_nodes
        return sweep_zombie_nodes(dry_run=dry_run)
    except Exception as e:
        return {"status": "ERROR", "terminated_count": 0, "freed_mb": 0.0, "actions": [str(e)]}

