import os
import re
import json
import time
import asyncio
from pathlib import Path
from typing import Dict, Any, Optional, List
import whisper

SCREENPLAY_ROOT = Path("C:/AI-BS/screenplay_projects")
AUDIO_TRANSCRIBE_TASKS: Dict[str, Dict[str, Any]] = {}


def format_seconds(seconds: float) -> str:
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    if h > 0:
        return f"{h:02d}:{m:02d}:{s:02d}"
    return f"{m:02d}:{s:02d}"


def run_transcription_sync(project_name: str, model_size: str = "base"):
    AUDIO_TRANSCRIBE_TASKS[project_name] = {
        "status": "processing",
        "progress": 5,
        "step": "Loading Whisper AI speech model...",
        "start_time": time.time()
    }
    
    try:
        audio_dir = SCREENPLAY_ROOT / project_name / "audio"
        if not audio_dir.exists():
            AUDIO_TRANSCRIBE_TASKS[project_name] = {"status": "error", "message": "Audio directory not found"}
            return
            
        audio_files = list(audio_dir.glob("*.wav")) + list(audio_dir.glob("*.mp3")) + list(audio_dir.glob("*.m4a"))
        if not audio_files:
            AUDIO_TRANSCRIBE_TASKS[project_name] = {"status": "error", "message": "No audio files found to transcribe"}
            return

        target_file = audio_files[0]
        AUDIO_TRANSCRIBE_TASKS[project_name]["step"] = f"Loading model '{model_size}'..."
        AUDIO_TRANSCRIBE_TASKS[project_name]["progress"] = 15
        
        model = whisper.load_model(model_size)
        
        AUDIO_TRANSCRIBE_TASKS[project_name]["step"] = f"Transcribing '{target_file.name}'..."
        AUDIO_TRANSCRIBE_TASKS[project_name]["progress"] = 35

        # Transcribe
        result = model.transcribe(str(target_file), language="en", verbose=False)
        
        AUDIO_TRANSCRIBE_TASKS[project_name]["progress"] = 80
        AUDIO_TRANSCRIBE_TASKS[project_name]["step"] = "Formatting documents & syncing vector memory..."

        transcripts_dir = SCREENPLAY_ROOT / project_name / "transcripts"
        transcripts_dir.mkdir(parents=True, exist_ok=True)

        full_text = result.get("text", "").strip()
        segments = result.get("segments", [])

        # 1. Plain Text
        txt_path = transcripts_dir / "audio_transcript.txt"
        txt_path.write_text(full_text, encoding="utf-8")

        # 2. Markdown Document with Timestamps
        md_lines = [
            f"# Audio Adaptation Transcript: {project_name}",
            f"**Source Audio:** `{target_file.name}`  ",
            f"**Transcribed At:** {time.strftime('%Y-%m-%d %H:%M:%S')}  ",
            f"**Total Segments:** {len(segments)}  \n",
            "---",
            "\n## Full Transcript with Timecodes\n"
        ]

        fountain_lines = [
            f"Title: {project_name.upper()} - AUDIO TRANSCRIPT",
            "Credit: Transcribed from ElevenLabs Audio Adaptation",
            "Author: Brett Stehouwer",
            f"Draft date: {time.strftime('%Y-%m-%d')}\n"
        ]

        current_heading_time = -999
        for seg in segments:
            s_time = seg.get("start", 0)
            e_time = seg.get("end", 0)
            text = seg.get("text", "").strip()
            timecode = f"[{format_seconds(s_time)} - {format_seconds(e_time)}]"
            
            md_lines.append(f"**{timecode}** {text}\n")

            # Fountain formatting (every ~3 minutes creates a scene heading)
            if s_time - current_heading_time >= 180:
                current_heading_time = s_time
                fountain_lines.append(f"\nINT. AUDIO CHAPTER - {format_seconds(s_time)} - DAY\n")
            
            fountain_lines.append(f"NARRATOR\n{text}\n")

        md_path = transcripts_dir / "audio_transcript.md"
        md_path.write_text("\n".join(md_lines), encoding="utf-8")

        fountain_path = transcripts_dir / "audio_transcript.fountain"
        fountain_path.write_text("\n".join(fountain_lines), encoding="utf-8")

        # 3. JSON Segments
        json_path = transcripts_dir / "audio_transcript.json"
        json_path.write_text(json.dumps(result, indent=2), encoding="utf-8")

        # 4. Auto-Sync into ChromaDB Project Collection
        try:
            from core.project_rag import get_chroma_client, get_project_collection_name, get_embedding_sync
            client = get_chroma_client()
            col = client.get_or_create_collection(get_project_collection_name(project_name))
            
            # Chunk into ~200 word sections for ChromaDB
            chunk_size = 5
            c_ids = []
            c_docs = []
            c_metas = []
            c_embs = []
            for i in range(0, len(segments), chunk_size):
                chunk_segs = segments[i:i+chunk_size]
                chunk_text = " ".join([s.get("text", "").strip() for s in chunk_segs])
                start_tc = format_seconds(chunk_segs[0].get("start", 0))
                doc_id = f"audio_chunk_{i//chunk_size + 1}"
                emb = get_embedding_sync(chunk_text)
                
                c_ids.append(doc_id)
                c_docs.append(f"[AUDIO ADAPTATION TIMECODE {start_tc}]\n{chunk_text}")
                c_embs.append(emb)
                c_metas.append({
                    "type": "audio_transcript",
                    "timecode": start_tc,
                    "project": project_name
                })
            if c_docs:
                col.upsert(ids=c_ids, embeddings=c_embs, documents=c_docs, metadatas=c_metas)
                print(f"[AudioTranscriber] Upserted {len(c_docs)} audio transcript vectors into ChromaDB.")
        except Exception as c_err:
            print(f"[AudioTranscriber] ChromaDB upsert warning: {c_err}")

        elapsed = round(time.time() - AUDIO_TRANSCRIBE_TASKS[project_name]["start_time"], 2)
        AUDIO_TRANSCRIBE_TASKS[project_name] = {
            "status": "completed",
            "progress": 100,
            "step": "Transcription complete & synced to Vector DB!",
            "elapsed_seconds": elapsed,
            "total_segments": len(segments),
            "md_path": str(md_path),
            "txt_path": str(txt_path),
            "fountain_path": str(fountain_path)
        }
    except Exception as e:
        print(f"[AudioTranscriber] Error: {e}")
        AUDIO_TRANSCRIBE_TASKS[project_name] = {
            "status": "error",
            "message": str(e)
        }


def get_project_transcription(project_name: str) -> Dict[str, Any]:
    transcripts_dir = SCREENPLAY_ROOT / project_name / "transcripts"
    md_path = transcripts_dir / "audio_transcript.md"
    json_path = transcripts_dir / "audio_transcript.json"

    if not md_path.exists():
        return {
            "status": "not_found",
            "has_transcript": False,
            "task": AUDIO_TRANSCRIBE_TASKS.get(project_name, {"status": "idle"})
        }

    content = md_path.read_text(encoding="utf-8", errors="ignore")
    return {
        "status": "success",
        "has_transcript": True,
        "transcript_markdown": content,
        "task": AUDIO_TRANSCRIBE_TASKS.get(project_name, {"status": "completed"})
    }
