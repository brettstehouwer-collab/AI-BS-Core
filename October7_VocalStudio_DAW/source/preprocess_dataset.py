#!/usr/bin/env python3
"""
ACE-Step 1.5 Audio Dataset Preprocessor
Slices, normalizes loudness to -14 LUFS, resamples to 44.1 kHz, and generates metadata.jsonl.
Optimized for local training on NVIDIA RTX 4090 (24GB VRAM).
"""

import os
import json
import argparse
from pathlib import Path

try:
    import soundfile as sf
    import pyloudnorm as pyln
    import librosa
    import numpy as np
    from tqdm import tqdm
except ImportError:
    print("\n[!] Missing audio packages. Run:")
    print("pip install soundfile pyloudnorm librosa tqdm numpy\n")
    exit(1)


def process_audio_file(
    input_path: Path,
    output_dir: Path,
    target_sr: int = 44100,
    segment_duration: float = 30.0,
    overlap: float = 2.0,
    target_lufs: float = -14.0,
    default_prompt: str = ""
):
    records = []

    # Load audio (preserving dual-channel stereo)
    audio, sr = librosa.load(str(input_path), sr=target_sr, mono=False)

    # Normalize shape to [channels, samples]
    if audio.ndim == 1:
        audio = np.stack([audio, audio], axis=0)
    elif audio.shape[0] > 2:
        audio = audio[:2, :]

    total_samples = audio.shape[1]
    segment_samples = int(segment_duration * target_sr)
    step_samples = int((segment_duration - overlap) * target_sr)

    # Initialize BS.1770 loudness meter
    meter = pyln.Meter(target_sr)

    stem_name = input_path.stem
    chunk_idx = 0

    for start in range(0, total_samples, step_samples):
        end = start + segment_samples
        if end > total_samples:
            # Skip fragments under 10 seconds
            if (total_samples - start) < (10.0 * target_sr):
                break
            chunk = audio[:, start:]
            pad_width = segment_samples - chunk.shape[1]
            chunk = np.pad(chunk, ((0, 0), (0, pad_width)), mode='constant')
        else:
            chunk = audio[:, start:end]

        chunk_t = chunk.T

        try:
            current_lufs = meter.integrated_loudness(chunk_t)
            if np.isneginf(current_lufs) or np.isnan(current_lufs):
                continue
            normalized_chunk_t = pyln.normalize.loudness(chunk_t, current_lufs, target_lufs)
        except Exception:
            peak = np.max(np.abs(chunk_t))
            if peak > 0:
                normalized_chunk_t = chunk_t / peak * 0.95
            else:
                continue

        # Prevent digital overs
        max_val = np.max(np.abs(normalized_chunk_t))
        if max_val > 1.0:
            normalized_chunk_t = normalized_chunk_t / max_val * 0.999

        out_filename = f"{stem_name}_seg{chunk_idx:04d}.wav"
        out_filepath = output_dir / out_filename

        sf.write(str(out_filepath), normalized_chunk_t, target_sr, subtype="PCM_16")

        tags = [t.strip().lower() for t in stem_name.replace("_", "-").split("-") if t.strip()]
        prompt = default_prompt if default_prompt else f"production track, {', '.join(tags)}"

        record = {
            "file_name": out_filename,
            "prompt": prompt,
            "lyrics": "",
            "sample_rate": target_sr,
            "duration": segment_duration,
            "tags": tags
        }
        records.append(record)
        chunk_idx += 1

    return records


def main():
    parser = argparse.ArgumentParser(description="Preprocess audio files for ACE-Step LoRA training.")
    parser.add_argument("--input-dir", type=str, default=".", help="Directory containing raw WAV/FLAC/MP3 files.")
    parser.add_argument("--output-dir", type=str, default="./processed_dataset", help="Directory to save sliced segments.")
    parser.add_argument("--sr", type=int, default=44100, help="Target sample rate (default: 44100).")
    parser.add_argument("--duration", type=float, default=30.0, help="Segment length in seconds (default: 30.0).")
    parser.add_argument("--overlap", type=float, default=2.0, help="Window overlap in seconds (default: 2.0).")
    parser.add_argument("--lufs", type=float, default=-14.0, help="Integrated LUFS target (default: -14.0).")
    parser.add_argument("--default-prompt", type=str, default="october 7, emotional alternative rap ballad, 80 bpm, c minor", help="Default prompt description.")

    args = parser.parse_args()

    in_path = Path(args.input_dir)
    out_path = Path(args.output_dir)
    out_path.mkdir(parents=True, exist_ok=True)

    audio_files = [f for f in in_path.rglob("*") if f.suffix.lower() in [".wav", ".flac", ".mp3", ".aiff"]]
    print(f"\nDiscovered {len(audio_files)} source audio files for preprocessing.")

    all_metadata = []

    for file_path in tqdm(audio_files, desc="Slicing and Normalizing"):
        file_records = process_audio_file(
            input_path=file_path,
            output_dir=out_path,
            target_sr=args.sr,
            segment_duration=args.duration,
            overlap=args.overlap,
            target_lufs=args.lufs,
            default_prompt=args.default_prompt
        )
        all_metadata.extend(file_records)

    manifest_file = out_path / "metadata.jsonl"
    with open(manifest_file, "w", encoding="utf-8") as f:
        for item in all_metadata:
            f.write(json.dumps(item, ensure_ascii=False) + "\n")

    print(f"\n[✓] Preprocessing complete:")
    print(f" - Output segments: {len(all_metadata)} WAV files")
    print(f" - Directory: {out_path}")
    print(f" - Training Manifest: {manifest_file}\n")


if __name__ == "__main__":
    main()
