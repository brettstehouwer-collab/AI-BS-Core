import wave
import numpy as np

# Let's inspect the audio in latency timing.mp4
# When does audio start playing in AI-BS vs Suno?
audio_path = r"C:\AI-BS\saved_data\video_inspect\latency_timing\audio.wav"

with wave.open(audio_path, 'rb') as wf:
    sample_rate = wf.getframerate()
    num_frames = wf.getnframes()
    audio = np.frombuffer(wf.readframes(num_frames), dtype=np.int16)

# Find silence / sound transitions
frame_step = int(sample_rate * 0.1) # 100ms
energies = []
for i in range(0, len(audio), frame_step):
    chunk = audio[i:i+frame_step]
    if len(chunk) == 0: break
    rms = np.sqrt(np.mean(chunk.astype(np.float64)**2))
    energies.append((i / sample_rate, rms))

# Print notable points (when playback starts/stops)
print("=== AUDIO TIMELINE OF RECORDING ===")
for t, rms in energies[::10]: # every 1 second
    status = "### AUDIO PLAYING" if rms > 1000 else "--- SILENT/QUIET"
    print(f"[{t:5.1f}s] RMS: {rms:6.1f}  {status}")
