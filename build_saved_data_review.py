#!/usr/bin/env python3
"""AI-BS Sovereign Ecosystem: Saved Data Vault Review Compiler.

Consolidates all 104 operational data, telemetry, recruiting, genomics,
and script files from C:\\AI-BS\\saved_data\\ into a master Markdown dossier:
C:\\Users\\footb\\OneDrive\\Desktop\\CONSOLIDATED_SAVED_DATA_REVIEW.md
"""

from __future__ import annotations

import os
import sys
import time
import hashlib
import json
import sqlite3
from pathlib import Path
from typing import Dict, List, Tuple

OUTPUT_FILE = r"C:\Users\footb\OneDrive\Desktop\CONSOLIDATED_SAVED_DATA_REVIEW.md"

ALL_SAVED_FILES = [
    # Batch 1 (80 files)
    r"C:\AI-BS\saved_data\trials_test.json",
    r"C:\AI-BS\saved_data\facebook_reel_karaoke.ass",
    r"C:\AI-BS\saved_data\pendulum_audio_for_vid_9x16.ass",
    r"C:\AI-BS\saved_data\pendulum_audio_for_vid_16x9.ass",
    r"C:\AI-BS\saved_data\pendulum_karaoke.ass",
    r"C:\AI-BS\saved_data\pendulum_karaoke_16x9.ass",
    r"C:\AI-BS\saved_data\CLAIM_DASHBOARD.html",
    r"C:\AI-BS\saved_data\MyPhoneContacts.csv",
    r"C:\AI-BS\saved_data\public_prospects_2027_2030.csv",
    r"C:\AI-BS\saved_data\rec_debut_athlete_emails_master.csv",
    r"C:\AI-BS\saved_data\recdebut_email_verification_report.csv",
    r"C:\AI-BS\saved_data\sample_scouted_roster.csv",
    r"C:\AI-BS\saved_data\agent_harness_sessions.db",
    r"C:\AI-BS\saved_data\air_sensor_telemetry.db",
    r"C:\AI-BS\saved_data\chef_orders.db",
    r"C:\AI-BS\saved_data\episodic_graph.db",
    r"C:\AI-BS\saved_data\rec_debut.db",
    r"C:\AI-BS\saved_data\recdebut_athletes.db",
    r"C:\AI-BS\saved_data\site_analytics.db",
    r"C:\AI-BS\saved_data\stehouwer_vault.db",
    r"C:\AI-BS\saved_data\crypto_trader_bot.err",
    r"C:\AI-BS\saved_data\aibs_email_router_worker.js",
    r"C:\AI-BS\saved_data\nvme_frame_01.jpg",
    r"C:\AI-BS\saved_data\nvme_frame_02.jpg",
    r"C:\AI-BS\saved_data\nvme_frame_03.jpg",
    r"C:\AI-BS\saved_data\nvme_frame_04.jpg",
    r"C:\AI-BS\saved_data\nvme_frame_05.jpg",
    r"C:\AI-BS\saved_data\nvme_frame_06.jpg",
    r"C:\AI-BS\saved_data\pendulum_static_artwork.jpg",
    r"C:\AI-BS\saved_data\test_frame.jpg",
    r"C:\AI-BS\saved_data\audio_assets_manifest.json",
    r"C:\AI-BS\saved_data\audio_for_vid_transcription.json",
    r"C:\AI-BS\saved_data\bible_study_notes.json",
    r"C:\AI-BS\saved_data\clinical_nutrition_payload.json",
    r"C:\AI-BS\saved_data\clinvar_search_CFTR.json",
    r"C:\AI-BS\saved_data\clinvar_summary_CFTR.json",
    r"C:\AI-BS\saved_data\clinvar_summary_test.json",
    r"C:\AI-BS\saved_data\clinvar_test.json",
    r"C:\AI-BS\saved_data\codebase_knowledge_index.json",
    r"C:\AI-BS\saved_data\cymatics_12_assets_sweep.json",
    r"C:\AI-BS\saved_data\cymatics_cards_inspection.json",
    r"C:\AI-BS\saved_data\cymatics_cross_check_matrix.json",
    r"C:\AI-BS\saved_data\cymatics_discovered_free_drops.json",
    r"C:\AI-BS\saved_data\cymatics_drop_log.json",
    r"C:\AI-BS\saved_data\cymatics_full_dom_json_extraction.json",
    r"C:\AI-BS\saved_data\cymatics_heartbeat.json",
    r"C:\AI-BS\saved_data\cymatics_locked_cards_live.json",
    r"C:\AI-BS\saved_data\cymatics_unowned_free_drops.json",
    r"C:\AI-BS\saved_data\dbsnp_rs699.json",
    r"C:\AI-BS\saved_data\dbsnp_rs1801133.json",
    r"C:\AI-BS\saved_data\digital_twin_state.json",
    r"C:\AI-BS\saved_data\drop_page_all_cards_audit.json",
    r"C:\AI-BS\saved_data\drop_watcher_state.json",
    r"C:\AI-BS\saved_data\encode_EH38E2941922.json",
    r"C:\AI-BS\saved_data\encode_test.json",
    r"C:\AI-BS\saved_data\facebook_group_videos_Bstehouwer_2026-07-21T21-27-08-544Z.json",
    r"C:\AI-BS\saved_data\facebook_group_videos_videos_2026-07-21T21-23-21-271Z.json",
    r"C:\AI-BS\saved_data\facebook_reel_transcription.json",
    r"C:\AI-BS\saved_data\facebook_user_search_Bstehouwer_2026-07-21T21-27-20-845Z.json",
    r"C:\AI-BS\saved_data\facebook_user_search_reels_2026-07-21T21-27-31-077Z.json",
    r"C:\AI-BS\saved_data\live_engagement_dump.json",
    r"C:\AI-BS\saved_data\marketing_campaigns.json",
    r"C:\AI-BS\saved_data\master_calendar_events.json",
    r"C:\AI-BS\saved_data\NEW_DROP_ALERT.json",
    r"C:\AI-BS\saved_data\pdb_test.json",
    r"C:\AI-BS\saved_data\rec_debut_athlete_emails.json",
    r"C:\AI-BS\saved_data\rec_debut_scheduler_state.json",
    r"C:\AI-BS\saved_data\rec_debut_smtp_swarm.json",
    r"C:\AI-BS\saved_data\recdebut_extracted_summary.json",
    r"C:\AI-BS\saved_data\recdebut_site_data.json",
    r"C:\AI-BS\saved_data\release_test_audit.json",
    r"C:\AI-BS\saved_data\release_test_pytest.json",
    r"C:\AI-BS\saved_data\release_test_shortcuts.json",
    r"C:\AI-BS\saved_data\release_test_sync.json",
    r"C:\AI-BS\saved_data\rs699.json",
    r"C:\AI-BS\saved_data\stehouwer_publishing_marketing_campaigns.json",
    r"C:\AI-BS\saved_data\stream_chat_telemetry_ping.json",
    r"C:\AI-BS\saved_data\subsecond_heartbeat.json",
    r"C:\AI-BS\saved_data\trials_Glioblastoma.json",
    r"C:\AI-BS\saved_data\trials_Melanoma.json",
    # Batch 2 (24 files)
    r"C:\AI-BS\saved_data\build_rich_site_data.py",
    r"C:\AI-BS\saved_data\check_campaigns_deep.py",
    r"C:\AI-BS\saved_data\check_dispatch.py",
    r"C:\AI-BS\saved_data\check_real_quota.py",
    r"C:\AI-BS\saved_data\check_swarm_status.py",
    r"C:\AI-BS\saved_data\check_timeline.py",
    r"C:\AI-BS\saved_data\check_today_dispatch.py",
    r"C:\AI-BS\saved_data\get_live_engagement.py",
    r"C:\AI-BS\saved_data\inject_recdebut_hub.py",
    r"C:\AI-BS\saved_data\inspect_12_pending.py",
    r"C:\AI-BS\saved_data\test_adam_live.py",
    r"C:\AI-BS\saved_data\test_adam_mms.py",
    r"C:\AI-BS\saved_data\test_replacements.py",
    r"C:\AI-BS\saved_data\update_delivery_notes.py",
    r"C:\AI-BS\saved_data\verify_rec_debut_features.py",
    r"C:\AI-BS\saved_data\clean_extracted_text.txt",
    r"C:\AI-BS\saved_data\cloud_tunnel.log",
    r"C:\AI-BS\saved_data\cloud_tunnel_url.txt",
    r"C:\AI-BS\saved_data\crypto_trader_bot.log",
    r"C:\AI-BS\saved_data\cymatics_subsecond_drops.log",
    r"C:\AI-BS\saved_data\cymatics_watchdog.log",
    r"C:\AI-BS\saved_data\rec_debut_athlete_emails_clean_list.txt",
    r"C:\AI-BS\saved_data\rec_debut_athlete_emails_with_names.txt",
    r"C:\AI-BS\saved_data\rec_debut_daily_scheduler.log",
]


def hash_file(filepath: str) -> str:
    try:
        h = hashlib.sha256()
        with open(filepath, "rb") as f:
            while chunk := f.read(65536):
                h.update(chunk)
        return h.hexdigest()
    except Exception as e:
        return f"ERR: {e}"


def categorize(filename: str) -> str:
    lower = filename.lower()
    ext = os.path.splitext(lower)[1]

    if ext == ".py":
        return "01. Python Automation & Dispatch Scripts"
    if ext == ".db":
        return "07. SQLite Database Schemas & Record Dumps"
    if ext == ".jpg":
        return "09. Visual Frames & Graphic Assets"
    if "rec_debut" in lower or "recdebut" in lower or "prospect" in lower or "roster" in lower or "myphone" in lower:
        return "02. RecDebut Sports & College Recruiting Matrices"
    if "clinvar" in lower or "dbsnp" in lower or "encode" in lower or "pdb" in lower or "trials" in lower or lower.startswith("rs699"):
        return "03. Sovereign Bio-AI & Scientific Genomics Ledgers"
    if "cymatics" in lower or "drop" in lower:
        return "04. Cymatics Audio Drops & Asset Monitors"
    if ext == ".ass" or "facebook" in lower or "transcription" in lower or "karaoke" in lower:
        return "05. Media Transcriptions, Reels & Karaoke Subtitles"
    if ext == ".html":
        return "08. Web Dashboard Interfaces"
    return "06. Cloud Tunnels, Telegram/Bot Daemons & Telemetry Logs"


def inspect_sqlite(db_path: str) -> str:
    """Extracts tables, DDL schemas, row counts, and first 5 sample rows."""
    lines = []
    try:
        conn = sqlite3.connect(db_path)
        cur = conn.cursor()
        cur.execute("SELECT name, sql FROM sqlite_master WHERE type='table' ORDER BY name;")
        tables = cur.fetchall()
        if not tables:
            lines.append("*(Database is initialized but contains no tables)*\n")
        for tname, sql in tables:
            try:
                cur.execute(f'SELECT COUNT(*) FROM "{tname}"')
                row_cnt = cur.fetchone()[0]
            except Exception:
                row_cnt = 0
            lines.append(f"### Table: `{tname}` ({row_cnt} total rows)\n")
            lines.append("````sql\n" + (sql or f"-- Table {tname} without DDL in sqlite_master") + "\n````\n")
            if row_cnt > 0:
                try:
                    cur.execute(f'SELECT * FROM "{tname}" LIMIT 5')
                    sample_rows = cur.fetchall()
                    col_names = [d[0] for d in cur.description] if cur.description else []
                    lines.append(f"**Sample Records (Top {len(sample_rows)} rows):**\n")
                    lines.append("```json\n")
                    formatted_rows = [dict(zip(col_names, row)) for row in sample_rows]
                    lines.append(json.dumps(formatted_rows, indent=2, default=str))
                    lines.append("\n```\n")
                except Exception as ex:
                    lines.append(f"*Could not fetch sample rows: {ex}*\n")
        conn.close()
    except Exception as e:
        lines.append(f"*(Error inspecting SQLite file: {e})*\n")
    return "\n".join(lines)


def get_lang(ext: str) -> str:
    mapping = {
        ".py": "python",
        ".json": "json",
        ".csv": "csv",
        ".ass": "ini",
        ".txt": "text",
        ".log": "text",
        ".err": "text",
        ".js": "javascript",
        ".html": "html",
    }
    return mapping.get(ext, "text")


def main() -> None:
    print(f"[{time.strftime('%H:%M:%S')}] Starting Saved Data Vault Compilation...")
    files_to_process = []
    for p in ALL_SAVED_FILES:
        if os.path.exists(p):
            files_to_process.append(p)
        else:
            print(f"  [WARN] Missing file: {p}")

    total_files = len(files_to_process)
    total_raw_bytes = sum(os.path.getsize(p) for p in files_to_process)
    print(f"[{time.strftime('%H:%M:%S')}] Total verified files: {total_files}")
    print(f"[{time.strftime('%H:%M:%S')}] Total raw size: {total_raw_bytes / (1024*1024):.2f} MB")

    # Group into categories
    buckets: Dict[str, List[Tuple[str, str, int]]] = {}
    for fp in files_to_process:
        bn = os.path.basename(fp)
        sz = os.path.getsize(fp)
        cat = categorize(bn)
        buckets.setdefault(cat, []).append((bn, fp, sz))

    print(f"[{time.strftime('%H:%M:%S')}] Writing master dossier to {OUTPUT_FILE}...")
    with open(OUTPUT_FILE, "w", encoding="utf-8", errors="replace") as out:
        # Title
        out.write("# AI-BS Sovereign Ecosystem: Saved Data Vault & Operational Dossier\n\n")
        out.write(f"**Target Compiler:** Gemini 4 Argon / Multi-Agent Review Engine  \n")
        out.write(f"**Compilation Date:** {time.strftime('%Y-%m-%d %H:%M:%S')}  \n")
        out.write(f"**Target Destination:** `{OUTPUT_FILE}`  \n")
        out.write(f"**Total Consolidated Files:** {total_files}  \n")
        out.write(f"**Total Source Size:** {total_raw_bytes / (1024*1024):.2f} MB ({total_raw_bytes:,} bytes)  \n\n")

        out.write("> [!IMPORTANT]\n")
        out.write("> **Document Scope & Purpose:**\n")
        out.write("> This document is the authoritative consolidation of all runtime operational databases, athlete recruiting matrices, bio-AI genomics payloads, social reel transcriptions, Cymatics drop monitors, and cloud tunnel logs from `C:\\AI-BS\\saved_data\\`.\n")
        out.write("> SQLite databases have been decompiled into exact DDL schemas and structured record dumps for direct tokenized inspection.\n\n")
        out.write("---\n\n")

        # Table of Contents
        out.write("## Table of Contents\n\n")
        for cat_name in sorted(buckets.keys()):
            items = buckets[cat_name]
            total_cat_sz = sum(sz for _, _, sz in items) / (1024 * 1024)
            cat_anchor = cat_name.lower().replace(" ", "-").replace("(", "").replace(")", "").replace("/", "").replace(",", "")
            out.write(f"### [{cat_name}](#{cat_anchor}) ({len(items)} files — {total_cat_sz:.2f} MB)\n")
            for bn, fp, sz in sorted(items, key=lambda x: x[0].lower()):
                file_anchor = "saved-" + bn.lower().replace(" ", "-").replace(".", "-").replace("(", "").replace(")", "").replace("+", "-").replace(":", "-")
                sz_str = f"{sz / 1024:.1f} KB" if sz < 1024*1024 else f"{sz / (1024*1024):.2f} MB"
                out.write(f"- [`{bn}`](#{file_anchor}) ({sz_str})\n")
            out.write("\n")

        out.write("---\n\n")

        # Process Categories
        for cat_name in sorted(buckets.keys()):
            cat_anchor = cat_name.lower().replace(" ", "-").replace("(", "").replace(")", "").replace("/", "").replace(",", "")
            out.write(f"<a id=\"{cat_anchor}\"></a>\n\n")
            out.write(f"# {cat_name}\n\n")

            # Visual Frames & JPG Graphic Assets
            if "Visual Frames" in cat_name:
                out.write("| Image File | Path | Size | SHA-256 Digest | Purpose |\n")
                out.write("| :--- | :--- | :--- | :--- | :--- |\n")
                for bn, fp, sz in sorted(buckets[cat_name], key=lambda x: x[0].lower()):
                    sz_str = f"{sz / 1024:.1f} KB" if sz < 1024*1024 else f"{sz / (1024*1024):.2f} MB"
                    sha = hash_file(fp)
                    purpose = "NVMe Hardware Benchmark Telemetry Frame" if "nvme" in bn else "Audio Staging / Test Frame Graphic"
                    out.write(f"| **`{bn}`** | `{fp}` | {sz_str} | `{sha[:16]}...` | {purpose} |\n")
                out.write("\n---\n\n")
                continue

            # SQLite Database Schemas & Record Dumps
            if "SQLite" in cat_name:
                for bn, fp, sz in sorted(buckets[cat_name], key=lambda x: x[0].lower()):
                    file_anchor = "saved-" + bn.lower().replace(" ", "-").replace(".", "-").replace("(", "").replace(")", "").replace("+", "-").replace(":", "-")
                    sz_str = f"{sz / 1024:.1f} KB" if sz < 1024*1024 else f"{sz / (1024*1024):.2f} MB"
                    out.write(f"<a id=\"{file_anchor}\"></a>\n\n")
                    out.write(f"## Database Vault: `{bn}`\n\n")
                    out.write(f"- **Path:** `{fp}`\n")
                    out.write(f"- **Raw SQLite Size:** {sz_str} ({sz:,} bytes)\n")
                    out.write(f"- **Decompiled Table Schemas & Record Samples:**\n\n")
                    sql_info = inspect_sqlite(fp)
                    out.write(sql_info)
                    out.write("\n---\n\n")
                continue

            # Standard Text / Code / JSON / CSV files
            for bn, fp, sz in sorted(buckets[cat_name], key=lambda x: x[0].lower()):
                file_anchor = "saved-" + bn.lower().replace(" ", "-").replace(".", "-").replace("(", "").replace(")", "").replace("+", "-").replace(":", "-")
                ext = os.path.splitext(bn)[1].lower()
                lang = get_lang(ext)
                sz_str = f"{sz / 1024:.1f} KB" if sz < 1024*1024 else f"{sz / (1024*1024):.2f} MB"

                out.write(f"<a id=\"{file_anchor}\"></a>\n\n")
                out.write(f"## File: `{bn}`\n\n")
                out.write(f"- **Original Path:** `{fp}`\n")
                out.write(f"- **File Size:** {sz_str} ({sz:,} bytes)\n")
                out.write(f"- **Format:** `{ext or 'raw'}` (Fenced: `{lang}`)\n\n")

                out.write(f"````{lang}\n")
                try:
                    with open(fp, "r", encoding="utf-8", errors="replace") as sf:
                        content = sf.read()
                        out.write(content)
                        if not content.endswith("\n"):
                            out.write("\n")
                except Exception as ex:
                    out.write(f"// Error reading file content: {ex}\n")
                out.write("````\n\n---\n\n")

    out_sz = os.path.getsize(OUTPUT_FILE)
    print(f"[{time.strftime('%H:%M:%S')}] Saved Data Compilation Complete!")
    print(f"[{time.strftime('%H:%M:%S')}] Output: {OUTPUT_FILE}")
    print(f"[{time.strftime('%H:%M:%S')}] Size: {out_sz / (1024*1024):.2f} MB ({out_sz:,} bytes)")


if __name__ == "__main__":
    main()
