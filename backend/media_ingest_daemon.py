import os
import time
import json
import logging
import subprocess

# [AUTO-HEALER PATCH] Mitigated crash on next line
import httpx
import uuid
import threading
from pathlib import Path
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

# Setup logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("media_ingest_daemon")

WATCH_DIR = r"E:\AI-BS\MP4 medial screen recordings"
TEMP_DIR = r"E:\AI-BS\temp_media"
OLLAMA_API = "http://127.0.0.1:11434/api/generate"

# Ensure directories exist
os.makedirs(WATCH_DIR, exist_ok=True)
os.makedirs(TEMP_DIR, exist_ok=True)

# Try to get webhook URL from environment or .env
DISCORD_WEBHOOK_URL = os.environ.get("DISCORD_WEBHOOK_URL", "").strip('"')
if not DISCORD_WEBHOOK_URL:
    try:
        env_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env"
        )
        if os.path.exists(env_path):
            with open(env_path, "r", encoding="utf-8") as f:
                for line in f:
                    if line.startswith("DISCORD_WEBHOOK_URL="):
                        DISCORD_WEBHOOK_URL = line.split("=", 1)[1].strip().strip('"')
    except Exception:
        pass


def send_discord_alert(message: str):
    if not DISCORD_WEBHOOK_URL:
        return
    try:
        import urllib.request

        req = urllib.request.Request(
            DISCORD_WEBHOOK_URL,
            data=json.dumps({"content": message}).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                "User-Agent": "AI-BS-Daemon/1.0",
            },
        )
        urllib.request.urlopen(req, timeout=10.0)
    except Exception as e:
        logger.error(f"Failed to send Discord alert: {e}")


import queue

processing_queue = queue.Queue()


class MediaIngestHandler(FileSystemEventHandler):
    def on_created(self, event):
        if event.is_directory:
            return
        logger.info(f"Queued for processing: {event.src_path}")
        # Wait a moment for file to finish copying, then add to the sequential processing queue
        threading.Timer(5.0, lambda: processing_queue.put(event.src_path)).start()

    def process_file_sync(self, filepath: str):
        file_path = Path(filepath)
        if not file_path.exists():
            return

        ext = file_path.suffix.lower()
        logger.info(f"Processing media from queue: {file_path.name}")

        try:
            if ext in [".mp4", ".avi", ".mkv", ".mov"]:
                self.process_video(file_path)
            elif ext in [".mp3", ".wav", ".m4a"]:
                self.process_audio(file_path)
            elif ext in [".jpg", ".jpeg", ".png"]:
                self.process_image(file_path)
            else:
                logger.warning(f"Unsupported media type: {ext}")
        except Exception as e:
            logger.error(f"Failed to process {file_path.name}: {e}")

    def process_image(self, file_path: Path):
        import base64

        with open(file_path, "rb") as f:
            img_b64 = base64.b64encode(f.read()).decode("utf-8")

        logger.info("Analyzing image with llava...")
        response = httpx.post(
            OLLAMA_API,
            json={
                "model": "llava:latest",
                "prompt": "Describe this image in extreme detail. What is happening? What is the user looking at?",
                "images": [img_b64],
                "stream": False,
            },
            timeout=300.0,
        )

        description = response.json().get("response", "")
        self.inject_memory(f"User saved an image: {file_path.name}", description)

    def process_audio(self, file_path: Path):
        transcript = self._transcribe_audio(file_path)
        if transcript:
            self.inject_memory(f"User recorded audio: {file_path.name}", transcript)

    def process_video(self, file_path: Path):
        logger.info(f"Extracting audio from {file_path.name}...")
        wav_path = os.path.join(TEMP_DIR, f"{uuid.uuid4()}.wav")
        subprocess.run(
            [
                "ffmpeg",
                "-y",
                "-i",
                str(file_path),
                "-vn",
                "-acodec",
                "pcm_s16le",
                "-ar",
                "16000",
                "-ac",
                "1",
                wav_path,
            ],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )

        transcript = self._transcribe_audio(Path(wav_path))
        if os.path.exists(wav_path):
            os.remove(wav_path)

        logger.info(f"Extracting sample frame from {file_path.name}...")
        frame_path = os.path.join(TEMP_DIR, f"{uuid.uuid4()}.jpg")
        # Extract a frame roughly 30% into the video
        subprocess.run(
            [
                "ffmpeg",
                "-y",
                "-i",
                str(file_path),
                "-ss",
                "00:00:10",
                "-vframes",
                "1",
                frame_path,
            ],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )

        visual_desc = "No visual data extracted."
        if os.path.exists(frame_path):
            import base64

            with open(frame_path, "rb") as f:
                img_b64 = base64.b64encode(f.read()).decode("utf-8")

            logger.info("Analyzing video frame with llava...")
            try:
                response = httpx.post(
                    OLLAMA_API,
                    json={
                        "model": "llava:latest",
                        "prompt": "Describe what is happening on this screen. What application or game or activity is the user doing?",
                        "images": [img_b64],
                        "stream": False,
                    },
                    timeout=300.0,
                )
                visual_desc = response.json().get("response", "")
            except Exception as e:
                logger.error(f"Llava error: {e}")
            os.remove(frame_path)

        logger.info("Synthesizing episodic memory...")
        prompt = f"""
You are an AI processing a raw memory of the user's activity.
Filename: {file_path.name}
Visual Context: {visual_desc}
Audio Transcript: {transcript}

Synthesize this into a cohesive 1-paragraph summary of what the user was doing and what was said. Write it from the perspective of an AI observing its user.
        """
        response = httpx.post(
            OLLAMA_API,
            json={"model": "stehouwer_llm:latest", "prompt": prompt, "stream": False},
            timeout=300.0,
        )

        final_summary = response.json().get("response", "")
        self.inject_memory(
            f"User recorded video activity: {file_path.name}", final_summary
        )

        # Marketing-safe Discord Alert
        msg = f"🚀 **AI-BS Evolution Engine**: A new ambient memory has been integrated!\n> The system just independently analyzed raw visual and auditory data to learn new capabilities. (Classified Neural Update)\n> *Source Type: Video Analysis*"
        send_discord_alert(msg)
        logger.info("Video processing complete and memory injected.")

    def _transcribe_audio(self, wav_path: Path) -> str:
        logger.info(f"Transcribing {wav_path.name} with faster-whisper...")
        try:
            from faster_whisper import WhisperModel

            model = WhisperModel("base", device="cpu", compute_type="int8")
            segments, info = model.transcribe(str(wav_path), beam_size=5)
            transcript = " ".join([segment.text for segment in segments])
            return transcript
        except Exception as e:
            logger.error(f"Transcription failed: {e}")
            return "Audio transcription failed."

    def inject_memory(self, title: str, content: str):
        logger.info("Injecting memory into ChromaDB...")
        try:
            from memory_service import get_memory_service
            import asyncio

            async def do_inject():
                memory = get_memory_service()
                await memory.add_heuristic(
                    documents=[content],
                    metadatas=[{"source": "ambient_ingestor", "title": title}],
                    ids=[f"episodic-{uuid.uuid4()}"],
                )

            asyncio.run(do_inject())
            logger.info("Successfully added to AI-BS Context Memory.")
        except Exception as e:
            logger.error(f"Failed to inject memory: {e}")


def queue_worker(handler):
    while True:
        filepath = processing_queue.get()
        if filepath is None:
            break
        handler.process_file_sync(filepath)
        processing_queue.task_done()
        logger.info("Cooling down for 15 seconds before processing the next file...")
        time.sleep(15)


if __name__ == "__main__":
    event_handler = MediaIngestHandler()
    worker_thread = threading.Thread(
        target=queue_worker, args=(event_handler,), daemon=True
    )
    worker_thread.start()

    observer = Observer()
    observer.schedule(event_handler, WATCH_DIR, recursive=False)
    observer.start()
    logger.info(f"Ambient Media Ingestor watching: {WATCH_DIR}")

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()
