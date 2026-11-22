import json
import urllib.request
import time

output_file = r"c:\AI-BS\Matthew.md"
print("Starting download of the complete Book of Matthew...")

chapters_data = {}

for ch in range(1, 29):
    print(f"Fetching Chapter {ch}/28...")
    success = False
    attempts = 0
    while not success:
        attempts += 1
        try:
            url = f"https://bible-api.com/matthew+{ch}?translation=kjv"
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
    f.write("# The Gospel According to Saint Matthew (KJV)\n\n")
    for ch in range(1, 29):
        f.write(f"## Chapter {ch}\n\n")
        for v in chapters_data.get(ch, []):
            text = v.get("text", "").strip()
            verse_num = v.get("verse", "")
            f.write(f"**{verse_num}** {text}\n\n")

print(f"Complete! All 28 chapters saved cleanly to {output_file}")
