import json
import re

TRANSCRIPTS_PATH = r"C:\AI-BS\logs\beta_tester_transcripts.txt"
PERSONA_DATASET_PATH = r"C:\AI-BS\database\Stehouwer_Persona_Dataset.jsonl"

with open(TRANSCRIPTS_PATH, "r", encoding="utf-8", errors="ignore") as f:
    raw = f.read()

# Split by delimiter
blocks = raw.split("================================================================================")
print(f"Total raw transcript blocks: {len(blocks)}")

extracted_pairs = []
for block in blocks:
    if "[CHAT] USER SENT:" in block and "[AI RESPONSE]:" in block:
        try:
            user_part = block.split("[CHAT] USER SENT:")[1].split("[AI RESPONSE]:")[0].strip()
            ai_part = block.split("[AI RESPONSE]:")[1].strip()
            
            # Filter out empty or toxic queries
            if len(user_part) < 3 or len(ai_part) < 3:
                continue
            if "slur" in ai_part.lower() or "cannot provide guidance" in ai_part.lower():
                continue
                
            turn = {
                "messages": [
                    {"role": "user", "content": user_part},
                    {"role": "assistant", "content": ai_part}
                ]
            }
            extracted_pairs.append(turn)
        except Exception:
            pass

print(f"Extracted {len(extracted_pairs)} clean dialogue pairs from Beta Tester Transcripts.")

with open(PERSONA_DATASET_PATH, "a", encoding="utf-8") as f:
    for pair in extracted_pairs[:150]: # Append top 150 clean pairs
        f.write(json.dumps(pair, ensure_ascii=False) + "\n")

with open(PERSONA_DATASET_PATH, "r", encoding="utf-8") as f:
    total_lines = sum(1 for line in f if line.strip())

print(f"[SUCCESS] Stehouwer_Persona_Dataset.jsonl updated to {total_lines} total dialogue pairs!")