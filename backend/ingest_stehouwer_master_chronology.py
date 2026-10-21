import os
import sys
sys.stdout.reconfigure(encoding='utf-8')
import re
import sqlite3
import chromadb

CHRONO_MD = "C:/AI-BS/STEHOUWER_OMNI_CHRONOLOGICAL_MASTER_ARCHIVE.md"
LEDGER_MD = "C:/AI-BS/AI_BS_MASTER_ARCHITECTURAL_LEDGER.md"
DB_PATH = "C:/AI-BS/database/stehouwer_chronology.db"
LOCAL_CHROMA = "C:/AI-BS/database/ChromaDB_local"
E_CHROMA = "E:/AI_BS_Resources/ChromaDB"

os.makedirs("C:/AI-BS/database", exist_ok=True)
os.makedirs(LOCAL_CHROMA, exist_ok=True)

with open(CHRONO_MD, "r", encoding="utf-8", errors="ignore") as f:
    text = f.read()

with open(LEDGER_MD, "r", encoding="utf-8", errors="ignore") as f:
    ledger_top = "\n".join(f.readlines()[:40])

combined_text = ledger_top + "\n\n" + text

sections = re.split(r'\n(?=## |### |\| \d{4}-\d{2}-\d{2} \|)', combined_text)
parsed_records = []

for sec in sections:
    sec = sec.strip()
    if not sec:
        continue
    date_match = re.search(r'(\d{4}-\d{2}-\d{2})', sec)
    date_str = date_match.group(1) if date_match else "2026-08-31"
    ver_match = re.search(r'\[?(v?\d+\.\d+(?:\.\d+)?)\]?', sec)
    ver_str = ver_match.group(1) if ver_match else "General"
    if not ver_str.startswith("v") and ver_str[0].isdigit():
        ver_str = "v" + ver_str
    first_line = sec.split("\n")[0].replace("#", "").replace("|", " ").strip()
    title_str = first_line[:140]
    era_str = "Era 8: Sovereign Native Studio & RecDebut Synthesis (Oct 2026)" if "2026-10" in date_str else "Ecosystem Evolution"
    parsed_records.append({
        "era": era_str,
        "date": date_str,
        "version": ver_str,
        "title": title_str,
        "content": sec[:4000]
    })

parsed_records.sort(key=lambda r: r["date"], reverse=True)

conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()
cursor.execute("DROP TABLE IF EXISTS chronology_fts;")
cursor.execute("DROP TABLE IF EXISTS chronology_meta;")
cursor.execute("""
CREATE VIRTUAL TABLE chronology_fts USING fts5(
    era, date, version, title, content, tokenize='porter unicode61'
);
""")
cursor.execute("""
CREATE TABLE chronology_meta (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    era TEXT, date TEXT, version TEXT, title TEXT, content TEXT
);
""")

for r in parsed_records:
    cursor.execute("INSERT INTO chronology_fts (era, date, version, title, content) VALUES (?, ?, ?, ?, ?);",
                   (r["era"], r["date"], r["version"], r["title"], r["content"]))
    cursor.execute("INSERT INTO chronology_meta (era, date, version, title, content) VALUES (?, ?, ?, ?, ?);",
                   (r["era"], r["date"], r["version"], r["title"], r["content"]))

conn.commit()
conn.close()
print(f"SQLite FTS5 database written to {DB_PATH} ({len(parsed_records)} records, newest: {parsed_records[0]['date']} {parsed_records[0]['version']}).")
