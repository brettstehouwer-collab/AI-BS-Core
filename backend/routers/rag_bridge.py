import os
from typing import Optional, Dict, Any, List
import httpx
from fastapi import APIRouter
from pydantic import BaseModel
import chromadb
from chromadb.utils import embedding_functions

router = APIRouter(prefix="/rag", tags=["RAG Services"])

HOT_DB_DIR = r"C:\AI-BS\stehouwer_vector_memory"
RESOURCE_DIR = r"E:\AI_BS_Resources\ChromaDB"

_hot_client = None
_resource_client = None
_embedding_fn = None

def get_embedding_function():
    global _embedding_fn
    if _embedding_fn is None:
        _embedding_fn = embedding_functions.DefaultEmbeddingFunction()
    return _embedding_fn

def get_hot_client():
    global _hot_client
    if _hot_client is None:
        _hot_client = chromadb.PersistentClient(path=HOT_DB_DIR)
    return _hot_client

def get_resource_client():
    global _resource_client
    if _resource_client is None and os.path.exists(RESOURCE_DIR):
        try:
            _resource_client = chromadb.PersistentClient(path=RESOURCE_DIR)
        except Exception:
            _resource_client = None
    return _resource_client

class RagQuery(BaseModel):
    industry_id: Optional[str] = None
    query_text: Optional[str] = None
    query: Optional[str] = None
    collection: Optional[str] = None
    top_k: Optional[int] = None
    n_results: Optional[int] = 3
    synthesize: Optional[bool] = False
    category: Optional[str] = None

OLLAMA_URL = os.environ.get("OLLAMA_HOST_EDRIVE_GEN", "http://127.0.0.1:11435/api/generate")
OLLAMA_MODEL = "stehouwer_llm" # Fast local model

def find_collection(name: str):
    """Searches hot client first, then resource client for the requested collection."""
    fn = get_embedding_function()
    hot = get_hot_client()
    try:
        return hot.get_collection(name=name, embedding_function=fn)
    except Exception:
        pass

    res_cli = get_resource_client()
    if res_cli:
        try:
            return res_cli.get_collection(name=name, embedding_function=fn)
        except Exception:
            pass
    return None

@router.post("/query")
@router.post("/api/rag/query")
async def query_rag(req: RagQuery):
    effective_query = req.query or req.query_text or ""
    effective_n = req.top_k or req.n_results or 3
    
    # Determine candidate collection names
    candidates = []
    if req.collection:
        candidates.append(req.collection)
    if req.industry_id:
        candidates.append(f"rag_{req.industry_id}")
        candidates.append(f"synced_{req.industry_id}")
        candidates.append(req.industry_id)
    candidates.append("ai_bs_synced_drive_assets")
    
    target_collection = None
    matched_name = None
    for cand in candidates:
        target_collection = find_collection(cand)
        if target_collection:
            matched_name = cand
            break

    if not target_collection:
        return {
            "status": "error",
            "message": f"None of the candidate collections {candidates} could be located in ChromaDB storage."
        }

    try:
        where_filter = None
        if req.category:
            where_filter = {"category": req.category}

        query_kwargs = {
            "query_texts": [effective_query],
            "n_results": effective_n
        }
        if where_filter:
            query_kwargs["where"] = where_filter

        results = target_collection.query(**query_kwargs)

        formatted_results = []
        ids = results.get("ids", [[]])[0] if results.get("ids") else []
        docs = results.get("documents", [[]])[0] if results.get("documents") else []
        metas = results.get("metadatas", [[]])[0] if results.get("metadatas") else []
        dists = results.get("distances", [[]])[0] if results.get("distances") else [0.0] * len(ids)

        for d_id, doc, meta, dist in zip(ids, docs, metas, dists):
            formatted_results.append({
                "id": d_id,
                "document": doc,
                "metadata": meta,
                "distance": dist
            })

        # If synthesis isn't requested, return formatted results + raw results
        if not req.synthesize:
            return {
                "status": "success",
                "collection": matched_name,
                "count": len(formatted_results),
                "results": formatted_results,
                "raw_results": results
            }

        # Synthesize with Ollama
        contexts = docs
        sources = metas

        if not contexts or not any(c.strip() for c in contexts):
            return {
                "status": "success",
                "answer": "I do not have enough context in my local knowledge base to answer this.",
                "sources": [],
                "results": formatted_results
            }

        context_string = "\n\n---\n\n".join(contexts)
        prompt = f"""You are a professional AI Research Assistant.
Answer the user's query strictly using ONLY the following context extracted from local PDFs. If the context does not contain the answer, say so. Do not hallucinate external information.

Context:
{context_string}

Query: {effective_query}
Answer:"""

        try:
            async with httpx.AsyncClient() as http_client:
                ollama_res = await http_client.post(OLLAMA_URL, json={
                    "model": OLLAMA_MODEL,
                    "prompt": prompt,
                    "stream": False
                }, timeout=10.0)

                ollama_data = ollama_res.json()
                answer = ollama_data.get("response", "Error synthesizing response.")

                return {
                    "status": "success",
                    "answer": answer,
                    "sources": sources,
                    "raw_context": contexts,
                    "results": formatted_results
                }
        except Exception:
            return {
                "status": "success",
                "answer": f"[Context retrieved from {matched_name}] " + contexts[0][:300],
                "sources": sources,
                "results": formatted_results
            }

    except Exception as e:
        return {"status": "error", "message": str(e)}

@router.get("/status")
def rag_status():
    return {
        "status": "ChromaDB RAG Bridge online.",
        "hot_db": HOT_DB_DIR,
        "resource_db": RESOURCE_DIR,
        "master_collection": "ai_bs_synced_drive_assets"
    }
