from youtube_transcript_api import YouTubeTranscriptApi

try:
    ytt = YouTubeTranscriptApi()
    transcript = ytt.fetch('zc-dsSauYGM')
    with open(r'C:\AI-BS\scratch\transcript_clean.txt', 'w', encoding='utf-8') as f:
        for entry in transcript:
            start = getattr(entry, 'start', getattr(entry, 'start_time', 0))
            text = getattr(entry, 'text', str(entry))
            f.write(f"[{float(start):.1f}s]: {text}\n")
    print(f"Successfully extracted {len(transcript)} lines!")
except Exception as e:
    print("Error with fetch:", e)
