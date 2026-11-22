import os
import json
import sqlite3
import sys

sys.stdout.reconfigure(encoding='utf-8')

db_path = r'C:\Users\footb\.gemini\antigravity\conversation_summaries.db'
conn = sqlite3.connect(db_path)
cur = conn.cursor()

query = "SELECT conversation_id, title, workspace, project, step_count FROM conversations_fts WHERE title != '';"
conversations = cur.execute(query).fetchall()
conn.close()

brain_dir = r'C:\Users\footb\.gemini\antigravity-ide\brain'

results = []

keywords = [
    'ai-bs', 'ai_bs', 'aibs', 'stehouwer', 'prestige', 'unrealhub', 'thebadside',
    '8080', '5173', '11434', '11435', '8000', 'saved_checkpoint', 'architectural ledger',
    'fastapi', 'chromadb', 'pearl', 'broad.mp4', 'clore', 'vast.ai', 'screenplay',
    'offline writing', 'voicecoach', 'voice coach', 'binaural', 'quarantine', 'sqlite_opt',
    'c:\\ai-bs', 'c:/ai-bs'
]

for cid, title, ws, proj, steps in conversations:
    c_brain = os.path.join(brain_dir, cid, '.system_generated', 'logs', 'transcript.jsonl')
    exists = os.path.exists(c_brain)
    
    user_prompts = []
    matched_keywords = set()
    total_lines = 0
    cwds = set()
    
    if exists:
        try:
            with open(c_brain, 'r', encoding='utf-8', errors='ignore') as f:
                for line in f:
                    total_lines += 1
                    try:
                        data = json.loads(line)
                    except Exception:
                        continue
                    
                    # capture Cwd if tool call
                    tool_calls = data.get('tool_calls', [])
                    for tc in tool_calls:
                        args = tc.get('arguments', {})
                        if isinstance(args, dict) and 'Cwd' in args:
                            cwds.add(args['Cwd'])
                        elif isinstance(args, str) and 'Cwd' in args:
                            # simple match
                            if 'c:\\AI-BS' in args or 'c:/AI-BS' in args:
                                cwds.add('c:\\AI-BS')
                    
                    if data.get('type') == 'USER_INPUT':
                        content = data.get('content', '')
                        if content and len(user_prompts) < 15:
                            # clean tags
                            c_clean = content.replace('<USER_REQUEST>', '').replace('</USER_REQUEST>', '').strip()
                            if c_clean:
                                user_prompts.append(c_clean[:150])
                    
                    line_lower = line.lower()
                    for kw in keywords:
                        if kw in line_lower:
                            matched_keywords.add(kw)
        except Exception as e:
            pass
            
    is_aibs_workspace = any('ai-bs' in c.lower() for c in cwds) or any(k in [w.lower() for w in [ws, proj, title]] for k in ['ai-bs', 'ai bs'])
    is_aibs_content = len(matched_keywords) >= 2 or 'c:\\ai-bs' in matched_keywords or 'ai-bs' in matched_keywords
    
    results.append({
        'id': cid,
        'title': title,
        'workspace': ws,
        'project': proj,
        'steps': steps,
        'cwds': list(cwds)[:5],
        'matched_keywords': list(matched_keywords),
        'is_aibs': is_aibs_workspace or is_aibs_content,
        'first_prompt': user_prompts[0] if user_prompts else '',
        'prompt_count': len(user_prompts)
    })

# Sort: AI-BS related first, then by steps desc
results.sort(key=lambda x: (not x['is_aibs'], -x['steps']))

print(f"Total analyzed: {len(results)}")
aibs_count = sum(1 for r in results if r['is_aibs'])
print(f"Total AI-BS related conversations identified: {aibs_count}")

with open(r'c:\AI-BS\scratch\all_conversations_manifest.json', 'w', encoding='utf-8') as out_f:
    json.dump(results, out_f, indent=2)

print("\nTop AI-BS conversations:")
for r in results[:35]:
    if r['is_aibs']:
        print(f"[{r['project'] or 'Global'}] {r['title']} | Steps: {r['steps']} | CWDs: {r['cwds']} | KW: {r['matched_keywords'][:4]}")
