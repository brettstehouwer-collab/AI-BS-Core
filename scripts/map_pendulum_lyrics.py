import json

# Read the transcription segments
with open(r"C:\AI-BS\saved_data\facebook_reel_transcription.json", "r", encoding="utf-8") as f:
    data = json.load(f)

segments = data["segments"]
print(f"Total audio segments: {len(segments)}")

verse1_lines = [
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
]

hook_lines = [
    "Transitioning from structure and accountability.",
    "From October to January.",
    "To compromising time that was once spent on self building.",
    "Starting over from the seed has proven the compromise I let slide.",
    "And the outcome is affecting the ones around me."
]

breakdown_lines = [
    "The distress I bring up with this is all in my head that I'm exacerbating.",
    "(Which unfortunately is true)",
    "Yet the journey with the positive intention has only turned to bite me.",
    "No need of reassuring.",
    "Can't begin renovation until the mess that was created is cleared away.",
    "So the vision starts with a clean slate.",
    "(Internal battle, fight it or to have the boarding tick ready)"
]

verse2_lines = [
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
]

outro_lines = [
    "Today the tunnel is the eye of the needle.",
    "I'm doing my best to fit through.",
    "(Till then I need to cut the noise)",
    "So once again, back to building calluses in my mind.",
    "The scar tissues that were built up to protect my time.",
    "Fail, yet get back up.",
    "Again I will try."
]

all_sections = [
    ("Verse 1", 12.7, 43.2, verse1_lines),
    ("Hook", 43.2, 73.8, hook_lines),
    ("Breakdown", 73.8, 105.3, breakdown_lines),
    ("Verse 2", 105.3, 134.5, verse2_lines),
    ("Outro", 134.5, 149.8, outro_lines)
]

for name, s_start, s_end, lines in all_sections:
    print(f"\n--- {name} ({s_start:.1f}s -> {s_end:.1f}s, duration {s_end - s_start:.1f}s, {len(lines)} lines) ---")
    dur_per_line = (s_end - s_start) / len(lines)
    for i, line in enumerate(lines):
        t0 = s_start + i * dur_per_line
        t1 = t0 + dur_per_line
        print(f"  [{t0:.2f} -> {t1:.2f}] {line}")
