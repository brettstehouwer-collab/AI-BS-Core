import whisper
import json
import os

vocals_path = r"C:\AI-BS\MP4 medial screen recordings-video\facebook_reel_isolated_vocals.mp3"
output_json = r"C:\AI-BS\saved_data\facebook_reel_transcription.json"

os.makedirs(r"C:\AI-BS\saved_data", exist_ok=True)

print("Loading Whisper model (base)...")
model = whisper.load_model("base", device="cuda" if whisper.torch.cuda.is_available() else "cpu")

print("Transcribing with word timestamps...")
result = model.transcribe(vocals_path, word_timestamps=True, verbose=True)

with open(output_json, "w", encoding="utf-8") as f:
    json.dump(result, f, indent=2, ensure_ascii=False)

print(f"Transcription saved to {output_json}")
print("Full Text:")
print(result["text"])
