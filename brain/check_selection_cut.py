import wave
import numpy as np

wav_path = r"C:\AI-BS\saved_data\video_inspect\october_full.wav"

with wave.open(wav_path, 'rb') as wf:
    sr = wf.getframerate()
    n_frames = wf.getnframes()
    audio = np.frombuffer(wf.readframes(n_frames), dtype=np.int16).astype(np.float32) / 32768.0

# Cut at 24.962 to 26.311
t1 = 24.962
t2 = 26.311

idx1 = int(t1 * sr)
idx2 = int(t2 * sr)

pre_cut = audio[idx1 - int(sr * 0.5) : idx1]
inside_cut = audio[idx1 : idx2]
post_cut = audio[idx2 : idx2 + int(sr * 0.5)]

print(f"Pre-cut (24.46s - 24.96s) RMS: {np.sqrt(np.mean(pre_cut**2)):.4f}")
print(f"Inside Selection (24.96s - 26.31s) RMS: {np.sqrt(np.mean(inside_cut**2)):.4f}")
print(f"Post-cut (26.31s - 26.81s) RMS: {np.sqrt(np.mean(post_cut**2)):.4f}")

# Check minimum energy in the selection
sub_rms = [np.sqrt(np.mean(inside_cut[i:i+int(sr*0.05)]**2)) for i in range(0, len(inside_cut)-int(sr*0.05), int(sr*0.05))]
print("Min RMS inside selection:", min(sub_rms) if sub_rms else "N/A")
print("Max RMS inside selection:", max(sub_rms) if sub_rms else "N/A")
