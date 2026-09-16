"""
Google Takeout Data Ingestor.

Parses Google Takeout JSON and HTML files and injects conversational text
into the Stehouwer LLM ChromaDB memory vector store.
"""

import os
import json
import glob
import sys
import uuid
from bs4 import BeautifulSoup

from chroma_storage import chroma_manager

TAKEOUT_DIR = r"C:\AI-BS\Gemini_Takeout_Dataparrent"


def parse_html_file(filepath):
    """Fallback parser if Google Takeout provides HTML."""
    conversations = []
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            soup = BeautifulSoup(f, 'html.parser')

        # Structure varies, but usually each chat is in a specific div class
        # This is a generic heuristic parser
        cards = soup.find_all('div', class_='outer-cell')
        if cards:
            for card in cards:
                text = card.get_text(separator='\n', strip=True)
                if len(text) > 50:  # filter out noise
                    conversations.append({
                        "content": text,
                        "source": filepath
                    })
        else:
            # Fallback to reading the entire HTML document text
            text = soup.get_text(separator='\n', strip=True)
            if len(text) > 50:
                conversations.append({
                    "content": text,
                    "source": filepath
                })
    except (OSError, UnicodeDecodeError) as e:
        print(f"Error parsing HTML {filepath}: {e}")
    return conversations


def parse_json_file(filepath):
    """Parser for Google Takeout JSON format."""
    conversations = []
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)

        # JSON structure usually contains an array of interaction events
        if isinstance(data, list):
            for item in data:
                text_parts = []
                if 'title' in item:
                    text_parts.append(f"Prompt: {item['title']}")
                if 'subtitles' in item:
                    for sub in item['subtitles']:
                        if 'name' in sub:
                            text_parts.append(sub['name'])
                if 'details' in item:
                    for det in item['details']:
                        if 'name' in det:
                            text_parts.append(det['name'])

                full_text = "\n".join(text_parts)
                if len(full_text) > 50:
                    conversations.append({
                        "content": full_text,
                        "source": filepath,
                        "timestamp": item.get('time', 'unknown')
                    })
    except (OSError, json.JSONDecodeError) as e:
        print(f"Error parsing JSON {filepath}: {e}")
    return conversations


def main():
    """Main execution block for ingestion."""
    print(f"Starting Gemini Takeout Ingestion from {TAKEOUT_DIR}...")

    if not os.path.exists(TAKEOUT_DIR):
        print(f"Directory {TAKEOUT_DIR} not found. Extract data here.")
        sys.exit(1)

    all_conversations = []

    # Check for JSON files
    json_path = os.path.join(TAKEOUT_DIR, '**', '*.json')
    json_files = glob.glob(json_path, recursive=True)
    for jf in json_files:
        all_conversations.extend(parse_json_file(jf))

    # Check for HTML files
    html_path = os.path.join(TAKEOUT_DIR, '**', '*.html')
    html_files = glob.glob(html_path, recursive=True)
    for hf in html_files:
        all_conversations.extend(parse_html_file(hf))

    if not all_conversations:
        print("No valid conversation data found.")
        sys.exit(0)

    print(
        f"Found {len(all_conversations)} conversational turns. "
        "Preparing for ChromaDB injection..."
    )

    texts = []
    metadatas = []
    ids = []

    for _, conv in enumerate(all_conversations):
        texts.append(conv['content'])
        metadatas.append({
            "source": "google_takeout",
            "file_source": conv['source'],
            "role": "user_history",
            "timestamp": conv.get("timestamp", "unknown")
        })
        ids.append(f"takeout_{uuid.uuid4().hex[:8]}")

    # Batch add to ChromaDB (chunking to prevent overloading)
    batch_size = 10
    total_added = 0
    for i in range(0, len(texts), batch_size):
        batch_texts = texts[i:i+batch_size]
        batch_metas = metadatas[i:i+batch_size]
        batch_ids = ids[i:i+batch_size]

        print(f"Processing batch {i//batch_size + 1}...")
        try:
            chroma_manager.add_communication_styles_batch(
                batch_texts, batch_metas, batch_ids
            )
            total_added += len(batch_texts)
            print(
                f"Injected batch {i//batch_size + 1}... "
                f"({total_added}/{len(texts)})"
            )
        except Exception as e:
            print(f"Failed to inject batch {i//batch_size + 1}: {e}")

    print(
        f"\nIngestion Complete! Successfully embedded {total_added} "
        "conversational turns into the Stehouwer LLM memory."
    )


if __name__ == "__main__":
    main()
