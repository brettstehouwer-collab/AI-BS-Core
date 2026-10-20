import os
import re
import json
import time
import uuid
import sqlite3

VAULT_DB_PATH = r"C:\AI-BS\backend\stehouwer_vault.db"
PERSONA_DATASET_PATH = r"C:\AI-BS\database\Stehouwer_Persona_Dataset.jsonl"
DOCS_DIR = r"C:\AI-BS\docs"

print("=" * 70)
print("     STEHOUWER LLM MULTIMODAL CORPUS & VAULT INGESTOR (v5.86.0)")
print("=" * 70)

# Connect to stehouwer_vault.db under WAL mode
conn = sqlite3.connect(VAULT_DB_PATH, timeout=5.0)
conn.execute("PRAGMA journal_mode=WAL;")
conn.execute("PRAGMA synchronous=NORMAL;")
conn.execute("PRAGMA busy_timeout=10000;")
conn.execute("""
    CREATE TABLE IF NOT EXISTS vault_data (
        id TEXT PRIMARY KEY,
        timestamp REAL,
        source TEXT,
        data TEXT
    );
""")

vault_entries = []
new_persona_dialogues = []

def read_text_file(filename):
    path = os.path.join(DOCS_DIR, filename)
    if not os.path.exists(path):
        return ""
    for enc in ["utf-8", "utf-8-sig", "latin1", "cp1252"]:
        try:
            with open(path, "r", encoding=enc) as f:
                return f.read()
        except Exception:
            pass
    return ""

# =========================================================================
# CLUSTER 1: AUTHENTIC PERSONA, HUMOR & BROTHERLY BANTER
# =========================================================================
print("[Cluster 1/6] Processing Authentic Persona & Humor...")
chat_text = read_text_file("WhatsApp Chat with Sean My Brother Who Never Leaves.md")
if not chat_text:
    chat_text = read_text_file("brother sean and i humore and reason..md")

if chat_text:
    # Extract timestamps and message exchanges: [date, time] Name: message
    lines = chat_text.splitlines()
    current_sender = None
    current_msg = []
    exchanges = []
    
    pattern = re.compile(r"^\[?(\d{1,2}[/-]\d{1,2}[/-]\d{2,4},?\s*\d{1,2}:\d{2}(?::\d{2})?\s*(?:AM|PM|am|pm)?)\]?\s*([^:]+):\s*(.*)$")
    
    for line in lines:
        match = pattern.match(line)
        if match:
            if current_sender and current_msg:
                exchanges.append((current_sender.strip(), "\n".join(current_msg).strip()))
            current_sender = match.group(2)
            current_msg = [match.group(3)]
        else:
            if current_sender:
                current_msg.append(line)
                
    if current_sender and current_msg:
        exchanges.append((current_sender.strip(), "\n".join(current_msg).strip()))

    # Build dialogue turns
    for i in range(len(exchanges) - 1):
        s1, m1 = exchanges[i]
        s2, m2 = exchanges[i+1]
        
        # Filter out empty messages, attachments, media omissions
        if "<Media omitted>" in m1 or "<Media omitted>" in m2 or not m1 or not m2:
            continue
        if len(m1) < 2 or len(m2) < 2:
            continue
            
        if "sean" in s1.lower() or "stehouwer" in s2.lower() or "adam" in s2.lower() or "brett" in s2.lower() or s1 != s2:
            turn = {
                "messages": [
                    {"role": "user", "content": m1},
                    {"role": "assistant", "content": m2}
                ]
            }
            new_persona_dialogues.append(turn)

    vault_entries.append({
        "cluster": "Authentic Persona & Humor",
        "source": "WhatsApp_Chat_Sean_Stehouwer",
        "title": "Family Dynamics, Spontaneous Humor & Brotherly Banter",
        "content_length": len(chat_text),
        "dialogue_turns_extracted": len(exchanges),
        "summary": "Full raw conversational dynamics, inside humor, work-life balancing, and spontaneous voice."
    })
    print(f"  -> Extracted {len(new_persona_dialogues)} dialogue pairs from Brother Sean chat.")

# =========================================================================
# CLUSTER 2: BUSINESS STRATEGIES & HOSPITALITY CONCEPTS (NOTO / BANQUETS)
# =========================================================================
print("[Cluster 2/6] Processing Business Strategies & Hospitality Concepts...")
noto_pitch = read_text_file("AI_BS_Tony_Noto_Pitch_Deck.md")
noto_ideas = read_text_file("tony noto ideas..md")

noto_combined = noto_pitch + "\n\n" + noto_ideas
if noto_combined.strip():
    # Chunk by markdown headers
    sections = re.split(r"\n(?=##?\s+)", noto_combined)
    for sec in sections:
        if len(sec.strip()) < 50:
            continue
        lines = sec.strip().splitlines()
        header = lines[0].replace("#", "").strip()
        body = "\n".join(lines[1:]).strip()
        
        vault_entries.append({
            "cluster": "Business & Hospitality",
            "source": "AI_BS_Tony_Noto_Pitch_Deck",
            "title": f"Noto Hospitality & Banquets - {header}",
            "body": body,
            "summary": f"Strategic planning, dining room automation, wine cellar management, and banquet operations for {header}."
        })
        
        # Add instructional Q&A to persona dataset
        new_persona_dialogues.append({
            "messages": [
                {"role": "user", "content": f"What is our operational vision and execution plan for {header} at Noto's?"},
                {"role": "assistant", "content": f"Here is the strategic framework for {header}:\n\n{body}"}
            ]
        })
    print(f"  -> Extracted {len(sections)} strategic business modules for Noto's.")

# =========================================================================
# CLUSTER 3: ECO-VENUE, SUSTAINABILITY & AGRICULTURAL ENGINEERING (NOCO)
# =========================================================================
print("[Cluster 3/6] Processing Eco-Venue & Sustainable Engineering...")
noco_ideas = read_text_file("NoCo Ideas.md")
noco_rf = read_text_file("Nocorf1.md")
ferm_text = read_text_file("fermentation-06-00092-v2.md")

noco_corpus = noco_ideas + "\n\n" + noco_rf + "\n\n" + ferm_text
if noco_corpus.strip():
    sections = re.split(r"\n(?=##?\s+)", noco_corpus)
    for sec in sections:
        if len(sec.strip()) < 60:
            continue
        lines = sec.strip().splitlines()
        header = lines[0].replace("#", "").strip()
        body = "\n".join(lines[1:]).strip()
        
        vault_entries.append({
            "cluster": "Eco & Sustainable Systems",
            "source": "Project_NoCo_Sustainable_Ecosystem",
            "title": f"NoCo Circular Eco-Venue - {header}",
            "body": body,
            "summary": f"Technical specs on circular bio-energy, microgrid design, greenhouse automation, and smart event venues."
        })
        
        new_persona_dialogues.append({
            "messages": [
                {"role": "user", "content": f"How do we integrate and scale {header} in the Project NoCo ecosystem?"},
                {"role": "assistant", "content": f"For {header}, the architectural and technical breakdown is as follows:\n\n{body}"}
            ]
        })
    print(f"  -> Extracted {len(sections)} NoCo sustainable engineering modules.")

# =========================================================================
# CLUSTER 4: SCREENWRITING & CREATIVE NARRATIVE (JULIE STEHOUWER / BUD)
# =========================================================================
print("[Cluster 4/6] Processing Screenwriting & Creative Narratives...")
julie_text = read_text_file("Officeal start of_ The Bad Side Upside Down Writen By_ Julie Stehouwer 2525 (2).md")
bud_text = read_text_file("BUDMD.md")

creative_corpus = julie_text + "\n\n" + bud_text
if creative_corpus.strip():
    sections = re.split(r"\n(?=##?\s+|SCENE\s+\d+|ACT\s+[I|V|X]+)", creative_corpus)
    for i, sec in enumerate(sections):
        if len(sec.strip()) < 80:
            continue
        lines = sec.strip().splitlines()
        header = lines[0].replace("#", "").strip() if lines else f"Scene Treatment {i+1}"
        body = "\n".join(lines[1:]).strip() if len(lines) > 1 else lines[0]
        
        vault_entries.append({
            "cluster": "Screenwriting & Creative",
            "source": "The_Bad_Side_Upside_Down_Julie_Stehouwer",
            "title": f"Narrative Script - {header[:60]}",
            "body": body[:2000],
            "summary": "Creative screenwriting, dialogue pacing, thematic character voice, and worldbuilding."
        })
        
        new_persona_dialogues.append({
            "messages": [
                {"role": "user", "content": f"Write a scene treatment or dialogue progression exploring: {header[:80]}"},
                {"role": "assistant", "content": f"{body[:1500]}"}
            ]
        })
    print(f"  -> Extracted {len(sections)} screenwriting & narrative treatments.")

# =========================================================================
# CLUSTER 5: MASTER SYSTEM ARCHITECTURE & OPERATIONAL LEDGERS
# =========================================================================
print("[Cluster 5/6] Processing Master System Architecture & Directives...")
manual_text = read_text_file("AI_BS_MASTER_ECOSYSTEM_MANUAL.md")
skills_text = read_text_file("AI-BS_Master_Skill_Ledger.md")
audit_text = read_text_file("AI_BS_MASTER_SYSTEM_AUDIT_DIRECTIVE.md")

arch_corpus = manual_text + "\n\n" + skills_text + "\n\n" + audit_text
if arch_corpus.strip():
    sections = re.split(r"\n(?=##?\s+)", arch_corpus)
    for sec in sections:
        if len(sec.strip()) < 60:
            continue
        lines = sec.strip().splitlines()
        header = lines[0].replace("#", "").strip()
        body = "\n".join(lines[1:]).strip()
        
        vault_entries.append({
            "cluster": "Master Architecture",
            "source": "AI_BS_Master_Architecture_Ledger",
            "title": f"System Architecture - {header}",
            "body": body,
            "summary": f"Hardware topologies, VRAM arbitration, port definitions, and daemon orchestrations for {header}."
        })
        
        new_persona_dialogues.append({
            "messages": [
                {"role": "user", "content": f"Explain the architectural design and rules for {header} in AI-BS Matrix."},
                {"role": "assistant", "content": f"AI-BS Architectural Standard for {header}:\n\n{body}"}
            ]
        })
    print(f"  -> Extracted {len(sections)} core system architecture modules.")

# =========================================================================
# CLUSTER 6: HISTORICAL REASONING & CONVERSATIONAL MEMORY
# =========================================================================
print("[Cluster 6/6] Processing Historical Reasoning & Conversational Memory...")
takeout_text = read_text_file("master_takeout_conversations.md")
aug_text = read_text_file("aug410.md")
combined_text = read_text_file("Batch_Final_21_Files_Combined.md")

hist_corpus = takeout_text + "\n\n" + aug_text + "\n\n" + combined_text
if hist_corpus.strip():
    sections = re.split(r"\n(?=##?\s+|===+\s+)", hist_corpus)
    for i, sec in enumerate(sections[:150]):
        if len(sec.strip()) < 70:
            continue
        lines = sec.strip().splitlines()
        header = lines[0].replace("#", "").replace("=", "").strip() or f"Reasoning Trace {i+1}"
        body = "\n".join(lines[1:]).strip()
        
        vault_entries.append({
            "cluster": "Historical Reasoning",
            "source": "Google_Takeout_Historical_Conversations",
            "title": f"Reasoning & Evolution - {header[:60]}",
            "body": body[:2000],
            "summary": "Historical debugging logs, technical iterations, and cognitive problem-solving traces."
        })
        
        new_persona_dialogues.append({
            "messages": [
                {"role": "user", "content": f"How did we solve or design the requirements for {header[:70]}?"},
                {"role": "assistant", "content": f"Technical reasoning trace for {header[:70]}:\n\n{body[:1200]}"}
            ]
        })
    print(f"  -> Extracted {min(len(sections), 150)} historical reasoning traces.")

# =========================================================================
# COMMIT TO STEHOUWER_VAULT.DB
# =========================================================================
print("\n" + "=" * 70)
print(f"Writing {len(vault_entries)} Structured Heuristics to stehouwer_vault.db...")
now_ts = time.time()
for entry in vault_entries:
    entry_id = f"vault_{entry['cluster'][:4].lower()}_{uuid.uuid4().hex[:8]}"
    json_data = json.dumps(entry)
    conn.execute(
        "INSERT OR REPLACE INTO vault_data (id, timestamp, source, data) VALUES (?, ?, ?, ?);",
        (entry_id, now_ts, entry["source"], json_data)
    )

conn.commit()
v_count = conn.execute("SELECT count(*) FROM vault_data;").fetchone()[0]
conn.close()
print(f"[SUCCESS] stehouwer_vault.db now contains {v_count} active vaulted knowledge records!")

# =========================================================================
# APPEND TO STEHOUWER_PERSONA_DATASET.JSONL
# =========================================================================
print(f"\nAppending {len(new_persona_dialogues)} new training dialogue pairs to Stehouwer_Persona_Dataset.jsonl...")
with open(PERSONA_DATASET_PATH, "a", encoding="utf-8") as f:
    for dialogue in new_persona_dialogues:
        f.write(json.dumps(dialogue, ensure_ascii=False) + "\n")

with open(PERSONA_DATASET_PATH, "r", encoding="utf-8") as f:
    total_lines = sum(1 for line in f if line.strip())

print(f"[SUCCESS] Stehouwer_Persona_Dataset.jsonl expanded to {total_lines} total fine-tuning pairs!")
print("=" * 70)