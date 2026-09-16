import os
import time
import json
import asyncio
from bullshit_memory import generate_embedding
from core.lexicon_service import LexiconService

HEURISTICS_DIR = r"C:\AI-BS\Heuristics"
ARCHIVE_FILE = os.path.join(HEURISTICS_DIR, "session_history_archive.json")
INDEX_FILE = r"C:\AI-BS\AI-BS_Knowledge_Vaults\vault_index.json"


async def tail_and_embed():
    print("[HeuristicsDaemon] Initialized. Watching for new pipeline failures...")

    if not os.path.exists(HEURISTICS_DIR):
        os.makedirs(HEURISTICS_DIR, exist_ok=True)

    if not os.path.exists(ARCHIVE_FILE):
        open(ARCHIVE_FILE, "w").close()

    # Get initial file size to only read new lines
    last_pos = os.path.getsize(ARCHIVE_FILE)

    while True:
        current_size = os.path.getsize(ARCHIVE_FILE)
        if current_size > last_pos:
            print("[HeuristicsDaemon] New heuristic detected! Processing...")
            with open(ARCHIVE_FILE, "r") as f:
                f.seek(last_pos)
                new_data = f.readlines()
                last_pos = f.tell()

            for line in new_data:
                line = line.strip()
                if not line:
                    continue
                try:
                    payload = json.loads(line)
                    heuristic_text = payload.get("heuristic")
                    if heuristic_text:
                        # Lexicon Integration for Stehouwer Persona Engine
                        expansion = LexiconService.bulk_expand(heuristic_text)
                        if expansion:
                            syn_list = [syn for syns in expansion.values() for syn in syns]
                            heuristic_text += f"\n[Vocabulary Constraints: Use {', '.join(syn_list[:10])} when applicable]"

                        print(
                            f"[HeuristicsDaemon] Embedding new rule: {heuristic_text[:50]}..."
                        )
                        emb = await generate_embedding(heuristic_text)
                        if emb:
                            # Append to Vault Index
                            entry = {
                                "file": "session_history_archive.json",
                                "content": heuristic_text,
                                "embedding": emb,
                                "type": "heuristic_rule",
                            }
                            index_data = []
                            if os.path.exists(INDEX_FILE):
                                try:
                                    with open(INDEX_FILE, "r", encoding="utf-8") as vf:
                                        index_data = json.load(vf)
                                except:
                                    pass
                            index_data.append(entry)
                            with open(INDEX_FILE, "w", encoding="utf-8") as vf:
                                json.dump(index_data, vf)
                            print(
                                "[HeuristicsDaemon] Successfully injected heuristic into Vector Vault."
                            )
                except Exception as e:
                    print(f"[HeuristicsDaemon] Error processing heuristic line: {e}")

        await asyncio.sleep(5)


def main():
    asyncio.run(tail_and_embed())


if __name__ == "__main__":
    main()
