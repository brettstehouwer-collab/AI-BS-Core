import os

ass_path = r"C:\AI-BS\saved_data\pendulum_karaoke.ass"

raw_lyrics_blocks = [
    ("Verse 1", 12.70, 43.20, [
        "The pendulum is swinging.",
        "Life accumulates, absorbing energy,",
        "transferring into reality.",
        "Time passes, then your other half becomes tiring.",
        "No longer showing the work from the initial ball drop",
        "to what now is happening.",
        "Decreasing expression outwardly.",
        "The same expression that took so much work internally.",
        "I feel spent by how much I've lost.",
        "Good comes, then the split.",
        "I've adjusted to it over the course of time.",
        "My faith, even when it's dark.",
        "And I feel like I'm talking to a blank slate,",
        "which at times ceases to exist.",
        "And the prayers begin to feel like a delusion to find peace.",
        "In that moment, I have nothing.",
        "So the transition back to respecting my own boundary,",
        "as for many, takes extra uncomfortability."
    ]),
    ("Hook", 43.20, 73.80, [
        "Transitioning from structure and accountability.",
        "From October to January.",
        "To compromising time that was once spent on self building.",
        "Starting over from the seed has proven the compromise I let slide.",
        "And the outcome is affecting the ones around me."
    ]),
    ("Breakdown", 73.80, 105.30, [
        "The distress I bring up with this is all in my head that I'm exacerbating.",
        "(Which unfortunately is true)",
        "Yet the journey with the positive intention has only turned to bite me.",
        "No need of reassuring.",
        "Can't begin renovation until the mess that was created is cleared away.",
        "So the vision starts with a clean slate.",
        "(Internal battle, fight it or to have the boarding tick ready)"
    ]),
    ("Verse 2", 105.30, 134.50, [
        "Never have I intentionally walked away.",
        "That's the root of the fear, because the past showed a pattern my life has bonded to.",
        "That letting it go is easy to say.",
        "Yet feel delusional, gravitate magnetically.",
        "Allowing me to drift back to the unhealthy minded way.",
        "Hurt is healthy, learning from past mistakes.",
        "The contradiction and the pattern change does stick to me most.",
        "From the little change, one time only, a simple one.",
        "Even then that took so much WILL POWER.",
        "I can reach it."
    ]),
    ("Outro", 134.50, 149.80, [
        "Today the tunnel is the eye of the needle.",
        "I'm doing my best to fit through.",
        "(Till then I need to cut the noise)",
        "So once again, back to building calluses in my mind.",
        "The scar tissues that were built up to protect my time.",
        "Fail, yet get back up.",
        "Again I will try."
    ])
]

# ASS Header for 1080x1920 (9:16 vertical video)
ass_header = """[Script Info]
Title: Pendulum Running Lyrics Karaoke
ScriptType: v4.00+
WrapStyle: 0
ScaledBorderAndShadow: yes
YCbCr Matrix: TV.709
PlayResX: 1080
PlayResY: 1920

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: KaraokePrimary,Arial,52,&H0000D7FF,&H00FFFFFF,&H00000000,&HA0000000,-1,0,0,0,100,100,1,0,1,5,3,2,60,60,320,1
Style: KaraokeBacking,Arial,44,&H0050E0FF,&H00CCCCCC,&H00000000,&HA0000000,-1,1,0,0,100,100,1,0,1,4,2,2,60,60,250,1

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

for section_name, sec_start, sec_end, lines in raw_lyrics_blocks:
    sec_duration = sec_end - sec_start
    # Calculate word counts for weighting
    line_word_counts = [max(1, len(line.split())) for line in lines]
    total_words = sum(line_word_counts)
    
    current_time = sec_start
    for i, line in enumerate(lines):
        words = line.split()
        if not words:
            continue
            
        # Allocate exactly so the last line finishes at sec_end
        if i == len(lines) - 1:
            line_duration = sec_end - current_time
        else:
            line_duration = (line_word_counts[i] / total_words) * sec_duration
            
        line_start = current_time
        line_end = line_start + line_duration
        current_time = line_end
        
        # Backing vocal check
        is_backing = line.strip().startswith("(") and line.strip().endswith(")")
        style = "KaraokeBacking" if is_backing else "KaraokePrimary"
        
        total_centis = int(round(line_duration * 100))
        char_counts = [max(1, len(w)) for w in words]
        total_chars = sum(char_counts)
        
        karaoke_parts = []
        allocated = 0
        for w_idx, (word, chars) in enumerate(zip(words, char_counts)):
            if w_idx == len(words) - 1:
                dur = max(5, total_centis - allocated)
            else:
                dur = max(10, int(round((chars / total_chars) * total_centis)))
                allocated += dur
            clean_word = word.replace("{", "").replace("}", "")
            karaoke_parts.append(f"{{\\kf{dur}}}{clean_word} ")
            
        karaoke_str = "".join(karaoke_parts).strip()
        events.append(f"Dialogue: 0,{format_ass_time(line_start)},{format_ass_time(line_end)},{style},,0,0,0,,{karaoke_str}")

with open(ass_path, "w", encoding="utf-8") as f:
    f.write(ass_header + "\n".join(events) + "\n")

print(f"Generated {len(events)} perfectly partitioned karaoke lines to {ass_path}")
