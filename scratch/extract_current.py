import json
import os
log_path = r'C:\Users\footb\.gemini\antigravity-ide\brain\8f8d4944-852d-45f9-be12-dd5696ccd829\.system_generated\logs\transcript.jsonl'
output_txt = r'C:\Users\footb\AI-BS_Matrix\llm_training_data\chat_export_today.txt'
output_jsonl = r'C:\Users\footb\AI-BS_Matrix\llm_training_data\chat_export_today.jsonl'
os.makedirs(r'C:\Users\footb\AI-BS_Matrix\llm_training_data', exist_ok=True)

history_txt = []
history_jsonl = []

try:
    with open(log_path, 'r', encoding='utf-8') as f:
        for line in f:
            if not line.strip():
                continue
            data = json.loads(line)
            source = data.get('source', '')
            type_ = data.get('type', '')
            content = data.get('content', '')

            if source == 'USER_EXPLICIT' and type_ == 'USER_INPUT':
                if '<USER_REQUEST>' in content:
                    text = content.split('<USER_REQUEST>')[1].split(
                        '</USER_REQUEST>')[0].strip()
                    if text:
                        history_txt.append(f'USER:\n{text}\n')
                        history_jsonl.append({'role': 'user', 'content': text})

            elif source == 'MODEL' and type_ == 'PLANNER_RESPONSE':
                if content and not content.startswith('<USER_REQUEST>'):
                    history_txt.append(f'AI:\n{content.strip()}\n')
                    history_jsonl.append(
                        {'role': 'assistant', 'content': content.strip()})

    with open(output_txt, 'w', encoding='utf-8') as out_f:
        out_f.write('=== AI-BS Development Chat History ===\n\n')
        out_f.write(
            '\n--------------------------------------------------\n'.join(history_txt))

    with open(output_jsonl, 'w', encoding='utf-8') as out_j:
        for entry in history_jsonl:
            out_j.write(json.dumps(entry) + '\n')

    print(
        f'Successfully extracted {
            len(history_txt)} messages to llm_training_data folder.')

except Exception as e:
    print(f'Error extracting history: {e}')
