import json

with open(r"C:\AI-BS\saved_data\facebook_reel_transcription.json", "r", encoding="utf-8") as f:
    data = json.load(f)

print(f"Total segments: {len(data['segments'])}")
for idx, s in enumerate(data['segments']):
    print(f"[{idx}] {s['start']:.2f}s -> {s['end']:.2f}s: {s['text']}")
    if 'words' in s and s['words']:
        w_sample = " | ".join([f"{w['word']}({w['start']:.2f}-{w['end']:.2f})" for w in s['words'][:6]])
        print(f"    Words ({len(s['words'])}): {w_sample}...")
