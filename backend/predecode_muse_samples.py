import os
import sys
import json
import math
import struct
import logging
import hashlib
import subprocess
import imageio_ffmpeg

logger = logging.getLogger("PredecodeMuseSamples")
logger.setLevel(logging.INFO)

MUSE_HUB_DIR = r"C:\Users\footb\Muse Hub"
CACHE_DIR = r"C:\AI-BS\backend\muse_samples_cache"
os.makedirs(CACHE_DIR, exist_ok=True)
INDEX_FILE = os.path.join(CACHE_DIR, "predecoded_index.json")


def predecode_all_muse_instruments():
    """
    Scans all 102 Muse Hub .sts container archives, extracts primary Opus multisample audio files,
    and decodes them into high-fidelity 44.1kHz stereo WAV PCM files in CACHE_DIR.
    """
    print(f"Scanning Muse Hub at {MUSE_HUB_DIR}...")
    sts_map = {}
    for root, dirs, fnames in os.walk(MUSE_HUB_DIR):
        for f in fnames:
            if f.endswith(".sts"):
                inst_name = os.path.splitext(f)[0].lower()
                sts_map[inst_name] = os.path.join(root, f)

    print(f"Found {len(sts_map)} instrument archives.")
    index_data = {}
    ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()

    for idx, (inst_name, sts_path) in enumerate(sts_map.items()):
        try:
            with open(sts_path, "rb") as f:
                magic_len = struct.unpack("<I", f.read(4))[0]
                magic = f.read(magic_len).decode("ascii", errors="ignore")
                if "StaffPad" not in magic:
                    continue

                num_files = struct.unpack("<I", f.read(4))[0]
                entries = []
                for _ in range(num_files):
                    fname_len = struct.unpack("<I", f.read(4))[0]
                    fname = f.read(fname_len).decode("utf-8", errors="ignore")
                    offset = struct.unpack("<Q", f.read(8))[0]
                    size = struct.unpack("<Q", f.read(8))[0]
                    entries.append((fname, offset, size))

                if not entries:
                    continue

                # Pick up to 3 representative samples per instrument (low, mid, high range/velocity)
                sample_choices = []
                if len(entries) >= 3:
                    sample_choices = [
                        entries[len(entries) // 4],
                        entries[len(entries) // 2],
                        entries[(3 * len(entries)) // 4],
                    ]
                else:
                    sample_choices = entries

                decoded_wav_paths = []
                for entry_idx, (fname, offset, size) in enumerate(sample_choices):
                    safe_fname = fname.replace("/", "_").replace("\\", "_")
                    cache_key = hashlib.md5(
                        f"{sts_path}_{fname}".encode("utf-8")
                    ).hexdigest()[:12]
                    wav_filename = f"{inst_name}_{entry_idx}_{cache_key}.wav"
                    cached_wav_path = os.path.join(CACHE_DIR, wav_filename)

                    if (
                        not os.path.exists(cached_wav_path)
                        or os.path.getsize(cached_wav_path) == 0
                    ):
                        temp_opus = os.path.join(CACHE_DIR, f"temp_{cache_key}.opus")
                        f.seek(offset)
                        opus_bytes = f.read(size)
                        with open(temp_opus, "wb") as opus_f:
                            opus_f.write(opus_bytes)

                        res = subprocess.run(
                            [
                                ffmpeg_exe,
                                "-y",
                                "-i",
                                temp_opus,
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
                            os.remove(temp_opus)
                        except Exception:
                            pass

                    if (
                        os.path.exists(cached_wav_path)
                        and os.path.getsize(cached_wav_path) > 0
                    ):
                        decoded_wav_paths.append(cached_wav_path)

                if decoded_wav_paths:
                    index_data[inst_name] = decoded_wav_paths
                    print(
                        f"[{idx+1}/{len(sts_map)}] Decoded & cached {len(decoded_wav_paths)} samples for: {inst_name}"
                    )

        except Exception as e:
            print(f"[{idx+1}/{len(sts_map)}] Warning processing {inst_name}: {e}")

    with open(INDEX_FILE, "w", encoding="utf-8") as out_idx:
        json.dump(index_data, out_idx, indent=2)

    print(
        f"\nPre-decoding complete! Cached {len(index_data)} instruments into {CACHE_DIR}"
    )


if __name__ == "__main__":
    predecode_all_muse_instruments()
