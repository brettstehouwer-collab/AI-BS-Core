import os

brain_dir = r'C:\Users\footb\.gemini\antigravity\brain'
transcripts = []
for d in os.listdir(brain_dir):
    log_dir = os.path.join(brain_dir, d, '.system_generated', 'logs')
    t_file = os.path.join(log_dir, 'transcript.jsonl')
    if os.path.exists(t_file):
        transcripts.append((d, os.path.getsize(t_file)))

print(f"Total transcripts found in antigravity/brain: {len(transcripts)} out of {len(os.listdir(brain_dir))} folders")
for t in transcripts[:10]:
    print(t[0], "Size:", t[1], "bytes")
