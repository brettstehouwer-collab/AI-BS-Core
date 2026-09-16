import os
import sys
import math
import struct
import logging
import hashlib
import numpy as np
import scipy.io.wavfile as wavfile
import subprocess
import imageio_ffmpeg

logger = logging.getLogger("MuseInstrumentSampler")
logger.setLevel(logging.INFO)

MUSE_HUB_DIR = r"C:\Users\footb\Muse Hub\Instruments"
CACHE_DIR = r"C:\AI-BS\backend\muse_samples_cache"
os.makedirs(CACHE_DIR, exist_ok=True)


class MuseInstrumentSampler:
    """
    Scans, extracts, and caches real multisample recordings from Muse Hub instruments
    (StaffPad .sts containers / .opus audio files) and layers them into AI audio tracks.
    """

    _sample_cache = {}

    @classmethod
    def find_sts_files(cls):
        """Discovers all available .sts instrument archives across Muse Hub folders."""
        instruments = {}
        if not os.path.exists(MUSE_HUB_DIR):
            logger.warning(f"Muse Hub directory not found at {MUSE_HUB_DIR}")
            return instruments

        for cat in os.listdir(MUSE_HUB_DIR):
            cat_dir = os.path.join(MUSE_HUB_DIR, cat)
            if os.path.isdir(cat_dir):
                for root, dirs, fnames in os.walk(cat_dir):
                    for f in fnames:
                        if f.endswith(".sts"):
                            inst_name = os.path.splitext(f)[0].lower()
                            instruments[inst_name] = os.path.join(root, f)
        return instruments

    @classmethod
    def extract_sample_from_sts(cls, sts_path, keyword=""):
        """Extracts or loads pre-decoded .wav audio sample from cache for zero-latency execution."""
        inst_name = os.path.splitext(os.path.basename(sts_path))[0].lower()
        index_file = os.path.join(CACHE_DIR, "predecoded_index.json")

        # Fast Path: Check predecoded_index.json
        if os.path.exists(index_file):
            try:
                import json

                with open(index_file, "r", encoding="utf-8") as idx_f:
                    idx_data = json.load(idx_f)
                    if inst_name in idx_data and idx_data[inst_name]:
                        cached_wav_path = idx_data[inst_name][0]
                        if os.path.exists(cached_wav_path):
                            sr, data = wavfile.read(cached_wav_path)
                            if data.dtype == np.int16:
                                return data.astype(np.float32) / 32768.0
                            elif data.dtype == np.int32:
                                return data.astype(np.float32) / 2147483648.0
                            else:
                                return data.astype(np.float32)
            except Exception as e:
                logger.warning(f"Fast index lookup warning: {e}")

        # Fallback Path: Direct extraction from .sts container
        try:
            with open(sts_path, "rb") as f:
                magic_len = struct.unpack("<I", f.read(4))[0]
                magic = f.read(magic_len).decode("ascii", errors="ignore")
                if "StaffPad" not in magic:
                    return None

                num_files = struct.unpack("<I", f.read(4))[0]
                entries = []
                for _ in range(num_files):
                    fname_len = struct.unpack("<I", f.read(4))[0]
                    fname = f.read(fname_len).decode("utf-8", errors="ignore")
                    offset = struct.unpack("<Q", f.read(8))[0]
                    size = struct.unpack("<Q", f.read(8))[0]
                    entries.append((fname, offset, size))

                # Find entry matching keyword or pick middle sample
                target_entry = None
                if keyword:
                    for entry in entries:
                        if keyword.lower() in entry[0].lower():
                            target_entry = entry
                            break
                if not target_entry and len(entries) > 0:
                    target_entry = entries[
                        len(entries) // 2
                    ]  # pick middle velocity/note sample

                if not target_entry:
                    return None

                fname, offset, size = target_entry
                cache_key = hashlib.md5(
                    f"{sts_path}_{fname}".encode("utf-8")
                ).hexdigest()[:12]
                cached_wav_path = os.path.join(CACHE_DIR, f"{cache_key}_{fname}.wav")

                if not os.path.exists(cached_wav_path):
                    # Extract Opus file to temporary location
                    temp_opus_path = os.path.join(CACHE_DIR, f"{cache_key}.opus")
                    f.seek(offset)
                    opus_bytes = f.read(size)
                    with open(temp_opus_path, "wb") as opus_f:
                        opus_f.write(opus_bytes)

                    # Decode Opus to WAV using bundled FFmpeg
                    ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()
                    res = subprocess.run(
                        [
                            ffmpeg_exe,
                            "-y",
                            "-i",
                            temp_opus_path,
                            "-ar",
                            "44100",
                            "-ac",
                            "2",
                            cached_wav_path,
                        ],
                        capture_output=True,
                        text=True,
                    )
                    try:
                        os.remove(temp_opus_path)
                    except Exception:
                        pass

                    if res.returncode != 0 or not os.path.exists(cached_wav_path):
                        return None

                # Read WAV file into numpy float array [-1.0, 1.0]
                sr, data = wavfile.read(cached_wav_path)
                if data.dtype == np.int16:
                    float_data = data.astype(np.float32) / 32768.0
                elif data.dtype == np.int32:
                    float_data = data.astype(np.float32) / 2147483648.0
                else:
                    float_data = data.astype(np.float32)

                return float_data
        except Exception as e:
            logger.error(f"Error extracting sample from {sts_path}: {e}")
            return None

    @classmethod
    def get_instrument_samples_for_genre(
        cls, genre, duration_sec, target_sample_rate=44100, musical_cues=None
    ):
        """
        Retrieves real Muse Hub instrument audio arrays tailored for specified genre and bracketed musical cues.
        Returns a dictionary of {instrument_label: float_numpy_array_stereo}.
        """
        instruments = cls.find_sts_files()
        if not instruments:
            return {}

        target_length = target_sample_rate * duration_sec
        g = genre.lower()
        requested_insts = []

        if "orchestral" in g or "epic" in g or "cinematic" in g:
            requested_insts = [
                "violins 1",
                "cellos",
                "french horns",
                "piano",
                "timpani",
                "harp",
            ]
        elif "rock" in g or "metal" in g:
            requested_insts = [
                "electric lp - heavy",
                "electric bass",
                "drum kit",
                "acoustic steel picked",
            ]
        elif "hip" in g or "rap" in g or "trap" in g or "drill" in g:
            requested_insts = ["electric bass", "piano", "trumpets a4", "trap kit"]
        elif "jazz" in g or "rnb" in g or "blues" in g:
            requested_insts = [
                "soft piano",
                "tenor saxophone",
                "electric bass",
                "concert combo",
            ]
        elif "folk" in g or "acoustic" in g or "country" in g:
            requested_insts = ["acoustic nylon", "flute 1", "handchimes", "harp"]
        elif "pop" in g or "edm" in g or "dance" in g:
            requested_insts = ["piano", "altos", "dream piano", "gm kit"]
        else:  # synthwave / cyberpunk / ambient
            requested_insts = ["soft piano", "cellos", "violin 1 solo"]

        # Dynamically append instruments extracted from bracketed musical cues
        if musical_cues:
            cues_text = " ".join(musical_cues).lower()
            if "piano" in cues_text and "piano" not in requested_insts:
                requested_insts.append("piano")
            if (
                "bell" in cues_text or "chimes" in cues_text
            ) and "handchimes" not in requested_insts:
                requested_insts.append("handchimes")
            if "tubular" in cues_text:
                requested_insts.append("tubular bells")
            if "glockenspiel" in cues_text:
                requested_insts.append("glockenspiel")
            if (
                "violin" in cues_text or "strings" in cues_text
            ) and "violins 1" not in requested_insts:
                requested_insts.append("violins 1")
            if "cello" in cues_text and "cellos" not in requested_insts:
                requested_insts.append("cellos")
            if "flute" in cues_text and "flute 1" not in requested_insts:
                requested_insts.append("flute 1")
            if (
                "guitar" in cues_text or "steel" in cues_text
            ) and "acoustic steel picked" not in requested_insts:
                requested_insts.append("acoustic steel picked")
            if (
                "808" in cues_text or "bass" in cues_text or "drill" in cues_text
            ) and "electric bass" not in requested_insts:
                requested_insts.append("electric bass")
            if (
                "drum" in cues_text or "trap" in cues_text
            ) and "trap kit" not in requested_insts:
                requested_insts.append("trap kit")
            if "horn" in cues_text or "brass" in cues_text:
                requested_insts.append("french horns")

        layers = {}
        for req in requested_insts:
            matched_key = None
            for key in instruments:
                if req in key or key in req:
                    matched_key = key
                    break

            if matched_key and matched_key in instruments:
                sts_path = instruments[matched_key]
                audio_data = cls.extract_sample_from_sts(sts_path)
                if audio_data is not None and len(audio_data) > 0:
                    if len(audio_data) < target_length:
                        repeats = int(math.ceil(target_length / len(audio_data)))
                        tiled = np.tile(audio_data, (repeats, 1))[:target_length]
                    else:
                        tiled = audio_data[:target_length]
                    layers[matched_key] = tiled

        return layers
