import whisper
import json
import os

audio_path = r"C:\AI-BS\audio for vid.mp3"
output_json = r"C:\AI-BS\saved_data\audio_for_vid_transcription.json"

os.makedirs(r"C:\AI-BS\saved_data", exist_ok=True)

print("Loading Whisper model (base)...")
model = whisper.load_model("base", device="cuda" if whisper.torch.cuda.is_available() else "cpu")

print(f"Transcribing {audio_path} with word timestamps...")
result = model.transcribe(audio_path, word_timestamps=True, verbose=True)

with open(output_json, "w", encoding="utf-8") as f:
    json.dump(result, f, indent=2, ensure_ascii=False)

print(f"Transcription saved to {output_json}")
print("\nFull Extracted Text:")
print(result["text"])
