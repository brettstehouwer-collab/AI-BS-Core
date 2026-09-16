"""
Google Takeout Markdown Compiler.

Parses Google Takeout JSON and HTML files and compiles them into a single,
massive Markdown file (master_takeout_conversations.md) for NotebookLM 
or standard LLM context ingestion.
"""

import os
import json
import glob
import sys
from bs4 import BeautifulSoup
from datetime import datetime

TAKEOUT_DIR = r"C:\AI-BS\Gemini_Takeout_Dataparrent"
OUTPUT_FILE = r"C:\AI-BS\docs\master_takeout_conversations.md"

def parse_html_file(filepath):
    """Fallback parser if Google Takeout provides HTML."""
    conversations = []
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            soup = BeautifulSoup(f, 'html.parser')

        cards = soup.find_all('div', class_='outer-cell')
        if cards:
            for card in cards:
                text = card.get_text(separator='\n', strip=True)
                if len(text) > 50:
                    conversations.append({
                        "content": text,
                        "source": os.path.basename(filepath),
                        "timestamp": "Unknown (HTML)"
                    })
        else:
            text = soup.get_text(separator='\n', strip=True)
            if len(text) > 50:
                conversations.append({
                    "content": text,
                    "source": os.path.basename(filepath),
                    "timestamp": "Unknown (HTML)"
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

        if isinstance(data, list):
            for item in data:
                text_parts = []
                if 'title' in item:
                    text_parts.append(f"**Prompt:** {item['title']}")
                if 'subtitles' in item:
                    for sub in item['subtitles']:
                        if 'name' in sub:
                            text_parts.append(sub['name'])
                if 'details' in item:
                    for det in item['details']:
                        if 'name' in det:
                            text_parts.append(det['name'])

                full_text = "\n\n".join(text_parts)
                if len(full_text) > 50:
                    conversations.append({
                        "content": full_text,
                        "source": os.path.basename(filepath),
                        "timestamp": item.get('time', 'Unknown (JSON)')
                    })
    except (OSError, json.JSONDecodeError) as e:
        print(f"Error parsing JSON {filepath}: {e}")
    return conversations

def main():
    print(f"Starting Gemini Takeout Markdown Compilation from {TAKEOUT_DIR}...")

    if not os.path.exists(TAKEOUT_DIR):
        print(f"Directory {TAKEOUT_DIR} not found. Please extract data here.")
        sys.exit(1)

    all_conversations = []

    json_path = os.path.join(TAKEOUT_DIR, '**', '*.json')
    for jf in glob.glob(json_path, recursive=True):
        all_conversations.extend(parse_json_file(jf))

    html_path = os.path.join(TAKEOUT_DIR, '**', '*.html')
    for hf in glob.glob(html_path, recursive=True):
        all_conversations.extend(parse_html_file(hf))

    if not all_conversations:
        print("No valid conversation data found.")
        sys.exit(0)

    print(f"Found {len(all_conversations)} conversational turns. Writing to {OUTPUT_FILE}...")
    
    os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)
    
    with open(OUTPUT_FILE, "w", encoding="utf-8") as out:
        out.write(f"# Master Takeout Conversations\n\n")
        out.write(f"*Compiled on: {datetime.now().isoformat()}*\n")
        out.write(f"*Total Conversational Turns: {len(all_conversations)}*\n\n")
        out.write("---\n\n")
        
        for idx, conv in enumerate(all_conversations, 1):
            out.write(f"## Conversation Turn {idx}\n")
            out.write(f"**Source:** `{conv['source']}` | **Timestamp:** `{conv['timestamp']}`\n\n")
            out.write(f"{conv['content']}\n\n")
            out.write("---\n\n")
            
    print("Compilation Complete!")

if __name__ == "__main__":
    main()
