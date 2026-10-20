import json

with open(r'c:\AI-BS\saved_data\recdebut_extracted_summary.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

with open(r'c:\AI-BS\saved_data\clean_extracted_text.txt', 'w', encoding='utf-8') as out:
    for url, p in data.items():
        out.write(f"\n========================================\n")
        out.write(f"PAGE: {p['title']}\nURL: {url}\n")
        out.write(f"IMAGES: {json.dumps(p['images'])}\n")
        out.write(f"LINKS: {json.dumps(p['links'])}\n")
        out.write(f"CONTENT:\n{p['content']}\n")

print("Wrote clean_extracted_text.txt successfully!")
