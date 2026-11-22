import wave
import numpy as np

wav_path = r"C:\AI-BS\saved_data\video_inspect\october_full.wav"

with wave.open(wav_path, 'rb') as wf:
    sr = wf.getframerate()
    n_frames = wf.getnframes()
    audio = np.frombuffer(wf.readframes(n_frames), dtype=np.int16).astype(np.float32) / 32768.0

# Analyze region from 24.0s to 27.5s (Selection In: 24.962s, Length: 1.349s)
start_sec = 24.0
end_sec = 27.5
start_idx = int(start_sec * sr)
end_idx = int(end_sec * sr)
sub = audio[start_idx:end_idx]

# Check RMS and zero crossing rate in 50ms windows
window_size = int(sr * 0.05) # 50ms
for i in range(0, len(sub) - window_size, int(sr * 0.05)):
    w = sub[i:i+window_size]
    rms = np.sqrt(np.mean(w**2))
    t = start_sec + i / sr
    zcr = np.mean(np.diff(w > 0) != 0)
    print(f"Time {t:.3f}s: RMS = {rms:.4f}, ZCR = {zcr:.3f}")

# Also check around 45.064s (Second marker from video)
print("\n--- Region around 44.5s - 46.5s ---")
start_sec2 = 44.5
end_sec2 = 46.5
sub2 = audio[int(start_sec2*sr):int(end_sec2*sr)]
for i in range(0, len(sub2) - window_size, int(sr * 0.05)):
    w = sub2[i:i+window_size]
    rms = np.sqrt(np.mean(w**2))
    t = start_sec2 + i / sr
    zcr = np.mean(np.diff(w > 0) != 0)
    print(f"Time {t:.3f}s: RMS = {rms:.4f}, ZCR = {zcr:.3f}")
