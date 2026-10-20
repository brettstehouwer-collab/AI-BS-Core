import json
import os

json_path = r"C:\AI-BS\saved_data\facebook_reel_transcription.json"
ass_path = r"C:\AI-BS\saved_data\facebook_reel_karaoke.ass"

with open(json_path, "r", encoding="utf-8") as f:
    data = json.load(f)

# ASS Header for 1080x1920 (9:16 vertical video)
ass_header = """[Script Info]
Title: Facebook Reel Karaoke
ScriptType: v4.00+
WrapStyle: 0
ScaledBorderAndShadow: yes
YCbCr Matrix: TV.709
PlayResX: 1080
PlayResY: 1920

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Karaoke,Arial,54,&H0000D7FF,&H00FFFFFF,&H00000000,&H80000000,-1,0,0,0,100,100,1,0,1,4,2,2,60,60,260,1
Style: KaraokeHeader,Arial,36,&H00FFFFFF,&H0000D7FF,&H00000000,&H80000000,-1,0,0,0,100,100,1,0,1,3,1,8,60,60,200,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""

def format_ass_time(seconds):
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    centis = int(round((seconds - int(seconds)) * 100))
    if centis == 100:
        centis = 99
    return f"{hours:01d}:{minutes:02d}:{secs:02d}.{centis:02d}"

events = []

for seg in data["segments"]:
    words = seg.get("words", [])
    if not words:
        continue
    
    # Split into manageable chunks if words > 8
    chunks = []
    current_chunk = []
    for w in words:
        current_chunk.append(w)
        # break on punctuation or length
        word_text = w["word"].strip()
        if len(current_chunk) >= 7 or (len(current_chunk) >= 4 and any(word_text.endswith(p) for p in [",", ".", "!", "?"])):
            chunks.append(current_chunk)
            current_chunk = []
    if current_chunk:
        chunks.append(current_chunk)
        
    for chunk in chunks:
        if not chunk:
            continue
        line_start = chunk[0]["start"]
        line_end = chunk[-1]["end"]
        
        # Give a small padding
        disp_start = max(0.0, line_start - 0.15)
        disp_end = line_end + 0.35
        
        # Build ASS karaoke string using \kf (smooth sweep fill)
        ass_text_parts = []
        last_t = line_start
        for w in chunk:
            w_start = w["start"]
            w_end = w["end"]
            
            # Lead-in silence
            lead_in = int(round((w_start - last_t) * 100))
            if lead_in > 0:
                ass_text_parts.append(f"{{\\k{lead_in}}}")
                
            dur = max(5, int(round((w_end - w_start) * 100)))
            clean_word = w["word"].replace("{", "").replace("}", "")
            ass_text_parts.append(f"{{\\kf{dur}}}{clean_word}")
            last_t = w_end
            
        ass_line = "".join(ass_text_parts)
        events.append(f"Dialogue: 0,{format_ass_time(disp_start)},{format_ass_time(disp_end)},Karaoke,,0,0,0,,{ass_line}")

with open(ass_path, "w", encoding="utf-8") as f:
    f.write(ass_header + "\n".join(events) + "\n")

print(f"Generated {len(events)} karaoke subtitle lines in {ass_path}")
