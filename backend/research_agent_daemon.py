import time
import hashlib
import httpx
import chromadb

try:
    from duckduckgo_search import DDGS

    HAS_DDGS = True
except ImportError:
    DDGS = None
    HAS_DDGS = False

try:
    from tools.vertex_mcp_client import VertexMCPClient

    HAS_VERTEX_MCP = True
except ImportError:
    HAS_VERTEX_MCP = False

CHROMA_HOST = "localhost"
CHROMA_PORT = 8001
OLLAMA_EMBED_URL = os.environ.get("OLLAMA_EMBED_URL", "http://127.0.0.1:11435/api/embeddings")
EMBED_MODEL = "nomic-embed-text"


def _embed(text: str):
    try:
        with httpx.Client(timeout=30.0) as client:
            r = client.post(
                OLLAMA_EMBED_URL, json={"model": EMBED_MODEL, "prompt": text}
            )
            r.raise_for_status()
            return r.json().get("embedding", [])
    except Exception as e:
        print(f"[RESEARCH-AGENT] Embedding error: {e}")
        return None


def scrape_and_ingest():
    print("[RESEARCH-AGENT] Waking up to gather market intelligence...")

    try:
        client = chromadb.HttpClient(host=CHROMA_HOST, port=CHROMA_PORT)
        collection = client.get_or_create_collection(COLLECTION_NAME)
    except Exception as e:
        print(f"[RESEARCH-AGENT] Chroma connection failed. Retrying later. Error: {e}")
    if not HAS_DDGS:
        print(
            "[RESEARCH-AGENT] duckduckgo_search library not installed. Running in standby mode."
        )
        return

    queries = [
        "Most profitable crypto to mine on RTX 4090",
        "Salad compute container optimization workloads",
        "Vast.ai latest GPU rental rates",
    ]

    ddgs = DDGS()

    for query in queries:
        print(f"[RESEARCH-AGENT] Searching: {query}")

        # 1. Google Vertex AI RAG Ingestion (Sovereign Sync)
        if HAS_VERTEX_MCP:
            print("    -> Querying Vertex AI MCP /mcp/retrieval")
            try:
                mcp_client = VertexMCPClient(
                    "https://aiplatform.googleapis.com/mcp/retrieval"
                )
                mcp_results = mcp_client.call_tool(
                    "retrieve_contexts", {"query": query}
                )

                # Assuming the MCP tool returns a list of context strings or dicts in 'contexts'
                contexts = mcp_results.get("contexts", [])
                for idx, ctx in enumerate(contexts):
                    text_content = ctx if isinstance(ctx, str) else str(ctx)
                    vector = _embed(text_content)
                    if vector:
                        eid = hashlib.sha256(
                            (query + text_content).encode()
                        ).hexdigest()[:24]
                        collection.upsert(
                            ids=[eid],
                            documents=[text_content],
                            embeddings=[vector],
                            metadatas=[
                                {
                                    "source": "vertex_ai_mcp",
                                    "query": query,
                                    "client_id": "stehouwer_publishing",
                                }
                            ],
                        )
                print(f"    -> Ingested {len(contexts)} contexts from Vertex AI.")
            except Exception as e:
                print(f"    -> Vertex MCP failed for '{query}': {e}")

        # 2. DuckDuckGo OSINT Ingestion
        if HAS_DDGS:
            try:
                results = list(ddgs.text(query, max_results=3))
                for res in results:
                    title = res.get("title", "")
                    snippet = res.get("body", "")
                    url = res.get("href", "")

                    content = f"Title: {title}\nURL: {url}\nContent: {snippet}"
                    vector = _embed(content)

                    if vector:
                        eid = hashlib.sha256(content.encode()).hexdigest()[:24]
                        try:
                            collection.upsert(
                                ids=[eid],
                                documents=[content],
                                embeddings=[vector],
                                metadatas=[
                                    {
                                        "source": url,
                                        "query": query,
                                        "client_id": "stehouwer_publishing",
                                    }
                                ],
                            )
                            print(f"    -> Ingested (DDG): {title[:40]}...")
                        except Exception as ex:
                            print(f"    -> Failed to upsert (DDG): {ex}")
            except Exception as e:
                print(f"[RESEARCH-AGENT] DDG Search failed for '{query}': {e}")

    print("[RESEARCH-AGENT] Sleep cycle initiated.")


if __name__ == "__main__":
    print("[RESEARCH-AGENT] Booting Automated Web-Scraping Agent...")
    while True:
        scrape_and_ingest()
        # Sleep for 12 hours before fetching fresh data
        time.sleep(43200)
