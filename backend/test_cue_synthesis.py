import sys, os

sys.path.insert(0, r"C:\AI-BS\backend")
from dynamic_audio_generator import generate_dynamic_song

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

url, calc_dur = generate_dynamic_song(
    prompt="AI-BS Tech Treason Drill Track with Spoken Dialogue and Beat Drops",
    genre="hiphop",
    duration_sec=0,
    lyrics=sample_lyrics,
    tempo_bpm=130,
    vocal_style="lead",
    arrangement="verse_chorus",
)

print("=== CUE PARSING AUDIO SYNTHESIS SUCCESS ===")
print("Generated Track URL:", url)
print("Calculated Song Duration:", calc_dur, "seconds")
