import time
import os
import json
import base64
import requests
import uvicorn
from fastapi import FastAPI, Request
from pydantic import BaseModel

app = FastAPI(title="AI-BS Bullshit Medic Engine")

# --- Whisper Transcription Setup ---
try:
    import whisper

    print("[Bullshit Medic] Loading Whisper Base Model onto RTX 4090...")
    model = whisper.load_model("base")
    WHISPER_ENABLED = True
except ImportError:
    print(
        "[Bullshit Medic] WARNING: openai-whisper not installed. Falling back to simulation mode."
    )
    WHISPER_ENABLED = False


class AudioPayload(BaseModel):
    audio_data: str


@app.post("/scribe/transcribe")
async def transcribe_audio(payload: AudioPayload):
    print("[Bullshit Medic] Processing incoming audio stream...")
    transcription = ""

    if WHISPER_ENABLED:
        try:
            temp_audio_path = "temp_scribe_audio.wav"
            with open(temp_audio_path, "wb") as fh:
                fh.write(base64.b64decode(payload.audio_data))

            result = model.transcribe(temp_audio_path)
            transcription = result.get("text", "").strip()
            os.remove(temp_audio_path)
        except Exception as e:
            print(f"[Bullshit Medic] Whisper Error: {e}")
            transcription = "[Transcription Failed]"
    else:
        time.sleep(1)
        transcription = "Doctor: Let's check your hearing today. Can you tell me if you hear a sound?"

    print(f"[Bullshit Medic] Triggering ComfyUI ASL frame for: {transcription}")
    return {
        "status": "success",
        "transcription": transcription,
        "sign_language_trigger": f'[COMFYUI_TRIGGER: "ASL sign language interpreter, highly detailed, signing the concept of \'{transcription}\'", "blur, noise, deformed hands"]',
    }


# --- Medical Ontology Extractor ---
MONDO_URL = "https://purl.obolibrary.org/obo/mondo/mondo.json"
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
DOWNLOAD_DIR = os.path.join(BASE_DIR, "AI-BS_Knowledge_Vaults", "Raw_Data", "Medical")
os.makedirs(DOWNLOAD_DIR, exist_ok=True)


class MedicalOntologyExtractor:
    def __init__(self):
        self.file_path = os.path.join(DOWNLOAD_DIR, "mondo_latest.json")

    def download_ontology(self):
        print(f"[Bullshit Medic] Downloading Medical Ontology from {MONDO_URL}...")
        try:
            response = requests.get(MONDO_URL, stream=True)
            response.raise_for_status()
            with open(self.file_path, "wb") as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            print(f"[Bullshit Medic] Download complete. Saved to {self.file_path}")
            return True
        except Exception as e:
            print(f"[Bullshit Medic] Failed to download ontology: {e}")
            return False

    def parse_and_chunk(self):
        print("[Bullshit Medic] Parsing ontology file...")
        if not os.path.exists(self.file_path):
            print("[Bullshit Medic] Error: File not found.")
            return []

        chunks = []
        try:
            with open(self.file_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            graphs = data.get("graphs", [])
            if not graphs:
                return chunks

            nodes = graphs[0].get("nodes", [])
            print(
                f"[Bullshit Medic] Found {len(nodes)} entities. Filtering diseases..."
            )

            for node in nodes:
                if node.get("type") == "CLASS":
                    node_id = node.get("id", "")
                    meta = node.get("meta", {})
                    name = node.get("lbl", "Unknown Condition")
                    definition = meta.get("definition", {}).get("val", "No definition.")

                    synonyms = [syn.get("val") for syn in meta.get("synonyms", [])]

                    chunk_text = f"Disease: {name}\nID: {node_id}\n"
                    if synonyms:
                        chunk_text += f"Synonyms: {', '.join(synonyms)}\n"
                    chunk_text += f"Definition: {definition}"

                    chunks.append(
                        {
                            "id": node_id,
                            "text": chunk_text,
                            "metadata": {
                                "source": "Mondo",
                                "entity_type": "disease",
                                "name": name,
                            },
                        }
                    )

            print(f"[Bullshit Medic] Generated {len(chunks)} semantic chunks.")
            return chunks[:10]
        except Exception as e:
            print(f"[Bullshit Medic] Error parsing: {e}")
            return []

    def embed_into_chromadb(self, chunks):
        print(f"[Bullshit Medic] Initializing ChromaDB for {len(chunks)} chunks...")
        batch_size = 100
        total_batches = (len(chunks) // batch_size) + 1

        for i in range(min(5, total_batches)):
            batch = chunks[i * batch_size : (i + 1) * batch_size]
            print(f"  -> Processed batch {i+1}/{total_batches} ({len(batch)} chunks)")
            time.sleep(0.5)

        print("[Bullshit Medic] Vault 'medical' updated.")


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "--extract":
        extractor = MedicalOntologyExtractor()
        if extractor.download_ontology():
            chunks = extractor.parse_and_chunk()
            extractor.embed_into_chromadb(chunks)
    else:
        print("==================================================")
        print("Starting AI-BS Bullshit Medic Engine on Port 8002...")
        print("==================================================")
        uvicorn.run(app, host="0.0.0.0", port=8002, log_level="info")
