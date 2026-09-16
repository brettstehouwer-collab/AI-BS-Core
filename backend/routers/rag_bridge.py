import os
import httpx
from fastapi import APIRouter
from pydantic import BaseModel
import chromadb

router = APIRouter(prefix="/rag", tags=["RAG Services"])

RESOURCE_DIR = "E:\\AI_BS_Resources"
CHROMA_DIR = os.path.join(RESOURCE_DIR, "ChromaDB")

_chroma_client = None

def get_chroma_client():
    global _chroma_client
    if _chroma_client is None:
        _chroma_client = chromadb.PersistentClient(path=CHROMA_DIR)
    return _chroma_client

class RagQuery(BaseModel):
    industry_id: str
    query_text: str
    n_results: int = 3
    synthesize: bool = True

OLLAMA_URL = os.environ.get("OLLAMA_HOST_EDRIVE_GEN", "http://127.0.0.1:11435/api/generate")
OLLAMA_MODEL = "stehouwer_llm" # Fast local model

@router.post("/query")
@router.post("/api/rag/query")
async def query_rag(req: RagQuery):
    client = get_chroma_client()
    collection_name = f"rag_{req.industry_id}"
    
    try:
        collection = client.get_collection(name=collection_name)
        results = collection.query(
            query_texts=[req.query_text],
            n_results=req.n_results
        )
        
        # If synthesis isn't requested, just return raw Chroma results
        if not req.synthesize:
            return {"status": "success", "results": results}

        # Synthesize with Ollama
        contexts = results.get("documents", [[]])[0]
        sources = results.get("metadatas", [[]])[0]
        
        if not contexts:
            return {"status": "success", "answer": "I do not have enough context in my local knowledge base to answer this.", "sources": []}

        context_string = "\n\n---\n\n".join(contexts)
        prompt = f"""You are a professional AI Research Assistant.
Answer the user's query strictly using ONLY the following context extracted from local PDFs. If the context does not contain the answer, say so. Do not hallucinate external information.

Context:
{context_string}

Query: {req.query_text}
Answer:"""

        async with httpx.AsyncClient() as http_client:
            ollama_res = await http_client.post(OLLAMA_URL, json={
                "model": OLLAMA_MODEL,
                "prompt": prompt,
                "stream": False
            }, timeout=60.0)
            
            ollama_data = ollama_res.json()
            answer = ollama_data.get("response", "Error synthesizing response.")
            
            return {
                "status": "success", 
                "answer": answer,
                "sources": sources,
                "raw_context": contexts
            }
            
    except Exception as e:
        return {"status": "error", "message": str(e)}

@router.get("/status")
def rag_status():
    return {"status": "ChromaDB RAG Bridge online. LLM Synthesis via Ollama enabled."}
