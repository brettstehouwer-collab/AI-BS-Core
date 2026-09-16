import os

paths = [
    r"E:\AI_BS_Resources",
    r"E:\Zodiac III - Melodies Vol 3",
    r"E:\Cymatics - Rattle Hip Hop Drum Frameworks",
    r"E:\Zodiac III - Melodies Vol 4",
    r"E:\Zodiac - Melodies - RnB",
    r"E:\Cymatics - Inferno Drum Loops",
    r"E:\Cymatics - PHARAOH - Beta Pack",
    r"E:\Cymatics - 2023 808 Collection",
    r"E:\Diamonds – Hip Hop Samples",
    r"E:\Cymatics - Tsunami House Sample Pack",
    r"E:\Cymatics - Mirage Lofi One Shot Collection",
    r"E:\Cymatics - Rift Tonal Ambience",
    r"E:\Cymatics - Lethal 808s",
    r"E:\Cymatics - Atomic Dubstep Sample Pack",
    r"E:\Zodiac Platinum Expansion",
    r"E:\Cymatics - Cavern - Melodic One Shots",
    r"E:\DARK SKY - Granular FX Engine",
    r"E:\Cymatics - DESTINY - Production Suite",
    r"E:\Cymatics - Duality - Vintage Melodies",
    r"E:\Cymatics - Kingdom Electronic MIDI Collection",
    r"E:\Cymatics Generations 1960s",
    r"E:\Cymatics Generations 1970s",
    r"E:\Cymatics - Sessions Melody Compositions",
    r"E:\Steven Cymatics - DOPE Samples",
    r"E:\Steven Cymatics - DOPE Drums",
    r"E:\Steven Cymatics - DOPE Vocals",
    r"E:\Steven Cymatics - DOPE Bonus Pack",
    r"E:\Cymatics - SOLACE (Acapellas)",
    r"E:\Cymatics - EUPHORIA (Vocal Chops)",
    r"E:\Cymatics - Duality - Ambient Melodies",
    r"E:\Cymatics - Trinity - Melody Loops Collection",
    r"E:\Cymatics - Trinity - Wet Percussion Collection",
    r"E:\SteamLibrary",
    r"E:\Recordings",
    r"E:\Cymatics - DESTINY - Analog Melodies",
    r"E:\Cymatics - Ripple - Pop Collection",
    r"E:\Cymatics - Evolution - Guitar Melodies",
    r"E:\Cymatics - BOOM'N - Drum Loops",
    r"E:\Cymatics - Exodus - Various Melodies",
    r"E:\Cymatics - Exodus - Various Drums",
    r"E:\Cymatics - Whisper - Melody Loops",
    r"E:\Cymatics - Terra - Trap Melodies",
    r"E:\Cymatics - HERITAGE (Vintage Melodies)",
    r"E:\Cymatics - FUGITIVE (Trap Melodies)",
    r"E:\Cymatics - CASHMERE (RnB Melodies)",
    r"E:\Cymatics - BOOM'N - Melody Loops",
    r"E:\Cymatics - Cascade Vocal Loops",
    r"E:\Cymatics - DAYDREAM (Vocal Loops)",
    r"E:\Cymatics - CASINO - Artist Pack",
    r"E:\Cymatics - OCTAGON - Artist Pack",
    r"E:\Cymatics - Trinity - MIDI Collection",
    r"E:\Apocalypse - Launch Edition - Offer",
    r"E:\Cymatics - Phalanx - 808s & Bass",
    r"E:\Cymatics",
    r"E:\_test_junction_dst"
]

verified_on_disk = []
missing_on_disk = []

for p in paths:
    if os.path.exists(p):
        verified_on_disk.append(p)
    else:
        # Check unicode variations like dash or quotes
        parent = os.path.dirname(p)
        base = os.path.basename(p)
        found = False
        if os.path.exists(parent):
            for f in os.listdir(parent):
                if f.lower().replace('–', '-').replace('—', '-').strip() == base.lower().replace('–', '-').replace('—', '-').strip():
                    verified_on_disk.append(os.path.join(parent, f))
                    found = True
                    break
        if not found:
            missing_on_disk.append(p)

print(f"Total Paths Checked: {len(paths)}")
print(f"Verified Existing on Disk: {len(verified_on_disk)}")
print(f"Missing: {len(missing_on_disk)}")

# Check DAW junction count
daw_junctions_dir = r"C:\AI-BS\shared_cloud_drive\4 media\Cymatics_Sample_Packs"
daw_count = len(os.listdir(daw_junctions_dir)) if os.path.exists(daw_junctions_dir) else 0
print(f"Total Audio Suites Junctioned into DAW Media Vault: {daw_count}")
