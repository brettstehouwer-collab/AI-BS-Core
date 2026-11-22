import json
import os

transcript_path = r'C:\Users\footb\.gemini\antigravity-ide\brain\c1a34017-4129-44db-85f8-d952501280a2\.system_generated\logs\transcript_full.jsonl'
output_dir = r'C:\AI-BS\scratch'

versions = []
with open(transcript_path, 'r', encoding='utf-8') as f:
    for line in f:
        try:
            data = json.loads(line)
            if 'tool_calls' in data:
                for tool in data['tool_calls']:
                    if tool['name'] == 'write_to_file' and 'ProjectNoCoStudioTab.jsx' in tool['args'].get('TargetFile', ''):
                        versions.append(tool['args']['CodeContent'])
        except Exception as e:
            pass

for i, v in enumerate(versions):
    with open(os.path.join(output_dir, f'recovered_noco_{i}.jsx'), 'w', encoding='utf-8') as out:
        out.write(v)

print(f"Recovered {len(versions)} full writes.")
