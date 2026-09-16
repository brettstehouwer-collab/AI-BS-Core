import os
import re
import asyncio
import json
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Dict, Any, List, Optional
import chromadb
import httpx

CHROMA_HOST = "127.0.0.1"
CHROMA_PORT = 8001
OLLAMA_URL = "http://127.0.0.1:11434"
EMBED_MODEL = "nomic-embed-text"
CHAT_MODEL = "stehouwer_dolphin:latest"
SCREENPLAY_ROOT = Path("C:/AI-BS/screenplay_projects")


def get_chroma_client():
    try:
        return chromadb.HttpClient(host=CHROMA_HOST, port=CHROMA_PORT)
    except Exception as e:
        print(f"[ProjectRAG] ChromaDB HTTP error: {e}, falling back to persistent client.")
        return chromadb.PersistentClient(path="C:/AI-BS/backend/chroma_db")


def get_project_collection_name(project_name: str) -> str:
    clean = re.sub(r'[^a-zA-Z0-9]', '', project_name.lower())
    if not clean:
        clean = "default"
    return f"screenplay_{clean}"


def parse_fdx_content(fdx_xml_string: str) -> List[Dict[str, Any]]:
    """
    Parses Final Draft XML (.fdx) format into structured scene blocks.
    Extracts Scene Headings, Action, Characters, Dialogue, and Parentheticals.
    """
    scenes = []
    try:
        root = ET.fromstring(fdx_xml_string)
        current_scene = {
            "heading": "SCENE START",
            "text": "",
            "characters": set(),
            "dialogue_count": 0
        }
        
        # Find all Paragraph elements inside Content
        for para in root.iter("Paragraph"):
            p_type = para.attrib.get("Type", "Action")
            
            # Extract text from all Text child nodes
            text_parts = []
            for text_elem in para.findall("Text"):
                if text_elem.text:
                    text_parts.append(text_elem.text)
            para_text = "".join(text_parts).strip()
            if not para_text:
                continue

            if p_type == "Scene Heading":
                if current_scene["text"].strip():
                    current_scene["characters"] = list(current_scene["characters"])
                    scenes.append(current_scene)
                current_scene = {
                    "heading": para_text,
                    "text": f"{para_text}\n\n",
                    "characters": set(),
                    "dialogue_count": 0
                }
            elif p_type == "Character":
                current_scene["characters"].add(para_text)
                current_scene["text"] += f"\n{para_text}\n"
            elif p_type == "Dialogue":
                current_scene["dialogue_count"] += 1
                current_scene["text"] += f"{para_text}\n"
            elif p_type == "Parenthetical":
                current_scene["text"] += f"({para_text})\n"
            else:
                current_scene["text"] += f"{para_text}\n\n"

        if current_scene["text"].strip():
            current_scene["characters"] = list(current_scene["characters"])
            scenes.append(current_scene)

    except Exception as e:
        print(f"[ProjectRAG] FDX XML parse warning: {e}")

    return scenes


def parse_fdx_file(file_path: Path) -> List[Dict[str, Any]]:
    if not file_path.exists():
        return []
    try:
        content = file_path.read_text(encoding="utf-8", errors="ignore")
        return parse_fdx_content(content)
    except Exception as e:
        print(f"[ProjectRAG] Error reading FDX file {file_path}: {e}")
        return []


async def get_embedding_async(text: str, client: Optional[httpx.AsyncClient] = None) -> List[float]:
    close_client = False
    if client is None:
        client = httpx.AsyncClient(timeout=15.0)
        close_client = True
    try:
        r = await client.post(f"{OLLAMA_URL}/api/embeddings", json={"model": EMBED_MODEL, "prompt": text[:4000]})
        if r.status_code == 200:
            return r.json().get("embedding", [0.0] * 768)
    except Exception as e:
        print(f"[ProjectRAG] Embedding generation error: {e}")
    finally:
        if close_client:
            await client.aclose()
    return [0.0] * 768


def get_embedding_sync(text: str) -> List[float]:
    try:
        with httpx.Client(timeout=15.0) as client:
            r = client.post(f"{OLLAMA_URL}/api/embeddings", json={"model": EMBED_MODEL, "prompt": text[:4000]})
            if r.status_code == 200:
                return r.json().get("embedding", [0.0] * 768)
    except Exception as e:
        print(f"[ProjectRAG] Sync embedding error: {e}")
    return [0.0] * 768


def get_project_stats(project_name: str) -> Dict[str, Any]:
    col_name = get_project_collection_name(project_name)
    try:
        client = get_chroma_client()
        col = client.get_collection(col_name)
        total_count = col.count()
        
        book_count = 0
        scene_count = 0
        fdx_count = 0
        if total_count > 0:
            peek = col.get(limit=min(total_count, 200), include=["metadatas"])
            metas = peek.get("metadatas", [])
            for m in metas:
                m_type = m.get("type", "")
                if m_type == "script_scene":
                    scene_count += 1
                elif m_type == "fdx_scene":
                    fdx_count += 1
                else:
                    book_count += 1
                    
        return {
            "status": "success",
            "project_name": project_name,
            "collection_name": col_name,
            "total_docs": total_count,
            "book_chunks": book_count,
            "script_scenes": scene_count,
            "fdx_scenes": fdx_count
        }
    except Exception as e:
        return {
            "status": "not_found",
            "project_name": project_name,
            "collection_name": col_name,
            "total_docs": 0,
            "book_chunks": 0,
            "script_scenes": 0,
            "fdx_scenes": 0,
            "message": str(e)
        }


async def sync_project_screenplay(project_name: str, fountain_text: Optional[str] = None) -> Dict[str, Any]:
    col_name = get_project_collection_name(project_name)
    client = get_chroma_client()
    col = client.get_or_create_collection(col_name)

    project_dir = SCREENPLAY_ROOT / project_name
    ids = []
    docs = []
    metas = []
    embeddings = []

    async with httpx.AsyncClient(timeout=30.0) as http_client:
        # 1. Parse .fdx files if present
        if project_dir.exists():
            fdx_files = list(project_dir.glob("*.fdx"))
            for fdx_file in fdx_files:
                fdx_scenes = parse_fdx_file(fdx_file)
                for s_idx, scene in enumerate(fdx_scenes):
                    s_text = scene["text"].strip()
                    if not s_text:
                        continue
                    doc_id = f"fdx_{fdx_file.stem}_{s_idx+1}"
                    emb = await get_embedding_async(s_text[:2000], http_client)
                    ids.append(doc_id)
                    docs.append(s_text)
                    embeddings.append(emb)
                    metas.append({
                        "type": "fdx_scene",
                        "scene_number": s_idx + 1,
                        "heading": scene["heading"][:120],
                        "characters": ", ".join(scene.get("characters", []))[:200],
                        "source_file": fdx_file.name,
                        "project": project_name
                    })

        # 2. Parse Fountain text
        content = fountain_text
        if not content and project_dir.exists():
            script_file = project_dir / "screenplay.fountain"
            if script_file.exists():
                content = script_file.read_text(encoding="utf-8", errors="ignore")

        if content:
            scenes = re.split(r'\n(?=(?:INT\.|EXT\.|INT\./EXT\.|EXT\./INT\.))', content)
            for i, scene_text in enumerate(scenes):
                scene_text = scene_text.strip()
                if not scene_text:
                    continue
                lines = scene_text.splitlines()
                heading = lines[0] if lines else f"SCENE {i+1}"
                doc_id = f"scene_{i+1}"
                
                emb = await get_embedding_async(scene_text[:2000], http_client)
                ids.append(doc_id)
                docs.append(scene_text)
                embeddings.append(emb)
                metas.append({
                    "type": "script_scene",
                    "scene_number": i + 1,
                    "heading": heading[:120],
                    "project": project_name
                })

        # 3. Parse chunks.json (Manuscript Book Source)
        if project_dir.exists():
            chunks_file = project_dir / "chunks.json"
            if chunks_file.exists():
                try:
                    chunks_data = json.loads(chunks_file.read_text(encoding="utf-8", errors="ignore"))
                    for c_idx, chunk in enumerate(chunks_data):
                        c_text = chunk.get("text", "") if isinstance(chunk, dict) else str(chunk)
                        c_text = c_text.strip()
                        if not c_text:
                            continue
                        doc_id = f"book_chunk_{c_idx+1}"
                        emb = await get_embedding_async(c_text[:2000], http_client)
                        ids.append(doc_id)
                        docs.append(c_text)
                        embeddings.append(emb)
                        metas.append({
                            "type": "book_chunk",
                            "chunk_index": c_idx + 1,
                            "chapter": chunk.get("chapter", f"Chapter {c_idx+1}") if isinstance(chunk, dict) else f"Chunk {c_idx+1}",
                            "project": project_name
                        })
                except Exception as c_err:
                    print(f"[ProjectRAG] Error ingesting chunks.json: {c_err}")

    if docs:
        col.upsert(ids=ids, embeddings=embeddings, documents=docs, metadatas=metas)
        print(f"[ProjectRAG] Upserted {len(docs)} total documents (FDX, Fountain, Book) into {col_name}. Total count: {col.count()}")

    return {
        "status": "success",
        "project_name": project_name,
        "collection_name": col_name,
        "indexed_docs": len(docs),
        "total_docs": col.count()
    }


async def query_project_rag_assistant(
    project_name: str,
    user_query: str,
    n_results: int = 5,
    custom_model: Optional[str] = None
) -> Dict[str, Any]:
    col_name = get_project_collection_name(project_name)
    client = get_chroma_client()
    
    try:
        col = client.get_collection(col_name)
    except Exception as e:
        return {
            "status": "error",
            "message": f"Project vector database '{col_name}' does not exist yet. Please adapt or sync the project first.",
            "response": f"Project memory for '{project_name}' has not been initialized yet. Please click '🔄 Sync DB' to index your screenplay and book into this project's isolated Vector DB.",
            "sources": []
        }

    q_emb = await get_embedding_async(user_query)
    query_res = col.query(query_embeddings=[q_emb], n_results=min(n_results, max(1, col.count())))

    matched_docs = query_res.get("documents", [[]])[0]
    matched_metas = query_res.get("metadatas", [[]])[0]

    book_excerpts = []
    script_excerpts = []
    sources = []

    for doc, meta in zip(matched_docs, matched_metas):
        m_type = meta.get("type", "unknown")
        if m_type == "script_scene":
            heading = meta.get("heading", "SCENE")
            scene_num = meta.get("scene_number", "?")
            script_excerpts.append(f"[SCREENPLAY SCENE #{scene_num}: {heading}]\n{doc}")
            sources.append({
                "type": "script_scene",
                "label": f"Scene #{scene_num}: {heading}",
                "excerpt": doc[:300] + "..." if len(doc) > 300 else doc
            })
        else:
            chunk_num = meta.get("chunk_index", meta.get("chunk", "?"))
            book_excerpts.append(f"[ORIGINAL BOOK / MEMOIR CHUNK #{chunk_num}]\n{doc}")
            sources.append({
                "type": "book_source",
                "label": f"Book Manuscript Chunk #{chunk_num}",
                "excerpt": doc[:300] + "..." if len(doc) > 300 else doc
            })

    context_str = ""
    if book_excerpts:
        context_str += "=== ORIGINAL BOOK / MEMOIR SOURCES ===\n" + "\n\n".join(book_excerpts) + "\n\n"
    if script_excerpts:
        context_str += "=== CURRENT SCREENPLAY DRAFT SCENES ===\n" + "\n\n".join(script_excerpts) + "\n\n"

    system_prompt = f"""You are the Dedicated AI Script & Memoir Assistant for the project '{project_name}'.
You have access ONLY to this project's isolated ChromaDB Vector Database containing its original book/memoir manuscript and its current screenplay draft.

STRICT EDITORIAL RULES:
1. STRICT TRUTH & FIDELITY: Base all answers, scene references, character motivations, and dialogue suggestions strictly on the retrieved context below. Do not invent outside fictional characters or events.
2. CITATIONS: When answering, reference whether information came from the Original Book Manuscript or the Current Screenplay Draft (mentioning scene numbers or chapters when available).
3. FORMATTING: If generating or rewriting dialogue or scenes, output clean, industry-standard Fountain syntax.
4. TONE: Professional, supportive, Hollywood creative executive and story doctor.

{context_str}"""

    target_model = custom_model or CHAT_MODEL
    llm_payload = {
        "model": target_model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_query}
        ],
        "stream": False,
        "options": {
            "temperature": 0.2,
            "top_p": 0.9
        }
    }

    ai_response = ""
    try:
        async with httpx.AsyncClient(timeout=45.0) as http_client:
            res = await http_client.post(f"{OLLAMA_URL}/api/chat", json=llm_payload)
            if res.status_code == 200:
                ai_response = res.json().get("message", {}).get("content", "")
            else:
                ai_response = f"AI Generation error ({res.status_code}): {res.text}"
    except Exception as e:
        ai_response = f"Assistant query error: {str(e)}"

    return {
        "status": "success",
        "project_name": project_name,
        "collection_name": col_name,
        "response": ai_response,
        "sources": sources,
        "context_docs_count": len(matched_docs)
    }
