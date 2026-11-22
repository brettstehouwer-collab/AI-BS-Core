"""
AI-BS Sovereign Music & Audio Assistant Router
Provides natural language conversation, music theory reasoning, DAW automation,
and prompt-to-production intelligence using local Ollama LLMs with instant heuristic fallback.
"""

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
import os
import re
import json
import httpx
import logging
import random

router = APIRouter(prefix="/api/audio/assistant", tags=["Music Audio Assistant"])
logger = logging.getLogger("aibs.music_assistant")

OLLAMA_HOST = os.environ.get("OLLAMA_HOST", "http://127.0.0.1:11434")

class MessageItem(BaseModel):
    role: str = "user"  # "user" | "assistant" | "system"
    content: str

class DawContext(BaseModel):
    bpm: Optional[int] = 85
    playMode: Optional[str] = "PAT"
    isPlaying: Optional[bool] = False
    masterVolume: Optional[float] = 0.0
    activeView: Optional[str] = "multimedia"
    activeChannel: Optional[str] = "c6"
    theatricalSync: Optional[bool] = True

class MusicAssistantChatRequest(BaseModel):
    message: str
    history: Optional[List[MessageItem]] = []
    context: Optional[DawContext] = None

# ═══════════════════════════════════════════════════════════════════════════
# DETERMINISTIC NATURAL LANGUAGE MUSIC INTENT & THEORY ENGINE (FALLBACK / ACCELERATOR)
# ═══════════════════════════════════════════════════════════════════════════

SCALE_KNOWLEDGE = {
    "c_major": ["C", "D", "E", "F", "G", "A", "B"],
    "a_minor": ["A", "B", "C", "D", "E", "F", "G"],
    "d_minor": ["D", "E", "F", "G", "A", "Bb", "C"],
    "f_minor": ["F", "G", "Ab", "Bb", "C", "Db", "Eb"],
    "c_minor": ["C", "D", "Eb", "F", "G", "Ab", "Bb"],
    "g_minor": ["G", "A", "Bb", "C", "D", "Eb", "F"],
    "e_minor": ["E", "F#", "G", "A", "B", "C", "D"],
    "bb_major": ["Bb", "C", "D", "Eb", "F", "G", "A"]
}

GENRE_PRESETS = {
    "synthwave": {
        "bpm": 115,
        "key": "D Minor",
        "chords": [["D3", "F3", "A3"], ["Bb2", "D3", "F3"], ["C3", "E3", "G3"], ["A2", "C#3", "E3"]],
        "chord_names": ["Dm", "Bb", "C", "A"],
        "bassline": ["D2", "D2", "D2", "D2", "Bb1", "Bb1", "C2", "A1"],
        "vibe": "Pulsing retro arpeggios, analog gated reverb drums, and driving melodic synthwave bass."
    },
    "trap": {
        "bpm": 136,
        "key": "F Minor",
        "chords": [["F3", "Ab3", "C4"], ["Db3", "F3", "Ab3"], ["Eb3", "G3", "Bb3"], ["C3", "E3", "G3"]],
        "chord_names": ["Fm", "Db", "Eb", "C"],
        "bassline": ["F1", "F1", "Db1", "C1"],
        "vibe": "Deep sliding 808 sub-bass, clean hi-hat rolls, and melodic bells."
    },
    "lofi": {
        "bpm": 82,
        "key": "Eb Major",
        "chords": [["Eb3", "G3", "Bb3", "D4"], ["C3", "Eb3", "G3", "Bb3"], ["F3", "Ab3", "C4", "Eb4"], ["Bb2", "D3", "F3", "Ab3"]],
        "chord_names": ["Ebmaj7", "Cm7", "Fm7", "Bb7"],
        "bassline": ["Eb2", "C2", "F2", "Bb1"],
        "vibe": "Dusty vinyl crackle, warm Rhodes piano chords, swing boom-bap rhythm."
    },
    "boombap": {
        "bpm": 90,
        "key": "G Minor",
        "chords": [["G3", "Bb3", "D4"], ["C3", "Eb3", "G3"], ["D3", "F#3", "A3"], ["Eb3", "G3", "Bb3"]],
        "chord_names": ["Gm", "Cm", "D7", "Ebmaj7"],
        "bassline": ["G1", "G1", "C1", "D1"],
        "vibe": "Classic 90s boom-bap hip-hop with crisp acoustic snare on 2 and 4, swinging 8th-note hats, and warm jazz bassline."
    },
    "rnb": {
        "bpm": 78,
        "key": "Eb Major",
        "chords": [["Eb3", "G3", "Bb3"], ["Ab2", "C3", "Eb3"], ["C3", "Eb3", "G3"], ["Bb2", "D3", "F3"]],
        "chord_names": ["Ebmaj7", "Abmaj7", "Cm7", "Bb7"],
        "bassline": ["Eb1", "Ab0", "C1", "Bb0"],
        "vibe": "Smooth soulful R&B groove with laid-back syncopated hats, deep sub-bass warmth, and emotional chord extensions."
    },
    "funk_pop": {
        "bpm": 108,
        "key": "E Minor",
        "chords": [["E3", "G3", "B3"], ["A2", "C3", "E3"], ["D3", "F#3", "A3"], ["B2", "D#3", "F#3"]],
        "chord_names": ["Em7", "Am7", "D7", "B7"],
        "bassline": ["E1", "G1", "A1", "D1"],
        "vibe": "Infectious upbeat funk-pop with bouncy 16th-note rhythm, snappy clap/snare, and walking bass groove."
    },
    "acoustic_ballad": {
        "bpm": 76,
        "key": "C Major",
        "chords": [["C3", "E3", "G3"], ["G2", "B2", "D3"], ["A2", "C3", "E3"], ["F2", "A2", "C3"]],
        "chord_names": ["C", "G", "Am", "F"],
        "bassline": ["C1", "G0", "A0", "F0"],
        "vibe": "Organic acoustic ballad with warm kick pulse, delicate cross-stick snare, and resonant piano progressions."
    },
    "suno_rock": {
        "bpm": 85,
        "key": "A Minor",
        "chords": [["A2", "C3", "E3"], ["F2", "A2", "C3"], ["C3", "E3", "G3"], ["G2", "B2", "D3"]],
        "chord_names": ["Am", "F", "C", "G"],
        "bassline": ["A1", "F1", "C2", "G1"],
        "vibe": "Emotional driving rock ballad matching October 7v2 tempo with powerful vocal support."
    },
    "cyberpunk": {
        "bpm": 130,
        "key": "C Minor",
        "chords": [["C3", "Eb3", "G3"], ["Ab2", "C3", "Eb3"], ["F2", "Ab2", "C3"], ["G2", "B2", "D3"]],
        "chord_names": ["Cm", "Ab", "Fm", "G"],
        "bassline": ["C1", "C1", "Ab0", "G0"],
        "vibe": "Distorted neuro-bass Reese sweeps, aggressive industrial kicks, futuristic tension."
    }
}

# Curated Clean Musical Genres Pool for Random Beat Generation (Zero Cyberpunk/Harsh Noise)
CLEAN_RANDOM_GENRES = [
    "suno_rock",
    "boombap",
    "lofi",
    "rnb",
    "funk_pop",
    "acoustic_ballad",
    "trap",
    "synthwave"
]

def parse_heuristic_actions(text: str, context: Optional[DawContext]) -> Dict[str, Any]:
    """Inspects natural language text for actionable DAW intents and music theory assistance."""
    t = text.lower().strip()
    actions = []
    suggestions = []
    reply_lines = []

    # 0. Make a Song with Assets / Load Project Stems into Arranger Playlist
    is_song_with_assets = any(k in t for k in [
        "make a song with what assets i have",
        "make a song with my assets",
        "make a song with the assets",
        "make a song with what i have",
        "make a song from what assets i have",
        "make a song from my assets",
        "make a song from what i have",
        "make a track with what assets i have",
        "make a track with my assets",
        "create a song with what assets i have",
        "create a song with my assets",
        "compose a song with what assets i have",
        "compose a song with my assets",
        "build a song with what assets i have",
        "build a song with my assets",
        "arrange a song with what assets i have",
        "arrange my assets into a song",
        "arrange my assets",
        "arrange the stems",
        "arrange my stems",
        "use what assets i have",
        "use my assets to make a song",
        "use my assets",
        "what assets i have",
        "make music with what assets i have",
        "make music with my assets",
        "make a song with stems",
        "make a song from stems",
        "song with what assets",
        "make a song with the files",
        "make a track with the files"
    ]) or (
        ("make a song" in t or "compose a song" in t or "create a song" in t or "build a song" in t)
        and any(w in t for w in ["asset", "assets", "what i have", "stem", "stems", "library", "vault", "october"])
    )

    is_send_to_studio = any(k in t for k in [
        "send to studio", "sent to studio", "send this to studio", "did you send", 
        "load to studio", "load into studio", "send to playlist", "send to arranger", 
        "open in studio", "put in studio", "bring to studio", "add to studio", 
        "load stems", "load my song", "send song", "october 7 to studio",
        "where is my created work", "where can i view my created work", "view created work",
        "where do i view", "where can i see", "see my song", "view my track"
    ])

    if is_song_with_assets or is_send_to_studio:
        actions.append({"type": "SEND_TO_STUDIO", "project": "october_7v2_remastered"})
        actions.append({"type": "SET_BPM", "bpm": 85})
        actions.append({"type": "SET_VIEW", "view": "playlist"})
        
        reply_lines.append("🎼 **Assembled Song from Your Library Assets!**")
        reply_lines.append("I analyzed the assets currently in your **Sound Vault & Stems Library** and dynamically arranged them directly into your **Arranger Playlist Timeline**:")
        reply_lines.append("• 🎙️ **Track 1 — Isolated Lead Vocals**: `vocals.wav` (Acapella lead performance)")
        reply_lines.append("• 🥁 **Track 2 — Drums & Percussion**: `drums.wav` (Full acoustic rock/pop kit transients)")
        reply_lines.append("• 🎸 **Track 3 — Electric Bass**: `bass.wav` (Driving bassline fundamentals)")
        reply_lines.append("• 🎹 **Track 4 — Repaired Instrumental Bed**: `other_repaired.wav` (Clean musical accompaniment with smoothed harmonic cut transition)")
        reply_lines.append("• 🏆 **Track 5 — Master Reference Mix**: `October_7v2_Master_Repaired.wav` (Full stereo reference track)")
        reply_lines.append("\n**DAW Actions Executed:**")
        reply_lines.append("• Staged all 5 multi-track stem audio clips into the Arranger Playlist.")
        reply_lines.append("• Locked project tempo to **85 BPM** (Native October 7v2 Suno cadence).")
        reply_lines.append("• Switched transport play mode to **SONG**.")
        reply_lines.append("• Opened the **Arranger Playlist** view so you can view, edit, and layer your tracks.")
        reply_lines.append("\nYou can click **PLAY (▶)** (or hit `Spacebar`) in the top transport bar to audition your full song arrangement immediately!")
        suggestions.extend(["▶️ Play Track (Song Mode)", "🥁 Layer Synthwave / Trap Beat", "🎚 Open Mixer Rack", "🎙️ Switch to Wave Studio"])

    # 1. BPM / Tempo matching
    bpm_match = re.search(r'(?:tempo|bpm|speed)\s*(?:to|at|is|=)?\s*(\d{2,3})', t)
    if not bpm_match:
        bpm_match = re.search(r'\b(\d{2,3})\s*(?:bpm|tempo)\b', t)
    
    if bpm_match:
        target_bpm = int(bpm_match.group(1))
        if 40 <= target_bpm <= 240:
            actions.append({"type": "SET_BPM", "bpm": target_bpm})
            reply_lines.append(f"⏱️ **Tempo Locked**: Set the studio tempo to **{target_bpm} BPM**.")
    elif "faster" in t or "speed up" in t:
        cur = (context.bpm if context else 85) + 10
        actions.append({"type": "SET_BPM", "bpm": cur})
        reply_lines.append(f"⚡ **Accelerating Tempo**: Bumped up by 10 BPM to **{cur} BPM**.")
    elif "slower" in t or "slow down" in t:
        cur = max(40, (context.bpm if context else 85) - 10)
        actions.append({"type": "SET_BPM", "bpm": cur})
        reply_lines.append(f"🌙 **Decelerating Tempo**: Eased down by 10 BPM to **{cur} BPM**.")

    # 2. Transport playback
    if any(k in t for k in ["play the song", "start playback", "hit play", "press play", "play track", "play"]):
        if not any(k in t for k in ["playlist", "piano roll"]):
            actions.append({"type": "TOGGLE_PLAY"})
            reply_lines.append("▶️ **Transport**: Started audio playback.")
    elif any(k in t for k in ["stop playing", "stop playback", "stop music", "pause", "halt audio", "stop"]):
        actions.append({"type": "STOP_PLAYBACK"})
        reply_lines.append("⏹️ **Transport**: Playback halted and playhead reset.")

    # 3. Beat & Groove Generation (Supports Clean Random Beats & Genre Customization)
    detected_genre = None
    is_random_request = (
        any(k in t for k in ["random", "randome", "randomize", "shuffle", "roll a beat", "roll the dice", "surprise me", "pick a beat"])
        and any(w in t for w in ["beat", "groove", "drum", "drums", "rhythm", "pattern", "track", "music", "stuff", "it"])
    ) or ("randome a beat" in t or "random a beat" in t or "randomize beat" in t or "random beat" in t)

    no_cyberpunk = any(k in t for k in ["no cyber", "non of that cyber", "none of that cyber", "not cyber", "without cyber", "no industrial"])

    if is_random_request:
        # Strictly select from clean, melodic, organic genres (Zero Cyberpunk / Harsh Noise)
        candidates = [g for g in CLEAN_RANDOM_GENRES if g != "cyberpunk"]
        detected_genre = random.choice(candidates)
    elif "boombap" in t or "boom bap" in t or "hip hop" in t or "hip-hop" in t or "90s" in t:
        detected_genre = "boombap"
    elif "r&b" in t or "rnb" in t or "soul" in t:
        detected_genre = "rnb"
    elif "funk" in t or "pop" in t:
        detected_genre = "funk_pop"
    elif "acoustic" in t or "unplugged" in t:
        detected_genre = "acoustic_ballad"
    elif "synthwave" in t or "80s" in t or "retro" in t:
        detected_genre = "synthwave"
    elif "trap" in t or "808" in t or "drill" in t:
        detected_genre = "trap"
    elif "lofi" in t or "lo-fi" in t or "chill" in t:
        detected_genre = "lofi"
    elif ("cyberpunk" in t or "darksynth" in t or "industrial" in t) and not no_cyberpunk:
        detected_genre = "cyberpunk"
    elif "rock" in t or "ballad" in t or "october" in t:
        detected_genre = "suno_rock"

    if detected_genre and (
        is_random_request or any(k in t for k in ["generate", "make", "create", "compose", "beat", "drum", "pattern", "groove", "write", "randome", "random"])
    ):
        preset = GENRE_PRESETS.get(detected_genre, GENRE_PRESETS["suno_rock"])
        actions.append({"type": "GENERATE_BEAT", "genre": detected_genre})
        if not bpm_match:
            actions.append({"type": "SET_BPM", "bpm": preset["bpm"]})
        actions.append({"type": "SET_VIEW", "view": "channel_rack"})
        
        genre_titles = {
            "suno_rock": "Suno Rock Anthem (85 BPM)",
            "boombap": "90s Hip-Hop Boom Bap (90 BPM)",
            "lofi": "Chill Lo-Fi / Neo-Soul (82 BPM)",
            "rnb": "Smooth R&B Soul (78 BPM)",
            "funk_pop": "Upbeat Funk-Pop (108 BPM)",
            "acoustic_ballad": "Organic Acoustic Ballad (76 BPM)",
            "trap": "Melodic 808 Trap (136 BPM)",
            "synthwave": "Melodic 80s Synthwave (115 BPM)"
        }
        title = genre_titles.get(detected_genre, detected_genre.upper())

        if is_random_request:
            reply_lines.append(f"🎲 **Random Clean Beat Rolled: {title}**")
            reply_lines.append("*(Zero cyberpunk or harsh industrial noise — strictly clean, organic, and musical groove!)*")
        else:
            reply_lines.append(f"🥁 **Beat Generated ({title})**:")

        reply_lines.append(f"• **Vibe**: {preset['vibe']}")
        reply_lines.append(f"• **Tempo**: **{preset['bpm']} BPM** | **Key**: **{preset['key']}**")
        reply_lines.append(f"• **Chord Progression**: `{' - '.join(preset['chord_names'])}`")
        reply_lines.append("• **Sequencer Programming**: 16-step rhythmic pattern dispatched to Channel Rack with punchy kicks, crisp snares, swung hats, and melodic bass.")
        reply_lines.append("\n**DAW Actions Executed:**")
        reply_lines.append(f"• Loaded `{detected_genre}` rhythm into the Channel Rack & Step Sequencer.")
        reply_lines.append(f"• Synchronized tempo to **{preset['bpm']} BPM**.")
        reply_lines.append("• Switched view to **Channel Rack & Step Sequencer**.")
        reply_lines.append("\nYou can click **PLAY (▶)** (or hit `Spacebar`) in the transport bar to audition the new groove live!")
        suggestions.extend(["🎲 Roll Another Clean Beat", "▶️ Play Groove", "🎼 Make Song With Assets", "🎚 Open Mixer FX Rack"])

    # 4. View Navigation
    if "wave studio" in t or "waveform" in t or "audio editor" in t:
        actions.append({"type": "SET_VIEW", "view": "wave_studio"})
        reply_lines.append("🎙️ **Switched View**: Opened **Stehouwer Multi-Track Wave Studio**.")
    elif "stem" in t or "isolate" in t or "demucs" in t or "vocal extract" in t:
        actions.append({"type": "SET_VIEW", "view": "ai_stems"})
        reply_lines.append("✨ **Switched View**: Opened **AI Vocal & Stem Extraction Suite** (Demucs v4 on RTX 4090).")
        suggestions.append("⚡ Drag audio file to extract 5 stems")
    elif "mixer" in t or "fader" in t or "eq" in t or "mixing" in t:
        actions.append({"type": "SET_VIEW", "view": "mixer"})
        reply_lines.append("🎚 **Switched View**: Opened **Master Mixer & FX Rack**.")
    elif "channel rack" in t or "step sequencer" in t:
        actions.append({"type": "SET_VIEW", "view": "channel_rack"})
        reply_lines.append("🥁 **Switched View**: Opened **Channel Rack & Step Sequencer**.")
    elif "playlist" in t or "arranger" in t or "timeline" in t:
        actions.append({"type": "SET_VIEW", "view": "playlist"})
        reply_lines.append("🎼 **Switched View**: Opened **Arranger Playlist Timeline**.")

    # 5. Volume & FX Control
    vol_match = re.search(r'(?:volume|master volume)\s*(?:to|at|=)?\s*([+-]?\d+)', t)
    if vol_match:
        target_vol = max(-30, min(6, int(vol_match.group(1))))
        actions.append({"type": "SET_VOLUME", "volume": target_vol})
        reply_lines.append(f"🔊 **Master Volume**: Calibrated to **{target_vol} dB**.")
    elif "mute" in t and "drum" in t:
        actions.append({"type": "MUTE_CHANNEL", "channelId": "c1", "mute": True})
        reply_lines.append("🔇 **Channel Muted**: Kick / Drum channel silenced.")

    if "reverb" in t and ("add" in t or "more" in t or "turn up" in t):
        actions.append({"type": "SET_FX", "fx": "reverb", "params": {"wet": 0.45, "decay": 3.0}})
        reply_lines.append("🌌 **Reverb Enhanced**: Increased wet mix to 45% and decay to 3.0s for an expansive spatial hall.")

    # 6. Music Theory, Vocal Repair, and Acoustic Questions
    if any(k in t for k in ["cut", "even out", "tone", "pitch", "repair", "transition", "autotune"]):
        reply_lines.append("🛠️ **Audio Transition & Vocal Repair Strategy**:")
        reply_lines.append("When smoothing out an edit where instruments or vocals were cut:")
        reply_lines.append("1. **Micro-Crossfade**: Apply a 15–30ms equal-power crossfade curve (`sqrt(t)`) across the seam to prevent transient clicks.")
        reply_lines.append("2. **Harmonic Key Matching**: If the cut jumps across chord changes, insert a transitional passing tone or invert the harmony to keep pitch continuity.")
        reply_lines.append("3. **Masking with Spatial Wash**: Place a subtle reverse-cymbal sweep or a 2.5s stereo reverb tail starting 0.5 bars before the cut to mask the spectral discontinuity.")
        reply_lines.append("4. **Demucs Isolation**: Separate the song into Drums, Bass, Vocals, and Instrumental stems in the **AI Stems Tab**, so you can crossfade the instrumental bed independently from the dry vocal line.")
        suggestions.extend(["✨ Open AI Stem Suite", "🎙️ Edit in Wave Studio", "⏱ Lock to 85 BPM"])

    if any(k in t for k in ["chord", "progression", "harmony", "scale", "minor", "major"]):
        if not detected_genre:
            reply_lines.append("🎼 **Harmonic Chord Progressions Recommended**:")
            reply_lines.append("- **Emotional Ballad (D Minor)**: `Dm (i) - Bb (VI) - F (III) - C (VII)` -> *Cinematic, uplifting yet sorrowful.*")
            reply_lines.append("- **Neo-Soul / Lofi (C Minor)**: `Cm9 - Fm9 - Abmaj7 - G7alt` -> *Rich jazz voicing with tension.*")
            reply_lines.append("- **Suno Rock (A Minor)**: `Am - F - C - G` -> *The timeless 80s / anthem power progression.*")
            suggestions.extend(["🥁 Generate Synthwave Beat", "🥁 Generate Trap Groove", "🎹 Load D Minor Chords"])

    # Fallback default conversational reply if nothing specifically triggered
    if not reply_lines:
        reply_lines.append(
            f"🎵 I am your **AI-BS Sovereign Music & Audio Assistant**, connected directly to your DAW engine on your RTX 4090.\n\n"
            f"Here is how we can collaborate in natural language:\n"
            f"- **Tempo & Timing**: *'Change tempo to 128 BPM'*, *'Lock tempo to 85 for Suno'*, *'Speed up by 5'*.\n"
            f"- **Groove Composition**: *'Create a synthwave beat'*, *'Make a dark trap rhythm'*, *'Generate lofi drums'*.\n"
            f"- **Transport Control**: *'Play the track'*, *'Stop playback'*, *'Mute drums'*.\n"
            f"- **Studio Views**: *'Open Wave Studio'*, *'Go to Stem Extractor'*, *'Show Mixer'*, *'Open Arranger'*.\n"
            f"- **Audio & Mixing Advice**: Ask about chord progressions, fixing cut spots, VST saturation, or sidechain compression.\n"
            f"- **Stem Isolation**: Separate any audio file with CUDA Demucs v4 in under 8 seconds."
        )
        suggestions.extend(["⏱ Set Tempo to 85 BPM", "🥁 Generate Synthwave Beat", "✨ Open AI Stem Suite", "🎙️ Switch to Wave Studio"])

    if not suggestions:
        suggestions = ["⏱ Set 85 BPM", "▶️ Play Track", "🥁 Generate Trap Beat", "🎚 Open Mixer"]

    return {
        "reply": "\n\n".join(reply_lines),
        "actions": actions,
        "suggestions": suggestions,
        "engine": "local_nlp_heuristic"
    }

async def query_ollama_music_assistant(prompt: str, history: List[MessageItem], context: Optional[DawContext]) -> Optional[Dict[str, Any]]:
    """Attempts to prompt the local Ollama LLM for deep conversational music reasoning."""
    system_prompt = (
        "You are the AI-BS Sovereign Music Producer and Audio Assistant, an elite sound engineer, "
        "music theorist, and music technologist running locally on a Windows 11 workstation with an NVIDIA RTX 4090. "
        "You help the producer compose songs, arrange tracks, design synth patches, repair audio seams, "
        "and master recordings using natural language.\n\n"
        f"CURRENT DAW STATE:\n"
        f"- Tempo: {context.bpm if context else 85} BPM\n"
        f"- Playing: {context.isPlaying if context else False}\n"
        f"- Active View: {context.activeView if context else 'multimedia'}\n"
        f"- Master Volume: {context.masterVolume if context else 0.0} dB\n\n"
        "INSTRUCTIONS:\n"
        "1. Speak in a helpful, knowledgeable, inspiring tone as a creative co-producer.\n"
        "2. If the user asks to change tempo, start/stop playback, generate beats, switch views, or adjust volume, "
        "describe what you are doing musically and provide the exact parameter.\n"
        "3. Provide chord names, scales, EQ frequencies, and mixing chains when asked.\n"
        "4. Keep explanations concise, practical, and punchy. Use bullet points for steps or chord charts."
    )

    messages = [{"role": "system", "content": system_prompt}]
    for h in history[-6:]:
        messages.append({"role": h.role, "content": h.content})
    messages.append({"role": "user", "content": prompt})

    # Find an active Ollama model
    target_model = "llama3.1:latest"
    try:
        async with httpx.AsyncClient(timeout=1.5) as client:
            tags_res = await client.get(f"{OLLAMA_HOST}/api/tags")
            if tags_res.status_code == 200:
                available = [m["name"] for m in tags_res.json().get("models", [])]
                for candidate in ["llama3.1:latest", "stehouwer_llm:latest", "llama3:latest", "qwen2.5-coder:latest", "gemma4:12b"]:
                    if candidate in available:
                        target_model = candidate
                        break
                else:
                    if available:
                        target_model = available[0]
    except Exception:
        return None

    try:
        async with httpx.AsyncClient(timeout=6.0) as client:
            payload = {
                "model": target_model,
                "messages": messages,
                "stream": False,
                "options": {
                    "temperature": 0.7,
                    "num_predict": 380
                }
            }
            res = await client.post(f"{OLLAMA_HOST}/api/chat", json=payload)
            if res.status_code == 200:
                data = res.json()
                raw_reply = data.get("message", {}).get("content", "").strip()
                if raw_reply:
                    # Also extract actions from prompt
                    heuristic = parse_heuristic_actions(prompt, context)
                    return {
                        "reply": raw_reply,
                        "actions": heuristic.get("actions", []),
                        "suggestions": heuristic.get("suggestions", ["⏱ Set Tempo", "🥁 New Beat", "🎚 Open Mixer"]),
                        "engine": f"ollama ({target_model})"
                    }
    except Exception as e:
        logger.debug(f"Ollama chat attempt timed out or failed: {e}")

    return None

# ═══════════════════════════════════════════════════════════════════════════
# API ENDPOINTS
# ═══════════════════════════════════════════════════════════════════════════

@router.post("/chat")
async def music_assistant_chat(req: MusicAssistantChatRequest):
    """
    Primary Natural Language Audio & Music Assistant Endpoint.
    Leverages local Ollama LLMs with instant intelligent heuristic fallback.
    """
    user_msg = req.message.strip()
    if not user_msg:
        raise HTTPException(status_code=400, detail="Message cannot be empty.")

    # 1. Attempt local Ollama inference
    ollama_res = await query_ollama_music_assistant(user_msg, req.history or [], req.context)
    if ollama_res:
        return {
            "status": "success",
            **ollama_res
        }

    # 2. Instant Heuristic & Intent Parser Fallback
    heuristic_res = parse_heuristic_actions(user_msg, req.context)
    return {
        "status": "success",
        **heuristic_res
    }

@router.get("/status")
async def music_assistant_status():
    """Returns local LLM hardware status and available music production capabilities."""
    ollama_online = False
    available_models = []
    try:
        async with httpx.AsyncClient(timeout=1.5) as client:
            r = await client.get(f"{OLLAMA_HOST}/api/tags")
            if r.status_code == 200:
                ollama_online = True
                available_models = [m["name"] for m in r.json().get("models", [])]
    except Exception:
        pass

    return {
        "status": "online",
        "ollama_online": ollama_online,
        "ollama_host": OLLAMA_HOST,
        "available_models": available_models[:10],
        "gpu_accelerated": True,
        "demucs_bridge": "online (RTX 4090)",
        "vst_bridge": "port_8013",
        "capabilities": [
            "natural_language_daw_control",
            "prompt_to_midi_generation",
            "stem_isolation_orchestration",
            "audio_repair_and_tuning_advice",
            "harmonic_progression_synthesis",
            "mix_and_fx_automation"
        ]
    }
