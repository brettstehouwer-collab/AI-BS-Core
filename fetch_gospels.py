import json
import urllib.request
import time
import os

books = [
    {"name": "Mark", "title": "The Gospel According to Saint Mark (KJV)", "chapters": 16, "file": r"c:\AI-BS\Mark.md"},
    {"name": "Luke", "title": "The Gospel According to Saint Luke (KJV)", "chapters": 24, "file": r"c:\AI-BS\Luke.md"},
    {"name": "John", "title": "The Gospel According to Saint John (KJV)", "chapters": 21, "file": r"c:\AI-BS\John.md"},
]

for book in books:
    b_name = book["name"]
    total_ch = book["chapters"]
    output_file = book["file"]
    print(f"\n==========================================")
    print(f"Starting download of {b_name} ({total_ch} chapters)...")
    print(f"==========================================")
    
    chapters_data = {}
    for ch in range(1, total_ch + 1):
        print(f"Fetching {b_name} Chapter {ch}/{total_ch}...")
        success = False
        attempts = 0
        while not success:
            attempts += 1
            try:
                url = f"https://bible-api.com/{b_name.lower()}+{ch}?translation=kjv"
                req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"})
                with urllib.request.urlopen(req) as resp:
                    data = json.loads(resp.read().decode("utf-8"))
                
                chapters_data[ch] = data.get("verses", [])
                success = True
                time.sleep(1.2)
            except Exception as e:
                wait_sec = min(attempts * 2, 10)
                print(f"  Rate limited / error ({e}), retrying in {wait_sec}s (attempt {attempts})...")
                time.sleep(wait_sec)

    with open(output_file, "w", encoding="utf-8") as f:
        f.write(f"# {book['title']}\n\n")
        for ch in range(1, total_ch + 1):
            f.write(f"## Chapter {ch}\n\n")
            for v in chapters_data.get(ch, []):
                text = v.get("text", "").strip()
                verse_num = v.get("verse", "")
                f.write(f"**{verse_num}** {text}\n\n")

    print(f"Saved {b_name} successfully to {output_file}")

print("\nAll books (Mark, Luke, John) successfully downloaded and saved!")
