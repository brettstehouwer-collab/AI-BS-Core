import json
import glob
import os

sample_files = glob.glob(r'C:\Users\footb\.gemini\antigravity-ide\brain\*\.system_generated\logs\transcript.jsonl')
print(f"Total transcript.jsonl files found: {len(sample_files)}")
if sample_files:
    print("Sample path:", sample_files[0])
    with open(sample_files[0], 'r', encoding='utf-8') as f:
        for i, line in enumerate(f):
            if i >= 5:
                break
            data = json.loads(line)
            print(f"Line {i} keys:", list(data.keys()))
            if data.get('type') == 'USER_INPUT':
                print(f"Line {i} content snippet:", str(data.get('content'))[:100])
