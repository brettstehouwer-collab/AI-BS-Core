import os
import time
import json
import random
import asyncio
import httpx
import shutil
import sys
import re
import argparse
from urllib.parse import urlparse
from neural_router import NeuralRouter
from bullshit_memory import INDEX_FILE

VAULT_DIR = r"C:\AI-BS\AI-BS_Knowledge_Vaults"


# ==============================================================================
# Corpus Scraper Logic
# ==============================================================================
def clean_html(html: str) -> str:
    html = re.sub(r"<script.*?>.*?</script>", "", html, flags=re.DOTALL)
    html = re.sub(r"<style.*?>.*?</style>", "", html, flags=re.DOTALL)
    html = re.sub(r"<[^>]+>", " ", html)
    html = re.sub(r"\s+", " ", html)
    return html.strip()


async def archive_url(url: str):
    print(f"[Bullshit Sponge] Initiating corpus extraction for: {url}")
    try:
        async with httpx.AsyncClient(follow_redirects=True) as client:
            res = await client.get(url, timeout=30.0)
            if res.status_code == 200:
                text_content = clean_html(res.text)

                domain = urlparse(url).netloc.replace(".", "_")
                filename = f"Corpus_Archive_{domain}.md"
                filepath = os.path.join(VAULT_DIR, filename)

                os.makedirs(VAULT_DIR, exist_ok=True)

                with open(filepath, "w", encoding="utf-8") as f:
                    f.write(f"# Auto-Archived Source: {url}\n\n")
                    f.write(text_content)

                print(
                    f"[Bullshit Sponge] Successfully ingested {len(text_content)} bytes into {filename}"
                )
                return True
            else:
                print(f"[Bullshit Sponge Error] HTTP {res.status_code}")
                return False
    except Exception as e:
        print(f"[Bullshit Sponge Error] {e}")
        return False


# ==============================================================================
# Hunter Gatherer Logic
# ==============================================================================
TOPICS = [
    "language:python stars:>5000",
    "language:javascript stars:>5000",
    "language:powershell stars:>500",
    "topic:machine-learning stars:>1000",
    "topic:fastapi stars:>1000",
]


def health_check():
    total, used, free = shutil.disk_usage(os.path.abspath(os.sep))
    free_gb = free // (2**30)
    if free_gb < 5:
        print(
            f"[Failsafe] CRITICAL: Only {free_gb}GB of free space left. Halting Bullshit Sponge automatically."
        )
        sys.exit(1)


def inject_knowledge(name, chunk, embedding):
    try:
        if os.path.exists(INDEX_FILE):
            with open(INDEX_FILE, "r", encoding="utf-8") as f:
                index_data = json.load(f)
        else:
            index_data = []

        if any(item.get("file") == f"github_{name}" for item in index_data):
            print("[Bullshit Sponge] Knowledge already exists in vault. Skipping.")
            return

        index_data.append(
            {"file": f"github_{name}", "chunk": chunk, "embedding": embedding}
        )

        with open(INDEX_FILE, "w", encoding="utf-8") as f:
            json.dump(index_data, f)

        print(f"[Bullshit Sponge] Successfully injected '{name}' into Vector Vault.")
    except Exception as e:
        print(f"[Bullshit Sponge] Injection error: {e}")


async def hunt_for_knowledge():
    print("[Bullshit Sponge] Waking up to forage for new knowledge...")
    topic = random.choice(TOPICS)
    print(f"[Bullshit Sponge] Target Topic: {topic}")

    url = (
        f"https://api.github.com/search/repositories?q={topic}&sort=updated&order=desc"
    )

    try:
        async with httpx.AsyncClient() as client:
            res = await client.get(url, timeout=15.0)
            if res.status_code == 200:
                data = res.json()
                items = data.get("items", [])
                if not items:
                    print("[Bullshit Sponge] No items found.")
                    return

                repo = random.choice(items[:5])
                name = repo.get("name")
                desc = repo.get("description")
                html_url = repo.get("html_url")

                if not desc:
                    return

                knowledge_chunk = (
                    f"GITHUB REPOSITORY: {name}. URL: {html_url}. DESCRIPTION: {desc}."
                )
                print(f"[Bullshit Sponge] Harvested: {name}")

                router = NeuralRouter()
                embedding = await router.route_to_embedder(knowledge_chunk)
                if embedding:
                    inject_knowledge(name, knowledge_chunk, embedding)
            elif res.status_code == 403:
                print("[Bullshit Sponge] GitHub API Rate limit hit. Sleeping...")
            else:
                print(f"[Bullshit Sponge] Failed to fetch: {res.status_code}")
    except Exception as e:
        print(f"[Bullshit Sponge] Hunting error: {e}")


async def main_loop():
    print("==================================================")
    print("Bullshit Sponge Daemon Initialized.")
    print("Autonomous knowledge collection active.")
    print("==================================================")

    while True:
        health_check()
        await hunt_for_knowledge()
        await asyncio.sleep(300)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--url", type=str, required=False, help="URL to ingest into the vault."
    )
    args = parser.parse_args()

    if args.url:
        asyncio.run(archive_url(args.url))
    else:
        asyncio.run(main_loop())
