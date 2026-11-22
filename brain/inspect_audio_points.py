import librosa
import numpy as np

audio_path = r"C:\AI-BS\FacebookData\October 7v2 (Add Vocal) (Remastered) (Remove Section).mp3"
y, sr = librosa.load(audio_path, sr=44100, mono=True)

duration = len(y) / sr
print(f"Total Song Duration: {duration:.3f}s ({duration/60:.2f} mins)")

# Check points:
# Point 1: 24.962s
# Point 2: 45.064s
# Point 3: 94.159s (01:34.159 from Suno Studio)

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
    
    # Calculate zero crossings and spectral centroid to detect sharp transitions or splices
    spec_cent = librosa.feature.spectral_centroid(y=window, sr=sr)
    mean_cent = np.mean(spec_cent) if len(spec_cent) > 0 else 0
    
    print(f"\n--- Point: {label} at {t:.3f}s ---")
    print(f"  RMS: {rms:.4f}, Peak: {peak:.4f}, Spectral Centroid: {mean_cent:.1f}Hz")
    
    # Check if there is a sudden jump in waveform in a +/- 50ms window
    micro = y[max(0, idx - int(sr*0.05)) : min(len(y), idx + int(sr*0.05))]
    diff = np.abs(np.diff(micro))
    max_jump = np.max(diff) if len(diff) > 0 else 0
    print(f"  Max sample jump in 50ms: {max_jump:.4f}")

# Check tempo / BPM of this song using librosa
tempo, beat_frames = librosa.beat.beat_track(y=y, sr=sr)
print(f"\nEstimated Tempo (Librosa): {float(tempo):.2f} BPM")
