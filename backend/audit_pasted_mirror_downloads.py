import os
import re

pasted_items = [
    ("EQC1A (EQC-1A Win Installer)", "Cymatics EQC-1A Installer 1.1.0 (PC).exe", ["eqc-1a", "eqc1a"]),
    ("Atomic - Dubstep Sample Pack", "CymaticsAtomicDubstepSamplePack-V1-v7c.zip", ["atomic", "dubstep"]),
    ("Zodiac Platinum Expansion", "Zodiac Platinum Expansion", ["zodiac", "platinum"]),
    ("DARK SKY - Granular FX Engine", "DARK SKY - Granular FX Engine", ["dark", "sky"]),
    ("Deja Vu - FX Plugin", "Cymatics Deja Vu", ["deja", "vu"]),
    ("NC-73 (NV-73 Win Installer)", "Cymatics NV73 Installer 1.1.0 (PC).exe", ["nv73", "nv-73", "nc-73"]),
    ("Cavern - Melodic One Shots", "Cymatics-Cavern-MelodicOneShots.zip", ["cavern"]),
    ("Rift - Tonal Ambience", "Cymatics - Rift Tonal Ambience", ["rift"]),
    ("Lethal - 808 Samples", "Cymatics - Lethal 808s", ["lethal"]),
    ("Mirage - Lofi One Shots", "Cymatics - Mirage Lofi One Shot Collection", ["mirage"]),
    ("Tsunami - House Sample Pack", "CymaticsTsunamiHouseSamplePack-V1-b2k.zip", ["tsunami"]),
    ("Diamonds – Hip Hop Samples", "Diamonds – Hip Hop Samples", ["diamonds"]),
    ("2023 - 808 Collection", "Cymatics - 2023 808 Collection", ["2023", "808"]),
    ("Pharaoh - Beta Pack", "Cymatics-PHARAOH-BetaPack.zip", ["pharaoh"]),
    ("Dream Cassette", "Dream Cassette", ["dream", "cassette"]),
    ("DESTINY - Production Suite", "Cymatics-DESTINY-ProductionSuite.zip", ["destiny", "production"]),
    ("Duality - Vintage Melodies", "Cymatics-Duality-VintageMelodies.zip", ["duality", "vintage"]),
    ("Trinity - Wet Percussion", "Cymatics-Trinity-WetPercussionCollection.zip", ["trinity", "wet"]),
    ("DOPE Collection - Melodies", "StevenCymatics-DOPESamples.zip", ["dope", "samples"]),
    ("DOPE Collection - Bonus Stash", "StevenCymatics-DOPEBonusPack.zip", ["dope", "bonus"]),
    ("DOPE Collection - Vocals", "StevenCymatics-DOPEVocals.zip", ["dope", "vocals"]),
    ("DOPE Collection - Drums", "StevenCymatics-DOPEDrums.zip", ["dope", "drums"]),
    ("Kingdom: Electronic MIDI Collection", "Cymatics - Kingdom Electronic MIDI Collection", ["kingdom"]),
    ("Generations - 1960s Premium Samples", "Cymatics Generations 1960s", ["generations", "1960"]),
    ("Generations - 1970s Premium Samples", "Cymatics Generations 1970s", ["generations", "1970"]),
    ("SESSIONS: Melody Compositions", "Cymatics - Sessions Melody Compositions", ["sessions"]),
    ("Terra - Trap Melodies", "Cymatics-Terra-TrapMelodies.zip", ["terra"]),
    ("Euphoria - Vocal Chops", "Cymatics-EUPHORIA_VocalChops_.zip", ["euphoria"]),
    ("Solace - Acapellas", "Cymatics-SOLACE_Acapellas_.zip", ["solace"]),
    ("Duality - Ambient Melodies", "Cymatics-Duality-AmbientMelodies.zip", ["duality", "ambient"]),
    ("Exodus - Various Drums", "Cymatics-Exodus-VariousDrums.zip", ["exodus", "drums"]),
    ("Trinity: Melody Collection", "Cymatics-Trinity-MelodyLoopsCollection.zip", ["trinity", "melody"]),
    ("Destiny - Analog Melodies", "Cymatics-DESTINY-AnalogMelodies.zip", ["destiny", "analog"]),
    ("Ripple - Pop Guitars", "Cymatics-Ripple-PopCollection.zip", ["ripple"]),
    ("Evolution - Guitar Melodies", "Cymatics-Evolution-GuitarMelodies.zip", ["evolution"]),
    ("Octagon - Don Toliver Pack", "Cymatics-OCTAGON-ArtistPack.zip", ["octagon"]),
    ("Trinity - MIDI Collection", "Cymatics-Trinity-MIDICollection.zip", ["trinity", "midi"]),
    ("Phalanx - 808 & Bass", "Cymatics-Phalanx-808s&Bass.zip", ["phalanx"]),
    ("BOOM’N - Drum Loops", "Cymatics-BOOM'N-DrumLoops.zip", ["boom", "drum"]),
    ("BOOM'N - Melodies", "Cymatics-BOOM'N-MelodyLoops.zip", ["boom", "melody"]),
    ("Whisper - Melody Collection", "Cymatics-Whisper-MelodyLoops.zip", ["whisper"]),
    ("Cascade - Vocal Loops", "Cymatics - Cascade Vocal Loops", ["cascade"]),
    ("Daydream - Vocal Loops", "Cymatics-DAYDREAM_VocalLoops_.zip", ["daydream"]),
    ("Exodus - Various Melodies", "Cymatics-Exodus-VariousMelodies.zip", ["exodus", "melodies"]),
    ("Casino - Baby Keem Inspired Pack", "Cymatics-CASINO-ArtistPack.zip", ["casino"]),
    ("Apocalypse - Launch Edition - Offer", "Apocalypse - Launch Edition - Offer", ["apocalypse"]),
    ("Chili Clip (Chili Clipper)", "Cymatics Chili Clipper", ["chili"]),
    ("HOTLINE", "Cymatics Hotline", ["hotline"]),
    ("GAMMA Lite", "Cymatics Gamma", ["gamma"]),
    ("RADAR", "Cymatics Radar", ["radar"]),
    ("PRISM", "Cymatics Prism", ["prism"]),
    ("OCCULAR", "Cymatics Occular", ["occular"]),
    ("HORIZON", "Cymatics Horizon", ["horizon"]),
    ("MIDI Shredder", "Cymatics MIDI Shredder", ["midi", "shredder"]),
    ("CRT Plugin", "Cymatics CRT", ["crt"])
]

e_folders = [f for f in os.listdir("E:\\")] if os.path.exists("E:\\") else []
docs_files = [f for f in os.listdir(r"C:\AI-BS\docs")] if os.path.exists(r"C:\AI-BS\docs") else []
vst3_plugins = [f for f in os.listdir(r"C:\Program Files\Common Files\VST3")] if os.path.exists(r"C:\Program Files\Common Files\VST3") else []
cache_files = [f for f in os.listdir(r"C:\Users\footb\AppData\Roaming\Cymatics Hub\installer-cache")] if os.path.exists(r"C:\Users\footb\AppData\Roaming\Cymatics Hub\installer-cache") else []

all_searched = []

for title, sample_fn, kws in pasted_items:
    found_locations = []
    
    # 1. Check E:\
    for ef in e_folders:
        if all(k in ef.lower().replace('–', '-').replace('—', '-') for k in kws):
            found_locations.append(f"E:\\{ef}")
            
    # 2. Check C:\AI-BS\docs
    for df in docs_files:
        if all(k in df.lower() for k in kws):
            found_locations.append(f"C:\\AI-BS\\docs\\{df}")
            
    # 3. Check VST3
    for vf in vst3_plugins:
        if all(k in vf.lower() for k in kws):
            found_locations.append(f"VST3: {vf}")
            
    # 4. Check installer cache
    for cf in cache_files:
        if all(k in cf.lower() for k in kws):
            found_locations.append(f"Cache: {cf}")

    all_searched.append({
        "title": title,
        "found": len(found_locations) > 0,
        "locations": list(set(found_locations))
    })

print("================================================================")
print("       MIRROR HUB DOWNLOADS CROSS-CHECK AUDIT (E:\\ & DOCS)     ")
print("================================================================")

found_cnt = len([s for s in all_searched if s['found']])
missing_cnt = len([s for s in all_searched if not s['found']])

print(f"Total Mirror Hub Items Audited: {len(all_searched)}")
print(f"Verified on E:\\ / Docs / VST:   {found_cnt} of {len(all_searched)} ({round(found_cnt/len(all_searched)*100, 1)}%)")
print(f"Missing from Local Storage:     {missing_cnt} of {len(all_searched)}")
print("================================================================\n")

print("--- VERIFIED ON DISK ---")
for s in all_searched:
    if s['found']:
        loc_str = " | ".join(s['locations'][:2])
        print(f"  [FOUND] {s['title']} -> {loc_str}")

if missing_cnt > 0:
    print("\n--- MISSING FROM DISK ---")
    for s in all_searched:
        if not s['found']:
            print(f"  [MISSING] {s['title']}")
