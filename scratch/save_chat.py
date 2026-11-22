import json
from pathlib import Path

transcript_path = Path(
    r'C:\Users\footb\.gemini\antigravity-ide\brain\d621f7b6-2352-4abb-ba12-344c32bb461e\.system_generated\logs\transcript_full.jsonl')
output_path = Path('c:/Users/footb/AI-BS_Matrix/AI_BS_Chat_Log.md')

if not transcript_path.exists():
    print('Transcript not found!')
    exit(1)

with open(transcript_path, 'r', encoding='utf-8') as fin, open(output_path, 'w', encoding='utf-8') as fout:
    fout.write('# AI-BS Matrix Chat Log\n\n')
    for line in fin:
        try:
            data = json.loads(line)
            role = data.get('source', 'UNKNOWN')
            step_type = data.get('type', '')
            content = data.get('content', '')

            if role == 'USER_EXPLICIT' and step_type == 'USER_INPUT':
                fout.write(f'### User\n{content}\n\n---\n\n')
            elif role == 'MODEL' and step_type == 'PLANNER_RESPONSE':
                fout.write(f'### AI-BS Matrix\n{content}\n\n---\n\n')
        except BaseException:
            pass

print(f'Chat saved successfully to {output_path}')
