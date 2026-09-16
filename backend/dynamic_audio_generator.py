import os
import math
import time
import struct
import wave
import hashlib
import win32com.client
import asyncio
from concurrent.futures import ThreadPoolExecutor

import re

# Dedicated background task pool for heavy DSP synthesis
audio_synthesis_pool = ThreadPoolExecutor(max_workers=2, thread_name_prefix="AudioSynth")

GENERATED_MEDIA_DIR = r"C:\AI-BS\frontend\public\media\generated"
TEMP_VOCAL_DIR = r"C:\AI-BS\backend\temp_vocals"
os.makedirs(GENERATED_MEDIA_DIR, exist_ok=True)
os.makedirs(TEMP_VOCAL_DIR, exist_ok=True)


def parse_lyric_cues(text):
    """
    Auto-detects bracketed/parenthesized musical directions, instrument cues, and section markers.
    Returns (extracted_cues_list, cleaned_vocal_lyrics_text).
    """
    if not text or not text.strip():
        return [], ""

    raw_lines = text.split("\n")
    extracted_cues = []
    vocal_lines = []

    for line in raw_lines:
        line_str = line.strip()
        if not line_str:
            continue

        # Extract all bracketed/parenthesized directives
        matches = re.findall(r"[\(\[]([^\)\]]+)[\)\]]", line_str)
        for m in matches:
            extracted_cues.append(m.strip())

        # Omit pure structural directive lines from vocal synthesis
        if (line_str.startswith("(") and line_str.endswith(")")) or (
            line_str.startswith("[") and line_str.endswith("]")
        ):
            if not any(k in line_str.lower() for k in ["spoken", "voice", "singing"]):
                continue

        # Handle spoken dialogue quotes e.g. (Brett spoken): "Yo Sean..."
        clean_text = line_str
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
            clean_text = re.sub(r"^\([^\)]+\)\s*:?\s*", "", clean_text).strip()
            clean_text = re.sub(r"^\[[^\]]+\]\s*:?\s*", "", clean_text).strip()

        if clean_text:
            vocal_lines.append(clean_text)

    return extracted_cues, "\n".join(vocal_lines)


class DSPAudioMasteringEngine:
    """
    High-Fidelity Master DSP Audio Processing Engine.
    - 1st Order High-Pass Filter (HPF @ 85 Hz) to eliminate low-end rumble and DC offset.
    - Professional Gain Staging (-14 dB headroom drop) to prevent digital saturation.
    - Smooth Tanh Soft-Knee Dynamic Limiter to eliminate 0 dBFS square-wave clipping and preserve transients.
    """

    def __init__(self, sample_rate=44100, cutoff_hz=85.0):
        self.sample_rate = sample_rate
        dt = 1.0 / float(sample_rate)
        rc = 1.0 / (2.0 * math.pi * cutoff_hz)
        self.alpha = rc / (rc + dt)
        self.prev_x_l = 0.0
        self.prev_y_l = 0.0
        self.prev_x_r = 0.0
        self.prev_y_r = 0.0

    def process_sample(self, in_l: float, in_r: float) -> tuple:
        # 1. High-Pass Filter (85 Hz Cutoff) -> Strips DC offset & low-end rumble
        out_l = self.alpha * (self.prev_y_l + in_l - self.prev_x_l)
        self.prev_x_l = in_l
        self.prev_y_l = out_l

        out_r = self.alpha * (self.prev_y_r + in_r - self.prev_x_r)
        self.prev_x_r = in_r
        self.prev_y_r = out_r

        # 2. Smooth Tanh Soft-Knee Limiter -> Prevents hard 0 dBFS square-wave clipping & preserves transients
        limited_l = math.tanh(out_l * 1.05) * 0.82
        limited_r = math.tanh(out_r * 1.05) * 0.82

        return limited_l, limited_r


def generate_dynamic_song(
    prompt: str,
    genre: str,
    duration_sec: int,
    lyrics: str = None,
    tempo_bpm: int = 110,
    vocal_style: str = "lead",
    arrangement: str = "verse_chorus",
) -> tuple:
    """
    Synthesizes a full stereo WAV audio track with automatic bracketed musical cue parsing,
    neural RVQ vocal rendering, Muse Hub instrument layer blending, and DSP audio mastering.
    """
    # Parse bracketed musical cues & clean lyric lines
    extracted_cues, clean_lyrics_text = parse_lyric_cues(lyrics)
    if extracted_cues:
        print(
            f"Auto-detected {len(extracted_cues)} bracketed musical cues: {extracted_cues[:5]}"
        )

    # Dynamic Auto-Timing Calculation based on Lyrics & BPM if duration_sec <= 0
    if duration_sec <= 0:
        bpm = max(60, min(180, tempo_bpm))
        beat_interval = 60.0 / float(bpm)
        bar_interval = beat_interval * 4.0

        target_text = clean_lyrics_text or lyrics or ""
        if target_text.strip():
            num_lines = len([l.strip() for l in target_text.split("\n") if l.strip()])
            auto_bars = (
                2 + (num_lines * 2) + 4
            )  # 2 bars intro + 2 bars per line + 4 bars outro
            duration_sec = int(math.ceil(auto_bars * bar_interval))
        else:
            auto_bars = 16  # 16 bars for instrumental arrangement
            duration_sec = int(math.ceil(auto_bars * bar_interval))

        duration_sec = max(15, min(600, duration_sec))
        print(f"Dynamic Auto-Timing calculated duration: {duration_sec}s ({bpm} BPM)")

    sample_rate = 44100
    num_samples = sample_rate * duration_sec

    # Hash unique filename
    unique_str = f"{prompt}_{genre}_{duration_sec}_{lyrics}_{tempo_bpm}_{vocal_style}_{arrangement}_{time.time()}"
    file_hash = hashlib.md5(unique_str.encode("utf-8")).hexdigest()[:12]
    filename = f"song_{genre}_{duration_sec}s_{file_hash}.wav"
    output_path = os.path.join(GENERATED_MEDIA_DIR, filename)

    # Instantiate Master DSP Engine (85 Hz HPF + Soft-Knee Limiter)
    dsp_engine = DSPAudioMasteringEngine(sample_rate=sample_rate, cutoff_hz=85.0)

    # 1. Synthesize Neural Vocal Track via Generative Audio Transformer (RVQ Codec)
    neural_vocal_array = None
    vocal_source = clean_lyrics_text if clean_lyrics_text else lyrics
    if vocal_source and vocal_source.strip() and vocal_style.lower() != "instrumental":
        try:
            from neural_audio_codec_transformer import synthesize_neural_vocal_track

            neural_vocal_array = synthesize_neural_vocal_track(
                lyrics=vocal_source,
                genre=genre,
                bpm=tempo_bpm,
                vocal_style=vocal_style,
                duration_sec=duration_sec,
                sample_rate=sample_rate,
            )
            print(
                f"Generated Neural Audio Transformer vocal track ({len(neural_vocal_array)} samples)"
            )
        except Exception as e:
            print(f"Neural Audio Transformer vocal synthesis warning: {e}")

    # 2. Base Frequencies & Musical Scale based on Genre & Dynamic BPM
    g = genre.lower()
    bpm = max(60, min(180, tempo_bpm))
    beat_interval = 60.0 / float(bpm)
    bar_interval = beat_interval * 4.0

    if "hip" in g or "rap" in g or "trap" in g:
        base_freq = 110.0  # A2
        chord = [110.0, 130.81, 164.81, 196.00]  # Am7
    elif "rock" in g or "metal" in g:
        base_freq = 82.41  # E2
        chord = [82.41, 123.47, 164.81, 246.94]  # E power chord
    elif "edm" in g or "pop" in g:
        base_freq = 130.81  # C3
        chord = [130.81, 164.81, 196.00, 246.94]  # Cmaj7
    elif "jazz" in g or "rnb" in g:
        base_freq = 146.83  # D3
        chord = [146.83, 174.61, 220.00, 261.63]  # Dm7
    else:  # synthwave / cyberpunk / ambient
        base_freq = 220.0  # A3
        chord = [220.0, 261.63, 329.63, 392.00]  # Am7

    # 3. Retrieve Muse Hub Real Instrument Multisample Layers
    muse_layers = {}
    try:
        from muse_instrument_sampler import MuseInstrumentSampler

        muse_layers = MuseInstrumentSampler.get_instrument_samples_for_genre(
            genre, duration_sec, sample_rate, musical_cues=extracted_cues
        )

        if muse_layers:
            print(
                f"Loaded {len(muse_layers)} Muse Hub instrument layers for {genre}: {list(muse_layers.keys())}"
            )
    except Exception as e:
        print(f"Muse instrument sampler warning: {e}")

    # 4. Render Stereo Audio Stream
    frames = bytearray()
    with wave.open(output_path, "wb") as wav_file:
        wav_file.setnchannels(2)  # Stereo
        wav_file.setsampwidth(2)  # 16-bit PCM
        wav_file.setframerate(sample_rate)

        frames = bytearray()

        for i in range(num_samples):
            t = i / sample_rate

            # Master volume envelope (fade-in / fade-out)
            song_progress = t / duration_sec
            volume_env = 1.0
            if song_progress < 0.02:
                volume_env = song_progress / 0.02
            elif song_progress > 0.95:
                volume_env = (1.0 - song_progress) / 0.05

            # LFO & Stereo Pan
            lfo = 0.5 + 0.5 * math.sin(2 * math.pi * 0.25 * t)
            lfo_pan = math.sin(2 * math.pi * 0.1 * t)

            # Synth Chord Pad (Gain Staging: scaled down to 0.08 per tone)
            val = 0.0
            for c_idx, f in enumerate(chord):
                detune = f * (1.0 + 0.002 * math.sin(2 * math.pi * (c_idx + 1) * t))
                val += math.sin(2 * math.pi * detune * t) * (0.08 / len(chord))

            # Sub-Bass 808 Pulse (Gain Staging: reduced from 0.35 to 0.15)
            bass_val = math.sin(2 * math.pi * (base_freq / 2.0) * t) * 0.15
            beat_cycle = (t % beat_interval) / beat_interval
            bass_envelope = math.exp(-3.0 * beat_cycle)
            val += bass_val * bass_envelope

            # Rhythm Kick & Snare Drums (Gain Staging: -14 dB reduction)
            beat_num = int(t / beat_interval) % 4
            kick_env = (
                math.exp(-12.0 * beat_cycle)
                if (beat_num == 0 or beat_num == 2)
                else 0.0
            )
            snare_env = (
                math.exp(-8.0 * beat_cycle) if (beat_num == 1 or beat_num == 3) else 0.0
            )

            kick = (
                math.sin(2 * math.pi * (60.0 - 30.0 * beat_cycle) * t) * kick_env * 0.22
            )
            snare = (
                math.sin(2 * math.pi * 200.0 * t) * 0.1
                + (hash(i) % 1000 / 1000.0 - 0.5) * 0.15
            ) * snare_env

            backing_val = (val + kick + snare) * volume_env

            # 4. Neural Vocal Blend (Gain Staging: reduced from 0.85 to 0.35)
            vocal_mix_l = 0.0
            vocal_mix_r = 0.0
            if neural_vocal_array is not None and i < len(neural_vocal_array):
                vocal_mix_l = float(neural_vocal_array[i][0]) * 0.35
                vocal_mix_r = float(neural_vocal_array[i][1]) * 0.35

            # Blend Muse Hub Real Instrument Multisample Layers (Gain Staging: reduced to 0.20)
            muse_mix_left = 0.0
            muse_mix_right = 0.0
            if muse_layers:
                for inst_key, audio_arr in muse_layers.items():
                    if i < len(audio_arr):
                        if audio_arr.ndim > 1:
                            s_l = float(audio_arr[i][0])
                            s_r = (
                                float(audio_arr[i][1])
                                if audio_arr.shape[1] > 1
                                else s_l
                            )
                        else:
                            s_l = float(audio_arr[i])
                            s_r = s_l
                        muse_mix_left += s_l * 0.20
                        muse_mix_right += s_r * 0.20

            # Sum Raw Headroom Signals (-14 dB gain staging applied)
            raw_left = (
                backing_val * (0.35 - 0.1 * lfo_pan)
                + vocal_mix_l
                + muse_mix_left * volume_env
            )
            raw_right = (
                backing_val * (0.35 + 0.1 * lfo_pan)
                + vocal_mix_r
                + muse_mix_right * volume_env
            )

            # Process through Master DSP Filter (85 Hz High-Pass Filter + Soft-Knee Limiter)
            left_sample, right_sample = dsp_engine.process_sample(raw_left, raw_right)

            # Convert to 16-bit PCM stereo (Clean dynamic range, zero digital clipping)
            left_pcm = int(left_sample * 32767)
            right_pcm = int(right_sample * 32767)
            frames.extend(struct.pack("<hh", left_pcm, right_pcm))

        wav_file.writeframes(frames)

    print(
        f"Synthesized beat-quantized song: {output_path} ({duration_sec}s, {len(frames)} bytes)"
    )
    return f"/media/generated/{filename}", duration_sec

async def generate_dynamic_song_async(*args, **kwargs) -> tuple:
    """
    Offloads local audio synthesis to a dedicated background task queue (ThreadPoolExecutor)
    to prevent main-thread execution blocking during track generation.
    """
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(audio_synthesis_pool, lambda: generate_dynamic_song(*args, **kwargs))
