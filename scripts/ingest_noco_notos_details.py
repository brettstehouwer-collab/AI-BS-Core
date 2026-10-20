import sqlite3
import json
import time
import uuid

VAULT_DB_PATH = r"C:\AI-BS\backend\stehouwer_vault.db"
PERSONA_DATASET_PATH = r"C:\AI-BS\database\Stehouwer_Persona_Dataset.jsonl"

conn = sqlite3.connect(VAULT_DB_PATH, timeout=5.0)
conn.execute("PRAGMA journal_mode=WAL;")
conn.execute("PRAGMA synchronous=NORMAL;")
conn.execute("PRAGMA busy_timeout=10000;")

now_ts = time.time()
new_vault_records = []
new_persona_turns = []

# 1. Ingest NoCo Technical Study Guide & Grand Estate Architecture
noco_path = r"C:\AI-BS\extracted_noco_docs.txt"
with open(noco_path, "r", encoding="utf-8", errors="ignore") as f:
    noco_full_text = f.read()

# Chunk into key technical topics
noco_chunks = [
    {
        "cluster": "Eco & Sustainable Systems",
        "source": "extracted_noco_docs.txt",
        "title": "Project NoCo Biomimetic Campus - Bio-Energy & Agricultural Infrastructure",
        "summary": "Full technical breakdown of BPEC, MFC root-zone harvesting, dual-well water management (20 GPM domestic / 50 GPM ag), and 4,000 sq ft NFT/DWC hydroponics greenhouse.",
        "body": noco_full_text[:4000]
    },
    {
        "cluster": "Eco & Sustainable Systems",
        "source": "extracted_noco_docs.txt",
        "title": "Project NoCo Microgrid & Islanded Power Distribution",
        "summary": "Hub-and-spoke electrical distribution with automatic transfer switches, LFP battery storage, and passive cooling via tree evapotranspiration.",
        "body": noco_full_text[4000:8000]
    }
]

for c in noco_chunks:
    rec_id = f"vault_noco_{uuid.uuid4().hex[:8]}"
    conn.execute(
        "INSERT OR REPLACE INTO vault_data (id, timestamp, source, data) VALUES (?, ?, ?, ?);",
        (rec_id, now_ts, c["source"], json.dumps(c))
    )

new_persona_turns.extend([
    {
        "messages": [
            {"role": "user", "content": "What are the primary bio-energy generation technologies specified for the Project NoCo venue?"},
            {"role": "assistant", "content": "Project NoCo utilizes three primary bio-energy technologies:\n1. Bio-Photoelectrochemical cells (BPEC): Intercepting electrons directly from photosynthesis.\n2. Microbial Fuel Cells (MFC): Heterotrophic bacteria in root zones releasing electrons to anodes.\n3. Piezoelectric Harvesters: Converting mechanical movement (plant sway from wind) into electricity."}
        ]
    },
    {
        "messages": [
            {"role": "user", "content": "How is water infrastructure partitioned between domestic and agricultural demands at the NoCo Biomimetic Campus?"},
            {"role": "assistant", "content": "Water is managed via dual redundant wells:\n- Domestic Well: 20 GPM for the Main House and artist residences, feeding a 5,000-gallon buried cistern.\n- Agricultural Well: 50 GPM for hydroponics and livestock, feeding a 10,000-gallon dual-section cistern (heated/unheated)."}
        ]
    }
])

# 2. Ingest Noto Enterprise Hospitality Architecture
noto_impl_path = r"C:\AI-BS\Notos implication.txt"
with open(noto_impl_path, "r", encoding="utf-8", errors="ignore") as f:
    noto_impl_text = f.read()

noto_rec = {
    "cluster": "Business & Hospitality",
    "source": "Notos implication.txt",
    "title": "Noto's Enterprise OS - Dual-Location Hospitality Architecture (GR & GH)",
    "summary": "Complete technical architecture for Joanne's 12,000-bottle wine cellar, Valentina's live BEO banquet engine, Tom's kitchen 86'd board, and Grand Haven Bil-Mar operations.",
    "body": noto_impl_text[:3500]
}

conn.execute(
    "INSERT OR REPLACE INTO vault_data (id, timestamp, source, data) VALUES (?, ?, ?, ?);",
    (f"vault_notos_{uuid.uuid4().hex[:8]}", now_ts, noto_rec["source"], json.dumps(noto_rec))
)

new_persona_turns.extend([
    {
        "messages": [
            {"role": "user", "content": "Explain the dual-location architecture of Noto's Enterprise OS."},
            {"role": "assistant", "content": "Noto's Enterprise OS bridges two premier locations:\n1. Grand Rapids (28th St): Focuses on the 12,000-bottle Wine Cellar Master, the 700-capacity Grand Ballroom BEO engine, and fine dining.\n2. Grand Haven (At the Bil-Mar): Focuses on lakeshore sunset dining, wood-fired pizza expo, outdoor bocce courts, and La Grande Vista event decks.\nBoth locations share synchronized shift logs, kitchen 86'd boards, and real-time inventory tracking."}
        ]
    }
])

conn.commit()
total_vault = conn.execute("SELECT count(*) FROM vault_data;").fetchone()[0]
conn.close()

with open(PERSONA_DATASET_PATH, "a", encoding="utf-8") as f:
    for turn in new_persona_turns:
        f.write(json.dumps(turn, ensure_ascii=False) + "\n")

with open(PERSONA_DATASET_PATH, "r", encoding="utf-8") as f:
    total_persona = sum(1 for line in f if line.strip())

print(f"[SUCCESS] stehouwer_vault.db updated to {total_vault} total heuristics!")
print(f"[SUCCESS] Stehouwer_Persona_Dataset.jsonl updated to {total_persona} total dialogue pairs!")