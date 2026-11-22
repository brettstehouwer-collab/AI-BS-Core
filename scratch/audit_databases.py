import os
import sqlite3
import json

db_results = []
lockfiles = []

# Search for all .db and .sqlite files
for root, dirs, files in os.walk(r'C:\AI-BS'):
    if any(ig in root for ig in ['pyppeteer_env', 'node_modules', '.git', 'Android Studio']):
        continue
    for f in files:
        if f.endswith('.db-wal') or f.endswith('.db-shm') or f.endswith('.db-journal'):
            lockfiles.append(os.path.join(root, f))
        elif f.endswith('.db') or f.endswith('.sqlite') or f.endswith('.sqlite3'):
            p = os.path.join(root, f)
            rel = os.path.relpath(p, r'C:\AI-BS')
            size_kb = round(os.path.getsize(p) / 1024, 2)
            try:
                conn = sqlite3.connect(p, timeout=2.0)
                cur = conn.cursor()
                cur.execute('PRAGMA integrity_check;')
                integrity = cur.fetchone()[0]
                cur.execute('PRAGMA journal_mode;')
                jmode = cur.fetchone()[0]
                cur.execute("SELECT name FROM sqlite_master WHERE type='table';")
                tables = [r[0] for r in cur.fetchall()]
                conn.close()
                db_results.append({
                    'file': rel,
                    'size_kb': size_kb,
                    'integrity': integrity,
                    'journal_mode': jmode,
                    'table_count': len(tables),
                    'tables': tables[:10]
                })
            except Exception as e:
                db_results.append({
                    'file': rel,
                    'size_kb': size_kb,
                    'error': str(e)
                })

chroma_info = {}
for c_dir in [r'C:\AI-BS\chroma_db', r'C:\AI-BS\stehouwer_vector_memory']:
    if os.path.exists(c_dir):
        files = os.listdir(c_dir)
        chroma_info[os.path.basename(c_dir)] = {
            'exists': True,
            'file_count': len(files),
            'files': files
        }

output = {
    'total_databases_checked': len(db_results),
    'healthy_databases': sum(1 for d in db_results if d.get('integrity') == 'ok'),
    'lockfiles_found': lockfiles,
    'chroma_vector_stores': chroma_info,
    'databases': db_results
}

with open(r'C:\AI-BS\scratch\phase5_db_audit_results.json', 'w', encoding='utf-8') as out:
    json.dump(output, out, indent=2)

print(f"Phase 5 DB audit completed! Checked {len(db_results)} databases.")
