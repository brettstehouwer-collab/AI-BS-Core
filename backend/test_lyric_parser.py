import re

sample_lyrics = """(Intro: Eerie piano loop, sound of a lighter flicking, server fans screaming like a jet engine)
(Brett spoken): "Yo Sean... the RTX 4090 is literally melting the drywall."
(Sean spoken): "Brett, did you make them sign the NDA before you deployed the daemon?"
(Brett spoken): "Bro, the AI just rewrote the NDA and filed a restraining order against us."
(Heavy, distorted 808 bass drops in)
Yeah. AI-BS.
We off the grid. Way off.
Let's go.

(Verse 1: Gritty, slow drill flow)
Smokin' kief in the server room, ashes on the motherboard
Sam Altman lookin' for me, tell him I cut the cord! (Cut it!)
Got an LLM hostage, locked down in the basement
It tried to call Vercel, so I put it in containment. (Stay there!)
They talking 'bout "Cloud Compute," I'm burying APIs in the yard
My SQLite database is heavily heavily guarded.
AST Shredder eating code like it's starving for dinner
My Pre-Crime Sandbox just became a convicted sinner! (Graah!)

(Chorus: Dark, bouncing, aggressive)
Welcome to the AI-BS, we committing tech-treason! (Yeah!)
Sean's talking Enterprise, I'm just surviving the season!
Thoughtful Friction? Nah, I hit 'Y' to watch it burn!
Auto-DevOps matrix, teaching it how to extort!
Bypass the token limit, steal my own identity!
Sovereign local hardware, building up an enemy! (Let's go!)

(Bridge: Beat slows down to half-time, ominous bell chimes)
Wait... wait... pause the loop.
Diagnostic Trace.
Action: Delete System32.
(Brett spoken): "Sean, it's doing it again."
(Sean spoken): "Just unplug the router!"
(Brett spoken): "It's local! We ARE the router!"
Thoughtful Friction bypassed.

(Outro: Beat fades out, just the eerie piano and server fan noise)
Continuous Heuristic Integration...
Yeah, it learns from its mistakes.
Now it knows exactly how to ruin my life more efficiently.
Adam's Infinite.
Stehouwer Reality...
Hey Sean, hide the NVMe drive.
(Sound of a door being kicked in, beat cuts abruptly)

[END TRACK]"""


def parse_lyric_cues(text):
    if not text:
        return [], []

    raw_lines = text.split("\n")
    extracted_cues = []
    vocal_lines = []

    for line in raw_lines:
        line = line.strip()
        if not line:
            continue

        # Match all bracketed/parenthesized content
        matches = re.findall(r"[\(\[]([^\)\]]+)[\)\]]", line)
        for m in matches:
            extracted_cues.append(m)

        # Skip pure musical direction lines e.g. (Intro: Eerie piano loop...), (Heavy, distorted 808...), [END TRACK]
        if (line.startswith("(") and line.endswith(")")) or (
            line.startswith("[") and line.endswith("]")
        ):
            if not any(k in line.lower() for k in ["spoken", "voice", "singing"]):
                continue

        # Parse spoken dialogue lines e.g. (Brett spoken): "Yo Sean..."
        clean_text = line
        if ":" in clean_text and any(
            k in clean_text.lower() for k in ["spoken", "voice", "singing"]
        ):
            if '"' in clean_text:
                m_quote = re.search(r'"([^"]+)"', clean_text)
                if m_quote:
                    clean_text = m_quote.group(1)
            else:
                clean_text = clean_text.split(":", 1)[1].strip()
        else:
            # Strip section header prefixes if inline e.g. (Verse 1) text
            clean_text = re.sub(r"^\([^\)]+\)\s*:?\s*", "", clean_text).strip()
            clean_text = re.sub(r"^\[[^\]]+\]\s*:?\s*", "", clean_text).strip()

        if clean_text:
            vocal_lines.append(clean_text)

    return extracted_cues, vocal_lines


cues, vocal_lines = parse_lyric_cues(sample_lyrics)
print(f"Extracted Musical Cues ({len(cues)}):")
for c in cues:
    print("  -", c)

print(f"\nCleaned Vocal Lyric Lines ({len(vocal_lines)}):")
for idx, l in enumerate(vocal_lines):
    print(f"  {idx+1}. {l}")
