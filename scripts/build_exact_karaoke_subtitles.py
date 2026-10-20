import json
import os

json_path = r"C:\AI-BS\saved_data\audio_for_vid_transcription.json"
ass_16x9_path = r"C:\AI-BS\saved_data\pendulum_audio_for_vid_16x9.ass"
ass_9x16_path = r"C:\AI-BS\saved_data\pendulum_audio_for_vid_9x16.ass"

with open(json_path, "r", encoding="utf-8") as f:
    data = json.load(f)

# Header for 1920x1080 (16:9 Widescreen)
header_16x9 = """[Script Info]
Title: Pendulum Running Lyrics (16:9)
ScriptType: v4.00+
WrapStyle: 0
ScaledBorderAndShadow: yes
YCbCr Matrix: TV.709
PlayResX: 1920
PlayResY: 1080

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: KaraokePrimary,Arial,48,&H0000D7FF,&H00FFFFFF,&H00000000,&HB0000000,-1,0,0,0,100,100,1,0,1,5,3,2,100,100,110,1
Style: KaraokeBacking,Arial,40,&H0050E0FF,&H00CCCCCC,&H00000000,&HB0000000,-1,1,0,0,100,100,1,0,1,4,2,2,100,100,75,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""

# Header for 1080x1920 (9:16 Vertical)
header_9x16 = """[Script Info]
Title: Pendulum Running Lyrics (9:16)
ScriptType: v4.00+
WrapStyle: 0
ScaledBorderAndShadow: yes
YCbCr Matrix: TV.709
PlayResX: 1080
PlayResY: 1920

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: KaraokePrimary,Arial,52,&H0000D7FF,&H00FFFFFF,&H00000000,&HB0000000,-1,0,0,0,100,100,1,0,1,5,3,2,60,60,320,1
Style: KaraokeBacking,Arial,44,&H0050E0FF,&H00CCCCCC,&H00000000,&HB0000000,-1,1,0,0,100,100,1,0,1,4,2,2,60,60,250,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""

def format_ass_time(seconds):
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    centis = int(round((seconds - int(seconds)) * 100))
    if centis >= 100:
        centis = 99
    return f"{hours:01d}:{minutes:02d}:{secs:02d}.{centis:02d}"

events = []

for seg in data["segments"]:
    words = seg.get("words", [])
    if not words:
        continue
        
    # Split long segments (>7 words or on natural pauses)
    chunks = []
    current_chunk = []
    for w in words:
        current_chunk.append(w)
        w_text = w["word"].strip()
        # Natural break points
        if len(current_chunk) >= 7 or (len(current_chunk) >= 4 and any(w_text.endswith(p) for p in [",", ".", "!", "?"])):
            chunks.append(current_chunk)
            current_chunk = []
    if current_chunk:
        chunks.append(current_chunk)
        
    for chunk in chunks:
        if not chunk:
            continue
        line_start = chunk[0]["start"]
        line_end = chunk[-1]["end"]
        
        disp_start = max(0.0, line_start - 0.1)
        disp_end = line_end + 0.3
        
        # Check if backing / whispered
        raw_line_text = " ".join(w["word"].strip() for w in chunk)
        is_backing = "(" in raw_line_text or "unfortunately is true" in raw_line_text or "cut the noise" in raw_line_text
        style = "KaraokeBacking" if is_backing else "KaraokePrimary"
        
        ass_parts = []
        last_t = line_start
        for w in chunk:
            w_start = w["start"]
            w_end = w["end"]
            
            lead_in = int(round((w_start - last_t) * 100))
            if lead_in > 0:
                ass_parts.append(f"{{\\k{lead_in}}}")
                
            dur = max(6, int(round((w_end - w_start) * 100)))
            clean_word = w["word"].replace("{", "").replace("}", "")
            
            # Text polish from user lyrics
            if "absorbant" in clean_word.lower():
                clean_word = clean_word.replace("absorbant", "absorbing").replace("Absorbant", "Absorbing")
            if "uncompability" in clean_word.lower():
                clean_word = clean_word.replace("uncompability", "uncomfortability")
            if "buy me" in clean_word.lower():
                clean_word = clean_word.replace("buy me", "bite me")
            if "willpower" in clean_word.lower():
                clean_word = "WILL POWER"
                
            ass_parts.append(f"{{\\kf{dur}}}{clean_word}")
            last_t = w_end
            
        karaoke_text = "".join(ass_parts)
        events.append(f"Dialogue: 0,{format_ass_time(disp_start)},{format_ass_time(disp_end)},{style},,0,0,0,,{karaoke_text}")

with open(ass_16x9_path, "w", encoding="utf-8") as f:
    f.write(header_16x9 + "\n".join(events) + "\n")

with open(ass_9x16_path, "w", encoding="utf-8") as f:
    f.write(header_9x16 + "\n".join(events) + "\n")

print(f"Successfully generated {len(events)} exact-timed karaoke lines!")
print(f"16:9: {ass_16x9_path}")
print(f"9:16: {ass_9x16_path}")
