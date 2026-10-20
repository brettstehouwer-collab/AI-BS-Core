import sqlite3
import json
import time
import uuid

VAULT_DB_PATH = r"C:\AI-BS\backend\stehouwer_vault.db"
PERSONA_DATASET_PATH = r"C:\AI-BS\database\Stehouwer_Persona_Dataset.jsonl"
VIDEO_BRIDGE_PATH = r"C:\AI-BS\AI-BS_Modual_Video_Editing\video_gen_engine\comfyui_bridge.py"

conn = sqlite3.connect(VAULT_DB_PATH, timeout=5.0)
conn.execute("PRAGMA journal_mode=WAL;")
conn.execute("PRAGMA synchronous=NORMAL;")
conn.execute("PRAGMA busy_timeout=10000;")

now_ts = time.time()

with open(VIDEO_BRIDGE_PATH, "r", encoding="utf-8", errors="ignore") as f:
    video_text = f.read()

rec_id = f"vault_video_{uuid.uuid4().hex[:8]}"
payload = {
    "cluster": "Master Architecture",
    "source": "AI-BS_Modual_Video_Editing/video_gen_engine/comfyui_bridge.py",
    "title": "Modular AI Video Generation & Automated Scene Segmentation",
    "summary": "Automated pipeline bridging ComfyUI Wan2.1/LTX-Video diffusion models, OpenCV scene detection, object tracking, and Unreal Engine viewport compositing.",
    "body": video_text[:3500]
}
conn.execute(
    "INSERT OR REPLACE INTO vault_data (id, timestamp, source, data) VALUES (?, ?, ?, ?);",
    (rec_id, now_ts, payload["source"], json.dumps(payload))
)

conn.commit()
total_vault = conn.execute("SELECT count(*) FROM vault_data;").fetchone()[0]
conn.close()

new_dialogues = [
    {
        "messages": [
            {"role": "user", "content": "How does the AI-BS modular video editing engine generate and assemble scenes?"},
            {"role": "assistant", "content": "The AI-BS modular video editing engine (AI-BS_Modual_Video_Editing) combines OpenCV scene detection and object tracking with ComfyUI diffusion bridges (Wan2.1 / LTX-Video) and Unreal Engine 5.8 virtual viewports to autonomously composite, color grade, and render multi-shot cinematics."}
        ]
    }
]

with open(PERSONA_DATASET_PATH, "a", encoding="utf-8") as f:
    for d in new_dialogues:
        f.write(json.dumps(d, ensure_ascii=False) + "\n")

with open(PERSONA_DATASET_PATH, "r", encoding="utf-8") as f:
    total_persona = sum(1 for line in f if line.strip())

print(f"[SUCCESS] stehouwer_vault.db updated to {total_vault} total heuristics!")
print(f"[SUCCESS] Stehouwer_Persona_Dataset.jsonl updated to {total_persona} total dialogue pairs!")