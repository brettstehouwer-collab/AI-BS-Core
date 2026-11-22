import os
import sys
import json
import sqlite3
import datetime
import re

sys.stdout.reconfigure(encoding='utf-8')

DB_PATH = r'C:\Users\footb\.gemini\antigravity\conversation_summaries.db'
BRAIN_DIR = r'C:\Users\footb\.gemini\antigravity\brain'
OUTPUT_DIR = r'C:\AI-BS\learning'
CONV_OUTPUT_DIR = os.path.join(OUTPUT_DIR, 'conversations')
os.makedirs(CONV_OUTPUT_DIR, exist_ok=True)
MASTER_MD_PATH = os.path.join(OUTPUT_DIR, 'AI_BS_MASTER_CONVERSATIONS_AND_SOLUTIONS.md')

# 1. Load metadata from conversation_summaries.db
conn = sqlite3.connect(DB_PATH)
cur = conn.cursor()
db_meta = {}
try:
    rows = cur.execute("SELECT conversation_id, title, workspace, project, step_count, last_modified_time FROM conversations_fts WHERE title != '';").fetchall()
    for cid, title, ws, proj, steps, lmt in rows:
        db_meta[cid] = {
            'title': title,
            'workspace': ws,
            'project': proj,
            'step_count': steps,
            'last_modified_time': lmt
        }
except Exception as e:
    print("DB query error:", e)
finally:
    conn.close()

# 2. Collect all conversations from brain
all_brain_dirs = [d for d in os.listdir(BRAIN_DIR) if os.path.isdir(os.path.join(BRAIN_DIR, d))]
print(f"Total brain directories found: {len(all_brain_dirs)}")

# AI-BS relevance filter
KEYWORDS = [
    'ai-bs', 'ai_bs', 'aibs', 'stehouwer', 'prestige', 'unrealhub', 'thebadside',
    'c:\\ai-bs', 'c:/ai-bs', 'broadcast', 'screenplay', 'pearl', 'clore', 'vast.ai',
    'chromadb', 'fastapi', '8080', '5173', '11434', '11435', 'saved_checkpoint',
    'master architectural ledger', 'voicecoach', 'voice coach', 'binaural',
    'dyadic', 'video stuttering', 'network mesh'
]

# Non-AI-BS explicit exclusions (like strictly personal or unrelated tasks)
EXCLUDE_TITLES = [
    'Black Ops 7 Release Date',
    'Biblical Text Word Statistics',
    'Grand Rapids Property Records Lookup'
]

def clean_tags(text):
    if not text:
        return ""
    text = re.sub(r'<USER_REQUEST>\s*', '', text)
    text = re.sub(r'\s*</USER_REQUEST>', '', text)
    text = re.sub(r'<ADDITIONAL_METADATA>[\s\S]*?</ADDITIONAL_METADATA>', '', text)
    text = re.sub(r'<USER_SETTINGS_CHANGE>[\s\S]*?</USER_SETTINGS_CHANGE>', '', text)
    return text.strip()

def format_timestamp(ts):
    if not ts:
        return ""
    try:
        # Check if nanoseconds or seconds
        val = int(ts)
        if val > 1e16:
            val = val / 1e9
        elif val > 1e12:
            val = val / 1e3
        return datetime.datetime.fromtimestamp(val, tz=datetime.timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')
    except Exception:
        return str(ts)

analyzed_conversations = []

for cid in all_brain_dirs:
    t_path = os.path.join(BRAIN_DIR, cid, '.system_generated', 'logs', 'transcript.jsonl')
    if not os.path.exists(t_path):
        continue
        
    meta = db_meta.get(cid, {})
    title = meta.get('title') or f"Conversation {cid[:8]}"
    project = meta.get('project') or meta.get('workspace') or 'Global / AI-BS Workspace Root'
    step_count = meta.get('step_count', 0)
    
    if title in EXCLUDE_TITLES:
        continue
        
    # Read transcript turns
    turns = []
    matched_reasons = []
    matched_cwds = set()
    user_prompts = []
    
    current_turn = None
    turn_counter = 0
    
    try:
        with open(t_path, 'r', encoding='utf-8', errors='ignore') as f:
            for line in f:
                if not line.strip():
                    continue
                try:
                    step = json.loads(line)
                except Exception:
                    continue
                    
                stype = step.get('type')
                scontent = step.get('content', '')
                sthinking = step.get('thinking', '')
                stool_calls = step.get('tool_calls', [])
                screated = step.get('created_at', '')
                
                # Check tool calls for cwds
                for tc in stool_calls:
                    args = tc.get('arguments', {})
                    if isinstance(args, dict) and 'Cwd' in args:
                        matched_cwds.add(args['Cwd'])
                
                if stype == 'USER_INPUT':
                    cleaned_prompt = clean_tags(scontent)
                    if cleaned_prompt:
                        user_prompts.append(cleaned_prompt)
                        turn_counter += 1
                        if current_turn:
                            turns.append(current_turn)
                        current_turn = {
                            'turn': turn_counter,
                            'created_at': screated,
                            'user_prompt': cleaned_prompt,
                            'thinking_blocks': [],
                            'tool_actions': [],
                            'model_responses': []
                        }
                elif current_turn is not None:
                    if sthinking:
                        # Keep thinking summary or key thoughts
                        current_turn['thinking_blocks'].append(sthinking)
                    if stool_calls:
                        for tc in stool_calls:
                            action_name = tc.get('name') or tc.get('toolAction') or 'tool_call'
                            summary = tc.get('toolSummary') or tc.get('description') or ''
                            args = tc.get('arguments', {})
                            cmd = args.get('CommandLine') or args.get('TargetFile') or args.get('Query') or ''
                            current_turn['tool_actions'].append({
                                'name': action_name,
                                'summary': summary,
                                'target': cmd
                            })
                    if stype == 'PLANNER_RESPONSE' and scontent:
                        # Clean model output
                        c_clean = scontent.strip()
                        if c_clean:
                            current_turn['model_responses'].append(c_clean)
        if current_turn:
            turns.append(current_turn)
    except Exception as e:
        print(f"Error reading transcript for {cid}: {e}")
        continue
        
    # Check AI-BS relevance
    is_aibs = False
    
    title_lower = title.lower()
    for kw in KEYWORDS:
        if kw in title_lower:
            is_aibs = True
            matched_reasons.append(f"Title contains '{kw}'")
            break
            
    if any('ai-bs' in str(c).lower() for c in matched_cwds):
        is_aibs = True
        matched_reasons.append("Tool Cwd includes c:\\AI-BS")
        
    if not is_aibs:
        for prompt in user_prompts[:5]:
            p_lower = prompt.lower()
            for kw in ['ai-bs', 'c:\\ai-bs', 'c:/ai-bs', 'prestige', 'unrealhub', 'stehouwer']:
                if kw in p_lower:
                    is_aibs = True
                    matched_reasons.append(f"Prompt contains '{kw}'")
                    break
            if is_aibs:
                break
                
    if not is_aibs and project in ['lucid-bardeen', 'VOICECOACHF', 'clever-hypatia', 'goofy-bose']:
        # If in these project workspaces, check if there's any mention of AI-BS files/system
        all_text = (title + " " + " ".join(user_prompts[:3])).lower()
        if any(k in all_text for k in ['ai', 'code', 'script', 'port', 'test', 'status', 'ide', 'build', 'websocket', 'error', 'bug', 'fix', 'run']):
            is_aibs = True
            matched_reasons.append(f"Project context '{project}' engineering activity")
            
    if is_aibs:
        analyzed_conversations.append({
            'id': cid,
            'title': title,
            'project': project,
            'step_count': step_count or len(turns),
            'last_modified_time': meta.get('last_modified_time', ''),
            'matched_reasons': matched_reasons,
            'cwds': list(matched_cwds),
            'turns': turns
        })

print(f"\nFiltered {len(analyzed_conversations)} AI-BS related conversations out of {len(all_brain_dirs)}")

# Sort by project, then by step count descending
analyzed_conversations.sort(key=lambda x: (str(x['project']), -x['step_count']))

# Write individual conversation markdown files
for c in analyzed_conversations:
    safe_proj = re.sub(r'[^a-zA-Z0-9_\-]', '_', str(c['project'])).strip()
    safe_title = re.sub(r'[^a-zA-Z0-9_\-]', '_', str(c['title'])).strip()[:60]
    conv_file = os.path.join(CONV_OUTPUT_DIR, f"{safe_proj}_{safe_title}_{c['id'][:8]}.md")
    
    with open(conv_file, 'w', encoding='utf-8') as cf:
        cf.write(f"# {c['title']}\n\n")
        cf.write(f"- **Project / Workspace:** `{c['project']}`\n")
        cf.write(f"- **Conversation ID:** `{c['id']}`\n")
        cf.write(f"- **Step Count:** {c['step_count']}\n")
        cf.write(f"- **Matched Criteria:** {', '.join(c['matched_reasons'])}\n")
        if c['cwds']:
            cf.write(f"- **Working Directories:** {', '.join([f'`{x}`' for x in c['cwds'][:5]])}\n")
        cf.write(f"- **Total Interaction Turns:** {len(c['turns'])}\n\n")
        cf.write("---\n\n")
        
        for turn in c['turns']:
            cf.write(f"## Turn {turn['turn']}\n\n")
            if turn['created_at']:
                cf.write(f"*{format_timestamp(turn['created_at'])}*\n\n")
            cf.write("### 👤 User Request / Prompt\n\n")
            cf.write(f"> {turn['user_prompt']}\n\n")
            
            if turn['thinking_blocks']:
                cf.write("### 🧠 Agent Thinking & Problem Analysis\n\n")
                for th in turn['thinking_blocks']:
                    # Truncate if massive
                    th_text = th.strip()
                    if len(th_text) > 2500:
                        th_text = th_text[:2500] + "\n\n*(...thinking process continues...)*"
                    cf.write(f"```text\n{th_text}\n```\n\n")
                    
            if turn['tool_actions']:
                cf.write("### 🛠️ Problem-Solving Actions & Tool Execution\n\n")
                for ta in turn['tool_actions'][:15]: # summarize up to 15 key actions
                    cf.write(f"- **{ta['name']}**: {ta['summary']} `{ta['target'][:100]}`\n")
                if len(turn['tool_actions']) > 15:
                    cf.write(f"- *(...and {len(turn['tool_actions']) - 15} more operational steps...)*\n")
                cf.write("\n")
                
            if turn['model_responses']:
                cf.write("### 💡 Agent Solution & Resolution\n\n")
                for mr in turn['model_responses']:
                    cf.write(f"{mr}\n\n")
            cf.write("---\n\n")

print(f"Wrote {len(analyzed_conversations)} standalone conversation files to {CONV_OUTPUT_DIR}")

# 3. Build MASTER single Markdown file
with open(MASTER_MD_PATH, 'w', encoding='utf-8') as mf:
    mf.write("# AI-BS Master Learning Archive: Conversations, Thinking Processes & Solutions\n\n")
    mf.write("This master document consolidates all historical Antigravity / Google Gemini conversations, user prompts, internal thinking processes, and problem-solving steps across all project folders relating to **AI-BS (Autonomous Intelligence & Build System)**.\n\n")
    mf.write(f"**Generated:** {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    mf.write(f"**Total AI-BS Conversations Compiled:** {len(analyzed_conversations)}\n")
    mf.write(f"**Output Directory:** [`C:\\AI-BS\\learning`](file:///C:/AI-BS/learning)\n\n")
    
    mf.write("## 📚 Table of Contents by Project Group\n\n")
    
    current_proj = None
    for idx, c in enumerate(analyzed_conversations, 1):
        if c['project'] != current_proj:
            current_proj = c['project']
            mf.write(f"### 📁 Project: `{current_proj}`\n\n")
        safe_link = f"#{c['title'].lower().replace(' ', '-').replace('/', '').replace(':', '')[:40]}"
        mf.write(f"{idx}. [{c['title']}]({safe_link}) - *{c['step_count']} steps, {len(c['turns'])} turns* (ID: `{c['id'][:8]}`)\n")
    
    mf.write("\n---\n\n")
    
    # Detailed contents
    for idx, c in enumerate(analyzed_conversations, 1):
        mf.write(f"# {idx}. {c['title']}\n\n")
        mf.write(f"- **Project / Workspace:** `{c['project']}`\n")
        mf.write(f"- **Conversation ID:** `{c['id']}`\n")
        mf.write(f"- **Step Count:** {c['step_count']} steps | **User Turns:** {len(c['turns'])}\n")
        mf.write(f"- **Classification Context:** {', '.join(c['matched_reasons'])}\n")
        if c['cwds']:
            mf.write(f"- **Active Host Directories:** {', '.join([f'`{x}`' for x in c['cwds'][:5]])}\n")
        mf.write("\n")
        
        # Summary of the conversation
        first_prompt = c['turns'][0]['user_prompt'] if c['turns'] else 'No prompt'
        mf.write(f"> **Initial Objective:** {first_prompt[:250]}...\n\n")
        
        for turn in c['turns']:
            mf.write(f"### 💬 Turn {turn['turn']}: User Request\n\n")
            mf.write(f"{turn['user_prompt']}\n\n")
            
            if turn['thinking_blocks']:
                mf.write("#### 🧠 Thinking & Architectural Reasoning\n\n")
                # Pick the most substantial thinking block
                best_th = max(turn['thinking_blocks'], key=len)
                th_snippet = best_th.strip()
                if len(th_snippet) > 1800:
                    th_snippet = th_snippet[:1800] + "\n\n*(...reasoning continues...)*"
                mf.write(f"```text\n{th_snippet}\n```\n\n")
                
            if turn['tool_actions']:
                mf.write("#### ⚡ Problem-Solving Steps & Executions\n\n")
                for ta in turn['tool_actions'][:8]:
                    mf.write(f"- **{ta['name']}**: {ta['summary']} `{ta['target'][:90]}`\n")
                if len(turn['tool_actions']) > 8:
                    mf.write(f"- *(...and {len(turn['tool_actions']) - 8} additional automated tool operations)*\n")
                mf.write("\n")
                
            if turn['model_responses']:
                mf.write("#### 🎯 Resolution & Key Deliverables\n\n")
                last_response = turn['model_responses'][-1]
                if len(last_response) > 3000:
                    last_response = last_response[:3000] + "\n\n*(...response truncated for master compilation readability; see full standalone file for complete output...)*"
                mf.write(f"{last_response}\n\n")
                
            mf.write("---\n\n")
        mf.write("\n\n")

print(f"Master file successfully created: {MASTER_MD_PATH}")
print(f"Size: {os.path.getsize(MASTER_MD_PATH)} bytes")
