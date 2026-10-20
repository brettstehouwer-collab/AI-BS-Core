import sys
import time
sys.path.insert(0, r"C:\AI-BS")

from native_studio.audio_kernel import AudioEngine

e = AudioEngine()
st = e.start()
print(f"Engine started: {st.mode} at {st.samplerate}Hz on {st.device}")

print("Auditioning Kick (Track 0)...")
e.audition(0)
time.sleep(0.3)

print("Auditioning Snare (Track 1)...")
e.audition(1)
time.sleep(0.3)

print("Auditioning Synth Lead (Track 7)...")
e.audition(7, note=64)
time.sleep(0.3)

print("Playing pattern for 1.5 seconds...")
e.set_step(0, 0, True)
e.set_step(1, 4, True)
e.play(True)
time.sleep(1.5)
e.play(False)
e.stop()
print("Playback test complete.")
