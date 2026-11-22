"""
AI-BS Audio Corpus FTS5 Indexing Engine
Extracts acoustic DSP parameters, timbral descriptors, and semantic narrative context
from 101,063 audio assets and builds the memory-mapped SQLite FTS5 virtual table.
"""

import sqlite3
import re
import time
import os

DB_PATHS = [
    r"C:\AI-BS\database\audio_catalog.db",
    r"C:\AIBS\audio_matrix\audio_corpus.db",
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "database", "audio_catalog.db")
]

def resolve_db_path():
    for p in DB_PATHS:
        if os.path.exists(p):
            return os.path.abspath(p)
    return r"C:\AI-BS\database\audio_catalog.db"

def normalize_key(key_str):
    if not key_str:
        return ""
    k = key_str.strip().replace(" ", "")
    k = re.sub(r'([A-G][#b]?)(Min|Maj|m|M)?', lambda m: m.group(1).upper() + (m.group(2).lower() if m.group(2) else ""), k)
    return k

def extract_dsp_semantics(filename, category, bpm, key_raw):
    fn_lower = filename.lower()
    cat_lower = (category or "").lower()
    
    # 1. Normalized category
    norm_cat = "sample"
    if "one-shot" in cat_lower or "one_shot" in cat_lower or "oneshot" in fn_lower:
        norm_cat = "one_shot"
    elif "stem" in cat_lower:
        norm_cat = "stem"
    elif "melody" in cat_lower:
        norm_cat = "melody_loop"
    elif "drum" in cat_lower or "perc" in cat_lower:
        norm_cat = "drum_percussion"
    elif "808" in cat_lower or "bass" in cat_lower:
        norm_cat = "bass_808"
    elif "guitar" in cat_lower:
        norm_cat = "guitar"
    elif "vocal" in cat_lower:
        norm_cat = "vocal"
    elif "fx" in cat_lower or "atmosphere" in cat_lower:
        norm_cat = "foley_fx"
    elif "midi" in cat_lower:
        norm_cat = "midi"

    # Stinger / Drone sub-classification
    if any(w in fn_lower for w in ["stinger", "impact", "hit", "zap", "punch", "strike", "slam"]):
        norm_cat = "stinger"
    elif any(w in fn_lower for w in ["drone", "pad", "atmo", "ambient", "texture", "bed"]):
        norm_cat = "drone"

    # 2. Timbral spectrum
    timbres = []
    if norm_cat in ["drum_percussion", "one_shot", "stinger"]:
        timbres.extend(["percussive", "sharp", "punchy", "transient"])
        if any(w in fn_lower for w in ["metal", "rim", "hihat", "cymbal", "hat", "ride", "crash"]):
            timbres.append("metallic")
        if any(w in fn_lower for w in ["acoustic", "real", "snare", "clap", "wood"]):
            timbres.append("acoustic")
    elif norm_cat in ["bass_808"]:
        timbres.extend(["dark", "sub_heavy", "sustained", "deep", "warm"])
    elif norm_cat in ["melody_loop", "guitar", "vocal"]:
        timbres.extend(["bright", "melodic", "harmonic", "warm"])
        if "guitar" in norm_cat or "acoustic" in fn_lower:
            timbres.append("acoustic")
    elif norm_cat in ["drone", "foley_fx"]:
        timbres.extend(["sustained", "ambient", "atmospheric", "textural"])
        if "dark" in fn_lower or "ominous" in fn_lower:
            timbres.append("dark")
        else:
            timbres.append("bright")

    timbral_spectrum = " ".join(set(timbres))

    # 3. Semantic Context
    semantics = []
    is_minor = "min" in (key_raw or "").lower() or any(w in fn_lower for w in ["min", "dark", "omen", "death", "armed", "war", "fear", "tension", "desolate", "blood", "devil", "shadow", "covert"])
    is_major = "maj" in (key_raw or "").lower() or any(w in fn_lower for w in ["maj", "bright", "sun", "happy", "triumph", "victory", "gold", "summer", "hills", "light", "joy", "peace"])

    if is_minor:
        semantics.extend(["tension", "critical", "suspense", "dark", "action", "intense"])
    if is_major:
        semantics.extend(["triumph", "positive", "euphoric", "calm", "elevated", "uplifting"])
    if norm_cat in ["stinger", "foley_fx"]:
        semantics.extend(["impact", "whoosh", "transition", "reveal"])
    if not semantics:
        semantics.append("neutral_ambient")

    semantic_context = " ".join(set(semantics))

    # 4. Data Bindings
    bindings = []
    if norm_cat in ["stinger", "foley_fx"] or "sharp" in timbres:
        bindings.extend(["metric_drop", "high_variance", "threshold_breach", "anomaly_flag"])
    if "triumph" in semantics or "positive" in semantics or norm_cat == "melody_loop":
        bindings.extend(["metric_gain", "target_met", "positive_trend", "quarterly_growth"])
    if "tension" in semantics or "dark" in semantics or norm_cat == "bass_808":
        bindings.extend(["negative_trend", "risk_elevation", "critical_breach", "volatility"])

    data_bindings = " ".join(set(bindings))

    return norm_cat, str(bpm or ""), normalize_key(key_raw), timbral_spectrum, semantic_context, data_bindings

def build_index():
    db_path = resolve_db_path()
    print(f"Connecting to audio database at: {db_path}")
    
    t0 = time.time()
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA journal_mode = WAL;")
    conn.execute("PRAGMA synchronous = NORMAL;")
    conn.execute("PRAGMA mmap_size = 536870912;")
    conn.execute("PRAGMA cache_size = -64000;")
    
    print("Dropping old audio_corpus_fts virtual table if exists...")
    conn.execute("DROP TABLE IF EXISTS audio_corpus_fts;")
    
    print("Creating audio_corpus_fts virtual table...")
    conn.execute("""
    CREATE VIRTUAL TABLE audio_corpus_fts USING fts5(
        asset_id UNINDEXED,
        file_path UNINDEXED,
        sample_rate UNINDEXED,
        duration_ms UNINDEXED,
        category,
        bpm,
        musical_key,
        timbral_spectrum,
        semantic_context,
        data_bindings,
        tokenize = 'porter unicode61'
    );
    """)

    cur = conn.cursor()
    cur.execute("SELECT id, filename, path, bpm, musical_key, category, size_bytes FROM audio_assets")
    rows = cur.fetchall()
    print(f"Loaded {len(rows)} assets from audio_assets.")

    batch = []
    for r in rows:
        asset_id = str(r[0])
        filename = r[1]
        file_path = r[2]
        bpm = r[3]
        key_raw = r[4]
        category = r[5]
        size_bytes = r[6] or 0

        duration_ms = str(int(size_bytes / 176.4)) if size_bytes > 0 else "0"
        sample_rate = "44100"

        norm_cat, norm_bpm, norm_key, timbre, semantics, bindings = extract_dsp_semantics(filename, category, bpm, key_raw)

        batch.append((
            asset_id,
            file_path,
            sample_rate,
            duration_ms,
            norm_cat,
            norm_bpm,
            norm_key,
            timbre,
            semantics,
            bindings
        ))

    print("Inserting into audio_corpus_fts...")
    conn.executemany("""
    INSERT INTO audio_corpus_fts (
        asset_id, file_path, sample_rate, duration_ms,
        category, bpm, musical_key, timbral_spectrum, semantic_context, data_bindings
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
    """, batch)
    
    conn.commit()
    t1 = time.time()
    print(f"Successfully indexed {len(batch)} records in {t1 - t0:.2f} seconds.")
    conn.close()

if __name__ == '__main__':
    build_index()
