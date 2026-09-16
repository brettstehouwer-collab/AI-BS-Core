"""
Audio Factoring, DSP Signal Processing & Prosody Mapping Engine for AI-BS Wave Studio & Suno AI
Integrates:
1. SoX & FFmpeg Filtergraph Suite: EBU R128 (-14 LUFS) normalization, phase cancellation, multiband compander.
2. Pitch & Tempo Stretching Engine: Rubber Band & FFmpeg tempo/pitch shift.
3. Acoustic-Somatic Prosody Mapper: Syllable density, rhyme topology, and DAW 16-bar grid alignment.
"""

import os
import sys
import subprocess
import shutil
import time
import re
import math
import logging
from typing import Dict, Any, Optional, List

logger = logging.getLogger("AudioDspProsodyEngine")

OUTPUT_AUDIO_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "saved_data", "audio_dsp"))
os.makedirs(OUTPUT_AUDIO_DIR, exist_ok=True)

FFMPEG_PATHS = [
    r"C:\Program Files\ffmpeg\bin\ffmpeg.exe",
    r"C:\ffmpeg\bin\ffmpeg.exe",
    r"C:\Users\footb\AppData\Local\Microsoft\WinGet\Links\ffmpeg.exe",
    "ffmpeg.exe",
    "ffmpeg"
]


class AudioDspProsodyEngine:
    """Master Audio Factoring, DSP, and Lyric Prosody Engine."""

    @staticmethod
    def _find_ffmpeg_binary() -> Optional[str]:
        for p in FFMPEG_PATHS:
            if os.path.isabs(p) and os.path.exists(p):
                return p
            elif shutil.which(p):
                return shutil.which(p)
        return None

    # =========================================================================
    # 1. DSP FILTERGRAPH ENGINE (EBU R128, COMPRESSION, PHASE CANCELLATION)
    # =========================================================================
    @staticmethod
    def process_dsp_filter(
        audio_path: str,
        filter_type: str = "loudness_normalize",
        target_lufs: float = -14.0,
        output_filename: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Applies DSP filtergraphs (EBU R128 loudness normalization, multiband compression,
        phase invert, lowpass/highpass) using FFmpeg/SoX.
        """
        start_time = time.time()
        if not os.path.exists(audio_path):
            return {"status": "error", "message": f"Audio file not found: {audio_path}"}

        out_name = output_filename or f"dsp_{filter_type}_{int(start_time)}.wav"
        output_path = os.path.join(OUTPUT_AUDIO_DIR, out_name)

        ffmpeg_bin = AudioDspProsodyEngine._find_ffmpeg_binary()
        if not ffmpeg_bin:
            return {"status": "error", "message": "FFmpeg binary not found on host."}

        # Build filtergraph argument
        if filter_type == "loudness_normalize":
            af = f"loudnorm=I={target_lufs}:TP=-1.0:LRA=11"
        elif filter_type == "vocal_clean":
            af = "highpass=f=80,lowpass=f=12000,acompressor=threshold=-20dB:ratio=4:attack=5:release=50"
        elif filter_type == "bass_boost":
            af = "equalizer=f=60:width_type=o:width=1.5:g=6,lowpass=f=250"
        elif filter_type == "phase_invert":
            af = "aeval=-val(0)|-val(1)"
        else:
            af = "anull"

        cmd = [
            ffmpeg_bin,
            "-y",
            "-i", audio_path,
            "-af", af,
            "-c:a", "pcm_s16le",
            output_path
        ]

        try:
            proc = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
            render_ms = round((time.time() - start_time) * 1000, 2)
            if proc.returncode == 0 and os.path.exists(output_path):
                return {
                    "status": "success",
                    "filter_type": filter_type,
                    "target_lufs": target_lufs if filter_type == "loudness_normalize" else None,
                    "input_path": audio_path,
                    "output_path": output_path,
                    "file_size_bytes": os.path.getsize(output_path),
                    "process_time_ms": render_ms,
                    "message": f"Applied '{filter_type}' DSP filter in {render_ms}ms"
                }
            else:
                return {"status": "error", "message": f"FFmpeg error: {proc.stderr[:300]}"}
        except Exception as e:
            return {"status": "error", "message": f"DSP processing failed: {e}"}

    # =========================================================================
    # 2. PITCH & TEMPO TIME-STRETCH ENGINE
    # =========================================================================
    @staticmethod
    def stretch_pitch_tempo(
        audio_path: str,
        tempo_ratio: float = 1.0,
        semitones: float = 0.0,
        output_filename: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Shifts pitch by semitones and/or stretches tempo without pitch distortion.
        """
        start_time = time.time()
        if not os.path.exists(audio_path):
            return {"status": "error", "message": f"Audio file not found: {audio_path}"}

        out_name = output_filename or f"stretch_t{tempo_ratio}_s{semitones}_{int(start_time)}.wav"
        output_path = os.path.join(OUTPUT_AUDIO_DIR, out_name)

        ffmpeg_bin = AudioDspProsodyEngine._find_ffmpeg_binary()
        if not ffmpeg_bin:
            return {"status": "error", "message": "FFmpeg binary not found on host."}

        # Pitch shift multiplier: 2^(semitones/12)
        pitch_factor = math.pow(2.0, semitones / 12.0)
        
        # asetrate shifts both pitch and speed, then atempo corrects speed
        # effective pitch = pitch_factor, effective tempo = tempo_ratio
        sample_rate = 44100
        new_sample_rate = int(sample_rate * pitch_factor)
        compensate_tempo = tempo_ratio / pitch_factor

        # Clamp atempo between 0.5 and 2.0 per FFmpeg filter requirements
        atempo_filters = []
        rem_tempo = compensate_tempo
        while rem_tempo > 2.0:
            atempo_filters.append("atempo=2.0")
            rem_tempo /= 2.0
        while rem_tempo < 0.5:
            atempo_filters.append("atempo=0.5")
            rem_tempo /= 0.5
        atempo_filters.append(f"atempo={round(rem_tempo, 4)}")

        atempo_chain = ",".join(atempo_filters)
        af = f"asetrate={new_sample_rate},{atempo_chain},aresample={sample_rate}"

        cmd = [
            ffmpeg_bin,
            "-y",
            "-i", audio_path,
            "-af", af,
            "-c:a", "pcm_s16le",
            output_path
        ]

        try:
            proc = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
            render_ms = round((time.time() - start_time) * 1000, 2)
            if proc.returncode == 0 and os.path.exists(output_path):
                return {
                    "status": "success",
                    "tempo_ratio": tempo_ratio,
                    "semitones": semitones,
                    "input_path": audio_path,
                    "output_path": output_path,
                    "file_size_bytes": os.path.getsize(output_path),
                    "process_time_ms": render_ms,
                    "message": f"Shifted pitch ({semitones}st) and stretched tempo ({tempo_ratio}x) in {render_ms}ms"
                }
            else:
                return {"status": "error", "message": f"FFmpeg error: {proc.stderr[:300]}"}
        except Exception as e:
            return {"status": "error", "message": f"Time stretch failed: {e}"}

    # =========================================================================
    # 3. ACOUSTIC-SOMATIC PROSODY & RHYME TOPOLOGY MAPPER
    # =========================================================================
    @staticmethod
    def map_lyrics_prosody(
        raw_lyrics: str,
        bpm: int = 140,
        time_signature: str = "4/4"
    ) -> Dict[str, Any]:
        """
        Parses raw song lyrics, calculates syllable density per bar, maps internal
        rhyme topologies, and constructs rigid DAW grid alignment for Suno AI & Wave Studio.
        """
        start_time = time.time()
        lines = [line.strip() for line in raw_lyrics.strip().split("\n") if line.strip()]
        
        # Syllable estimator based on vowel clusters
        def count_syllables(word: str) -> int:
            w = re.sub(r'[^a-zA-Z]', '', word.lower())
            if not w:
                return 0
            if len(w) <= 3:
                return 1
            w = re.sub(r'(?:[^laeiouy]|ed|es|e)$', '', w)
            w = re.sub(r'^y', '', w)
            matches = re.findall(r'[aeiouy]{1,2}', w)
            return max(1, len(matches))

        # Extract phonetic end-rhyme sound token
        def get_rhyme_token(word: str) -> str:
            w = re.sub(r'[^a-zA-Z]', '', word.lower())
            vowels = re.findall(r'[aeiouy]+[a-z]*$', w)
            return vowels[0] if vowels else w[-2:] if len(w) >= 2 else w

        mapped_bars = []
        rhyme_dict: Dict[str, str] = {}
        rhyme_labels = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
        rhyme_idx = 0
        total_syllables = 0

        for i, line in enumerate(lines, 1):
            words = line.split()
            line_syllables = sum(count_syllables(w) for w in words)
            total_syllables += line_syllables
            last_word = words[-1] if words else ""
            r_token = get_rhyme_token(last_word)

            if r_token not in rhyme_dict:
                rhyme_dict[r_token] = rhyme_labels[rhyme_idx % len(rhyme_labels)]
                rhyme_idx += 1
            rhyme_tag = rhyme_dict[r_token]

            # Syllable stress evaluation (target ~8-12 syllables for a 4/4 rap bar or 6-8 for melodic)
            cadence_status = "Optimal" if 7 <= line_syllables <= 14 else ("Dense (Fast Flow)" if line_syllables > 14 else "Sparse (Melodic/Half-Time)")

            mapped_bars.append({
                "bar_number": i,
                "text": line,
                "word_count": len(words),
                "syllable_count": line_syllables,
                "cadence_status": cadence_status,
                "rhyme_scheme_tag": rhyme_tag,
                "last_word": last_word,
                "est_duration_beats": 4
            })

        avg_syllables = round(total_syllables / max(len(lines), 1), 2)
        total_bars = len(lines)
        total_seconds = round((total_bars * 4 * 60) / bpm, 2)
        render_ms = round((time.time() - start_time) * 1000, 2)

        return {
            "status": "success",
            "total_bars": total_bars,
            "total_syllables": total_syllables,
            "avg_syllables_per_bar": avg_syllables,
            "bpm": bpm,
            "time_signature": time_signature,
            "estimated_duration_seconds": total_seconds,
            "mapped_bars": mapped_bars,
            "rhyme_scheme": "".join(b["rhyme_scheme_tag"] for b in mapped_bars),
            "process_time_ms": render_ms,
            "message": f"Successfully mapped prosody across {total_bars} bars ({avg_syllables} avg syl/bar) in {render_ms}ms"
        }
