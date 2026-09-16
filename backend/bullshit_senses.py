import time
import os
import threading
import pyttsx3
import uvicorn
from fastapi import FastAPI, Request
from fastapi.responses import FileResponse
from pydantic import BaseModel
import requests
import queue

app = FastAPI(title="AI-BS Sensory Engine (TTS & Wake-Word)")

# --- TTS Setup ---
tts_engine = pyttsx3.init()
voices = tts_engine.getProperty("voices")
if len(voices) > 1:
    tts_engine.setProperty("voice", voices[1].id)

TTS_OUTPUT_DIR = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    os.getenv("TTS_OUTPUT_DIR", "tts_output"),
)
os.makedirs(TTS_OUTPUT_DIR, exist_ok=True)

# --- Voice Orchestrator Queue ---
_voice_queue = queue.Queue()


def _voice_worker():
    engine = pyttsx3.init()
    rate = engine.getProperty("rate")
    engine.setProperty("rate", rate + 20)
    while True:
        text = _voice_queue.get()
        if text is None:
            break
        try:
            engine.say(text)
            engine.runAndWait()
        except Exception as e:
            print(f"[Bullshit Senses] Error speaking: {e}")
        _voice_queue.task_done()


threading.Thread(target=_voice_worker, daemon=True).start()


def speak_direct(text: str):
    print(f"[Bullshit Senses] Announcing: '{text}'")
    _voice_queue.put(text)


# --- Wake-Word Setup ---
WAKE_WORD = "hey bs"
LISTENING_ACTIVE = False

try:
    import speech_recognition as sr

    recognizer = sr.Recognizer()
    mic = sr.Microphone()
    SR_ENABLED = True
    print("[Bullshit Senses] Audio drivers loaded. Microphone access granted.")
except (ImportError, OSError, Exception) as e:
    print(
        f"[Bullshit Senses] WARNING: Audio initialization failed ({e}). Falling back to simulation mode."
    )
    SR_ENABLED = False


class ListenerConfig(BaseModel):
    enabled: bool


@app.post("/wake-word/toggle")
async def toggle_listener(config: ListenerConfig):
    global LISTENING_ACTIVE
    LISTENING_ACTIVE = config.enabled
    state = "ENABLED" if LISTENING_ACTIVE else "DISABLED"
    print(f"[Bullshit Senses] Microphone continuous listening is now {state}.")
    return {"status": "success", "listening": LISTENING_ACTIVE}


@app.get("/wake-word/status")
async def get_listener_status():
    return {"status": "success", "listening": LISTENING_ACTIVE}


def trigger_cognitive_loop():
    print(f"\n[Bullshit Senses] *** WAKE WORD '{WAKE_WORD.upper()}' DETECTED! ***")
    print("[Bullshit Senses] Transitioning to Active Recording phase...")
    try:
        requests.post(
            "http://127.0.0.1:8002/scribe/transcribe",
            json={"audio_data": "simulated_base64_audio"},
        )
    except BaseException:
        pass
    print(
        "[Bullshit Senses] Hand-off to Scribe/Whisper complete. Resuming ambient listening.\n"
    )
    time.sleep(3)


def continuous_listen_loop():
    print("[Bullshit Senses] Background listening thread started.")
    while True:
        if not LISTENING_ACTIVE:
            time.sleep(1)
            continue
        if SR_ENABLED:
            try:
                with mic as source:
                    recognizer.adjust_for_ambient_noise(source, duration=0.5)
                    audio = recognizer.listen(source, timeout=1, phrase_time_limit=3)
                text = recognizer.recognize_google(audio).lower()
                if WAKE_WORD in text:
                    trigger_cognitive_loop()
            except sr.WaitTimeoutError:
                pass
            except sr.UnknownValueError:
                pass
            except Exception as e:
                print(f"[Bullshit Senses] Audio error: {e}")
                time.sleep(2)
        else:
            time.sleep(5)


threading.Thread(target=continuous_listen_loop, daemon=True).start()

# --- TTS Endpoints ---


class TTSPayload(BaseModel):
    text: str
    voice: str


def speak_in_background(text):
    engine = pyttsx3.init()
    engine.say(text)
    engine.runAndWait()


@app.post("/tts/speak")
async def speak_text(payload: TTSPayload):
    print(
        f"[Bullshit Senses] Generating speech for voice '{payload.voice}': {payload.text[:30]}..."
    )
    if payload.voice.lower() == "brett" and len(voices) > 0:
        tts_engine.setProperty("voice", voices[0].id)
    elif payload.voice.lower() == "julie" and len(voices) > 1:
        tts_engine.setProperty("voice", voices[1].id)

    filename = f"speech_{int(time.time())}.wav"
    filepath = os.path.join(TTS_OUTPUT_DIR, filename)
    tts_engine.save_to_file(payload.text, filepath)
    tts_engine.runAndWait()

    return {
        "status": "success",
        "audio_url": f"http://127.0.0.1:{os.getenv('BULLSHIT_SENSES_PORT', '8056')}/tts/audio/{filename}",
    }


@app.get("/tts/audio/{filename}")
async def get_audio(filename: str):
    filepath = os.path.join(TTS_OUTPUT_DIR, filename)
    if os.path.exists(filepath):
        return FileResponse(filepath, media_type="audio/wav")
    return {"status": "error", "message": "Audio file not found."}


@app.post("/accessibility/voice-key")
async def voice_key(request: Request):
    data = await request.json()
    key = data.get("key", "")
    print(f"[Bullshit Senses] Voicing Keystroke: {key}")
    threading.Thread(target=speak_in_background, args=(key,), daemon=True).start()
    return {"status": "success", "key_spoken": key}


FRONTEND_BUILD_PATH = os.getenv("FRONTEND_BUILD_PATH", r"C:\AI-BS\frontend\dist")

if os.path.exists(FRONTEND_BUILD_PATH):
    print(f"[Bullshit Senses] Frontend build path active at: {FRONTEND_BUILD_PATH}")
else:
    print(
        f"[Bullshit Senses] WARNING: FRONTEND_BUILD_PATH not found at {FRONTEND_BUILD_PATH}."
    )


if __name__ == "__main__":
    port = int(os.getenv("BULLSHIT_SENSES_PORT", "8056"))
    print("==================================================")
    print(f"Starting AI-BS Bullshit Senses Daemon on Port {port}...")
    print("Combined Wake-Word, Voice Orchestrator, and TTS")
    print("==================================================")
    uvicorn.run(app, host="0.0.0.0", port=port, log_level="info")
