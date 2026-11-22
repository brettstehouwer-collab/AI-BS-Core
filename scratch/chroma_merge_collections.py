#!/usr/bin/env python3
"""
chroma_merge_collections.py
━━━━━━━━━━━━━━━━━━━━━━━━━━
Merge all ChromaDB collections from the .agents/skills vector store
into the canonical root stehouwer_vector_memory store.

This enables maximum learning coverage: the LLM retrieval pipeline can
query both skill-development heuristics AND session context memory from
a single HTTP endpoint served by the chroma_daemon.

Run:
    python chroma_merge_collections.py            # merge + report
    python chroma_merge_collections.py --dry-run  # report only, no writes
    python chroma_merge_collections.py --status   # print collection counts

Safe to run repeatedly — uses upsert so duplicate IDs are overwritten, not doubled.
"""

import argparse
import sys
from pathlib import Path

try:
    import chromadb
except ImportError:
    print("[ERROR] chromadb not installed. Run: pip install chromadb")
    sys.exit(1)

ROOT = Path(__file__).parent.resolve()
SOURCE_PATH = ROOT / ".agents" / "skills" / "stehouwer_vector_memory"
DEST_PATH = ROOT / "stehouwer_vector_memory"


def open_client(path: Path) -> chromadb.PersistentClient:
    if not path.exists():
        print(f"[ERROR] Path not found: {path}")
        sys.exit(1)
    return chromadb.PersistentClient(path=str(path))


def list_collections_summary(client, label: str):
    collections = client.list_collections()
    if not collections:
        print(f"  [{label}] (no collections)")
        return
    for col in collections:
        count = client.get_collection(col.name).count()
        print(f"  [{label}] {col.name}: {count} documents")


def merge(dry_run: bool = False):
    src_client = open_client(SOURCE_PATH)
    dest_client = open_client(DEST_PATH)

    src_collections = src_client.list_collections()
    if not src_collections:
        print("[INFO] Source store has no collections. Nothing to merge.")
        return

    total_merged = 0

    for col_info in src_collections:
        col_name = col_info.name
        src_col = src_client.get_collection(col_name)
        count = src_col.count()

        if count == 0:
            print(f"  SKIP  {col_name} — empty collection")
            continue

        # Fetch ALL documents in batches of 500
        all_ids = []
        all_documents = []
        all_metadatas = []
        all_embeddings = []

        offset = 0
        batch = 500
        while True:
            result = src_col.get(
                limit=batch,
                offset=offset,
                include=["documents", "metadatas", "embeddings"],
            )
            if not result["ids"]:
                break

            # Tag the source so we know where each doc came from
            tagged_meta = []
            for m in result["metadatas"]:
                m = dict(m) if m else {}
                m.setdefault("merged_from", "agents_skills_vector_memory")
                tagged_meta.append(m)

            all_ids += result["ids"]
            all_documents += result["documents"]
            all_metadatas += tagged_meta
            raw_embeds = result.get("embeddings")
            if raw_embeds is None:
                batch_embeds = [None] * len(result["ids"])
            else:
                try:
                    batch_embeds = list(raw_embeds)
                except Exception:
                    batch_embeds = [None] * len(result["ids"])
            all_embeddings += batch_embeds
            offset += batch

        print(
            f"  {
                '[DRY] ' if dry_run else ''}MERGE  {col_name}  ({
                len(all_ids)} docs) -> root store")

        if dry_run:
            total_merged += len(all_ids)
            continue

        # Ensure destination collection exists
        dest_col = dest_client.get_or_create_collection(col_name)

        # Upsert in batches of 100 (ChromaDB HTTP limit)
        for i in range(0, len(all_ids), 100):
            ids = all_ids[i:i + 100]
            docs = all_documents[i:i + 100]
            metas = all_metadatas[i:i + 100]
            embeds = all_embeddings[i:i + 100]
            has_embeds = any(e is not None for e in embeds)

            kwargs = dict(ids=ids, documents=docs, metadatas=metas)
            if has_embeds:
                kwargs["embeddings"] = embeds

            dest_col.upsert(**kwargs)

        total_merged += len(all_ids)
        new_count = dest_col.count()
        print(f"           -> dest '{col_name}' now has {new_count} documents")

    if dry_run:
        print(
            f"\n[DRY RUN] Would have merged {total_merged} documents. No files written.")
    else:
        print(
            f"\n[OK] Merged {total_merged} documents into root vector store.")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Report without writing")
    parser.add_argument(
        "--status",
        action="store_true",
        help="Print collection counts only")
    args = parser.parse_args()

    print(f"\nSource : {SOURCE_PATH}")
    print(f"Dest   : {DEST_PATH}\n")

    src_client = open_client(SOURCE_PATH)
    dest_client = open_client(DEST_PATH)

    print("Current state:")
    list_collections_summary(src_client, "source -> .agents/skills")
    list_collections_summary(dest_client, "dest   -> root store    ")
    print()

    if args.status:
        return

    merge(dry_run=args.dry_run)

    if not args.dry_run:
        print("\nPost-merge state:")
        list_collections_summary(dest_client, "root store")


if __name__ == "__main__":
    main()
