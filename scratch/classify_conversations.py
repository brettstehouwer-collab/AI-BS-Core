import os
import json
import sqlite3
import sys

sys.stdout.reconfigure(encoding='utf-8')

# 1. Connect to summaries db
db_path = r'C:\Users\footb\.gemini\antigravity\conversation_summaries.db'
conn = sqlite3.connect(db_path)
cur = conn.cursor()

query = "SELECT conversation_id, title, workspace, project, step_count FROM conversations_fts WHERE title != '';"
conversations = cur.execute(query).fetchall()
conn.close()

print(f"Total indexed conversations: {len(conversations)}")

# 2. Check each conversation in brain directory
brain_dir = r'C:\Users\footb\.gemini\antigravity-ide\brain'

aibs_conversations = []
non_aibs_conversations = []

for cid, title, ws, proj, steps in conversations:
    c_brain = os.path.join(brain_dir, cid, '.system_generated', 'logs', 'transcript.jsonl')
    exists = os.path.exists(c_brain)
    
    # Check if AI-BS related
    is_aibs = False
    reasons = []
    
    title_lower = title.lower()
    if any(k in title_lower for k in ['ai-bs', 'ai bs', 'aibs', 'architectural ledger', 'prestige', 'dyadic', 'stehouwer', 'broadcast', 'screenplay', 'unreal', 'vst3', 'clore', 'vast']):
        is_aibs = True
        reasons.append(f"Title keyword match: '{title}'")
    
    # Check first few user prompts and workspace
    prompts = []
    if exists:
        try:
            with open(c_brain, 'r', encoding='utf-8') as f:
                for line in f:
                    data = json.loads(line)
                    if data.get('type') == 'USER_INPUT':
                        text = data.get('content', '')
                        if text:
                            prompts.append(text[:200])
                            t_lower = text.lower()
                            if any(k in t_lower for k in ['ai-bs', 'c:\\ai-bs', 'c:/ai-bs', 'stehouwer', 'prestige', 'unrealhub', 'thebadside']):
                                is_aibs = True
                                reasons.append("Prompt content match (c:\\AI-BS)")
                                break
                    if len(prompts) >= 10:
                        break
        except Exception as e:
            pass
            
    if is_aibs:
        aibs_conversations.append((cid, title, ws, proj, steps, reasons, len(prompts)))
    else:
        non_aibs_conversations.append((cid, title, ws, proj, steps, len(prompts)))

print(f"\nFound {len(aibs_conversations)} AI-BS related conversations:")
for c in aibs_conversations:
    print(f"- [{c[3] or 'No-Project'}] {c[1]} (ID: {c[0][:8]}, Steps: {c[4]}) -> {c[5][0]}")

print(f"\nOther {len(non_aibs_conversations)} conversations:")
for c in non_aibs_conversations[:15]:
    print(f"- [{c[3] or 'No-Project'}] {c[1]} (ID: {c[0][:8]}, Steps: {c[4]})")
