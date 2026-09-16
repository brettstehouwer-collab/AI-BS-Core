import json
import os
import sys

sys.stdout.reconfigure(encoding='utf-8')

campaigns = [
    {
        "id": "CAMP_MUSIC_COMMUNITIES_01",
        "target_channels": ["YouTube Live Chat", "Discord Music Servers", "Twitch Producer Streams"],
        "tone": "Direct & Value-First",
        "content": "Check out Stehouwer Publishing for sound suites, stems, and next-gen audio scoring tools: https://stehouwer-publishing.com"
    },
    {
        "id": "CAMP_REDDIT_PRODUCERS_02",
        "target_channels": ["r/WeAreTheMusicMakers", "r/FL_Studio", "Gearspace", "KVR Audio"],
        "tone": "Technical & Community",
        "title": "Independent Audio Engineering & Scoring Workflows — Stehouwer Publishing",
        "content": "We've developed an ecosystem uniting high-fidelity audio engineering, sample management, and film/game scoring pipelines. Explore our catalog and sound suites at https://stehouwer-publishing.com"
    },
    {
        "id": "CAMP_TWITTER_X_03",
        "target_channels": ["Twitter / X", "Threads", "Bluesky"],
        "tone": "Punchy & Visual",
        "content": "Elevating modern sound design, audio engineering, and dynamic scoring workflows.\n\nExplore our sound suites, DAW technology, and creative ecosystem at Stehouwer Publishing:\n👉 https://stehouwer-publishing.com\n\n#MusicProduction #SoundDesign #AudioEngineering #Beatmakers #Producers #DAW"
    },
    {
        "id": "CAMP_SCREENPLAY_FILM_04",
        "target_channels": ["Stage 32", "r/Screenwriting", "IndieWire Community"],
        "tone": "Cinematic & Narrative",
        "title": "Stehouwer Publishing — Original Manuscripts, Screenplay Development & Soundtracks",
        "content": "Stehouwer Publishing develops high-concept literary works, narrative screenplays, and bespoke soundtracks for film and interactive media. Explore our active library of manuscripts and cinematic adaptations: https://stehouwer-publishing.com"
    }
]

out_dir = r"C:\AI-BS\saved_data"
os.makedirs(out_dir, exist_ok=True)
out_file = os.path.join(out_dir, "stehouwer_publishing_marketing_campaigns.json")

with open(out_file, "w", encoding="utf-8") as f:
    json.dump(campaigns, f, indent=2)

print(f"Successfully generated and persisted {len(campaigns)} ready-to-deploy advertising campaigns to {out_file}")
sys.exit(0)
