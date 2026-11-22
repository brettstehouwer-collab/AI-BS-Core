import httpx
import chromadb

CHROMA_HOST = "localhost"
CHROMA_PORT = 8001
COLLECTION_NAME = "ai_bs_context_memory"
OLLAMA_EMBED_URL = "http://127.0.0.1:11434/api/embeddings"
EMBED_MODEL = "nomic-embed-text"


def get_query_embedding(text):
    try:
        with httpx.Client(timeout=30.0) as client:
            r = client.post(
                OLLAMA_EMBED_URL,
                json={
                    "model": EMBED_MODEL,
                    "prompt": text})
            r.raise_for_status()
            return r.json().get("embedding", [])
    except Exception as e:
        print(f"Failed to generate query embedding: {e}")
        return None


def run_test(query_text):
    print(f"\n--- Running Semantic Test Query: '{query_text}' ---")

    # 1. Embed the query
    vector = get_query_embedding(query_text)
    if not vector:
        return

    # 2. Query ChromaDB
    try:
        client = chromadb.HttpClient(host=CHROMA_HOST, port=CHROMA_PORT)
        collection = client.get_collection(COLLECTION_NAME)

        results = collection.query(
            query_embeddings=[vector],
            n_results=3,
            include=['documents', 'metadatas']
        )

        if not results['documents'][0]:
            print("No matching results found in the database.")
            return

        for i, (doc, meta) in enumerate(
                zip(results['documents'][0], results['metadatas'][0])):
            print(
                f"\nResult {
                    i +
                    1} [Source: {
                    meta.get(
                        'source',
                        'Unknown')}]")
            print(f"Content Preview: {doc[:150].strip()}...\n")

    except Exception as e:
        print(f"ChromaDB Query Failed: {e}")


if __name__ == "__main__":
    test_queries = [
        "architecture of AI-BS matrix memory",
        "local vault manuscript drafts",
        "description of a photo or image"
    ]

    for q in test_queries:
        run_test(q)
