import subprocess
import numpy as np
import wave
import os

source_wav = r"C:\AI-BS\saved_data\video_inspect\october_full.wav"
repaired_master_wav = r"C:\AI-BS\saved_data\audio_stems\october_7v2_remastered\October_7v2_Master_Repaired.wav"
repaired_master_mp3 = r"C:\AI-BS\saved_data\audio_stems\october_7v2_remastered\October_7v2_Master_Repaired.mp3"

with wave.open(source_wav, 'rb') as wf:
    sr = wf.getframerate()
    n_frames = wf.getnframes()
    audio = np.frombuffer(wf.readframes(n_frames), dtype=np.int16).astype(np.float32) / 32768.0

print(f"Sample Rate: {sr}, Length: {len(audio)} samples ({len(audio)/sr:.2f}s)")

# We will apply dual-spot repair:
# Spot 1: 24.962s to 26.311s (The exact spot highlighted in Stehouwer Wave Studio)
# Spot 2: 41.58s to 45.06s (The second transition spot)

audio_repaired = np.copy(audio)

# --- REPAIR SPOT 1: 24.962s - 26.311s ---
# In Spot 1, between 25.5s and 26.35s there is an energy drop followed by an abrupt jump at 26.40s
t1_start = 24.962
t1_end = 26.350
idx1_start = int(t1_start * sr)
idx1_end = int(t1_end * sr)

# Smooth envelope crossfade and tone preservation
fade_len = int(sr * 0.15) # 150ms crossfade
pre_segment = audio[idx1_start - fade_len : idx1_start]
post_segment = audio[idx1_end : idx1_end + fade_len]

# Generate synthesized harmonic fill at 85 BPM beat grid
# 85 BPM beat length = 60 / 85 = 0.70588s
# Crossfade into a clean, tone-matched bridge
t_span = np.linspace(0, (idx1_end - idx1_start) / sr, idx1_end - idx1_start)
# Key of song: A minor (440Hz, 523Hz, 659Hz) / C major
pad = 0.04 * (np.sin(2 * np.pi * 220 * t_span) + 0.5 * np.sin(2 * np.pi * 330 * t_span) + 0.5 * np.sin(2 * np.pi * 440 * t_span))
window_hann = np.hanning(len(t_span))
pad = pad * window_hann

# Apply smooth crossfade to audio_repaired
# Interpolate between pre and post smoothly
alpha = np.linspace(0, 1, idx1_end - idx1_start)
# Keep existing audio but smooth out the jarring dip and spike
smoothed_region = (1 - alpha) * audio[idx1_start] + alpha * audio[idx1_end] + pad
# Soft blend with original audio to preserve natural texture without clipping
audio_repaired[idx1_start:idx1_end] = 0.5 * audio[idx1_start:idx1_end] + 0.5 * smoothed_region

# --- REPAIR SPOT 2: 41.58s to 45.06s ---
idx2_start = int(41.58 * sr)
idx2_end = int(44.00 * sr)
t_span2 = np.linspace(0, (idx2_end - idx2_start) / sr, idx2_end - idx2_start)
pad2 = 0.05 * (np.sin(2 * np.pi * 220 * t_span2) + 0.5 * np.sin(2 * np.pi * 330 * t_span2)) * np.hanning(len(t_span2))
audio_repaired[idx2_start:idx2_end] = audio_repaired[idx2_start:idx2_end] + pad2

# Normalize without clipping
peak = np.max(np.abs(audio_repaired))
if peak > 0.98:
    audio_repaired = audio_repaired * (0.98 / peak)

# Save to repaired master WAV & MP3
out_int16 = (audio_repaired * 32767).astype(np.int16)
with wave.open(repaired_master_wav, 'wb') as wf:
    wf.setnchannels(1)
    wf.setsampwidth(2)
    wf.setframerate(sr)
    wf.writeframes(out_int16.tobytes())

print("Saved repaired WAV to:", repaired_master_wav)

# Convert to MP3
subprocess.run(["ffmpeg", "-y", "-i", repaired_master_wav, "-b:a", "320k", repaired_master_mp3], capture_output=True)
print("Saved repaired MP3 to:", repaired_master_mp3)
