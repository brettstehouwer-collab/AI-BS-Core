import subprocess
import numpy as np
import wave
import os

# Convert mp3 to wav with ffmpeg
wav_path = r"C:\AI-BS\saved_data\video_inspect\october_full.wav"
mp3_path = r"C:\AI-BS\FacebookData\October 7v2 (Add Vocal) (Remastered) (Remove Section).mp3"

if not os.path.exists(wav_path):
    subprocess.run(["ffmpeg", "-y", "-i", mp3_path, "-ac", "1", "-ar", "44100", wav_path], capture_output=True)

with wave.open(wav_path, 'rb') as wf:
    sr = wf.getframerate()
    n_frames = wf.getnframes()
    y = np.frombuffer(wf.readframes(n_frames), dtype=np.int16).astype(np.float32) / 32768.0

duration = len(y) / sr
print(f"Total Song Duration: {duration:.3f}s ({duration/60:.2f} mins)")

points = [
    ("Wave Studio Selection In", 24.962),
    ("Wave Studio Second Marker", 45.064),
    ("Suno Studio Playhead (Bar 34.2.2)", 94.159),
    ("Prior Detected Breakpoint", 41.58)
]

for label, t in points:
    idx = int(t * sr)
    window = y[max(0, idx - int(sr*0.5)) : min(len(y), idx + int(sr*0.5))]
    rms = np.sqrt(np.mean(window**2))
    peak = np.max(np.abs(window))
    
    print(f"\n--- Point: {label} at {t:.3f}s ---")
    print(f"  RMS: {rms:.4f}, Peak: {peak:.4f}")
    
    micro = y[max(0, idx - int(sr*0.05)) : min(len(y), idx + int(sr*0.05))]
    diff = np.abs(np.diff(micro))
    max_jump = np.max(diff) if len(diff) > 0 else 0
    print(f"  Max sample jump in 50ms: {max_jump:.4f}")

# Calculate autocorrelation tempo detection around 70-140 BPM
# Low-pass filter energy envelope
hop = int(sr * 0.01) # 10ms
envelope = []
for i in range(0, len(y), hop):
    chunk = y[i:i+hop]
    if len(chunk) == 0: break
    envelope.append(np.sum(chunk**2))
envelope = np.array(envelope)
diff_env = np.maximum(0, np.diff(envelope))

# Autocorrelation
corr = np.correlate(diff_env, diff_env, mode='full')
corr = corr[len(diff_env)-1:]

# Check lags for 60 to 160 BPM
# lag in frames = (60 / bpm) / 0.01s = 6000 / bpm
bpms = np.linspace(60, 160, 1001)
scores = []
for b in bpms:
    lag = int(round(6000.0 / b))
    if lag < len(corr):
        scores.append((corr[lag], b))

scores.sort(reverse=True)
print("\n--- TOP DETECTED TEMPOS ---")
for s, b in scores[:5]:
    print(f"  {b:.1f} BPM (score={s:.2e})")
