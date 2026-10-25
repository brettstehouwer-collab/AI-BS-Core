"""AI Adapter core logic."""

import asyncio
import json
import os
import re
from pathlib import Path

import chromadb
import fitz
import httpx

from core.adaptation_store import (
    ADAPTATION_TASKS, OwnershipLost, reserve_adaptation, claim_job, check_owned,
    update_job, retain_chunks, commit_chunk, load_all_states,
    cancel_adaptation, reset_adaptation, get_all_adaptation_tasks,
)

# Track global progress in-memory (synced with disk)
OLLAMA_HOST = os.environ.get("OLLAMA_HOST_EDRIVE", "http://127.0.0.1:11435")
if not OLLAMA_HOST.startswith("http"):
    if OLLAMA_HOST == "0.0.0.0":
        OLLAMA_HOST = "http://127.0.0.1:11435"
    else:
        OLLAMA_HOST = f"http://{OLLAMA_HOST}"
if ":" not in OLLAMA_HOST.replace("http://", "").replace("https://", ""):
    OLLAMA_HOST = f"{OLLAMA_HOST}:11435"
FALLBACK_MODELS = [
    "stehouwer_dolphin:latest",
    "stehouwer_hermes:latest",
    "stehouwer_llm:latest",
    "llama3.1:latest",
    "qwen2.5-coder:latest",
    "mixtral:latest",
    "llama3:latest"
]


def _is_model_refusal(text: str) -> bool:
    """Detects canned LLM safety refusal boilerplate so it is never inserted into outputs."""
    if not text or not text.strip():
        return True
    refusal_patterns = [
        r"I cannot (?:create|generate|write|depict|fulfill|help|provide|discuss|share|comment|disclose)",
        r"I am unable to (?:create|generate|write|depict|fulfill|help|provide|discuss|share|comment|disclose)",
        r"I can't (?:create|generate|write|depict|fulfill|help|provide|discuss|share|comment|disclose)",
        r"As an AI (?:language model|assistant)",
        r"I apologize, but I cannot",
        r"personal relationship",
        r"content that depicts",
        r"against my (?:safety|content|ethical) (?:guidelines|policy|policies)",
        r"violates (?:our|the) safety policy",
        r"Is there anything else I can help you with\?",
        r"I'm sorry, but I can't fulfill this request"
    ]
    for pat in refusal_patterns:
        if re.search(pat, text, re.IGNORECASE):
            return True
    return False


import zipfile
import xml.etree.ElementTree as ET

def _extract_text_from_file(file_path: Path) -> str:
    """Universal text extractor supporting PDF, DOCX, EPUB, TXT, RTF, MD, Fountain, and FDX."""
    suffix = file_path.suffix.lower()
    
    # 1. PDF or EPUB via PyMuPDF (fitz)
    if suffix in [".pdf", ".epub"]:
        try:
            doc = fitz.open(str(file_path))
            full_text = ""
            for page in doc:
                text_page = page.get_text()
                if isinstance(text_page, str):
                    full_text += text_page + "\n"
            doc.close()
            if full_text.strip():
                return full_text
        except Exception as e:
            print(f"[AI Adapter] fitz extraction failed for {suffix}: {e}")

    # 2. DOCX extraction
    if suffix in [".docx", ".doc"]:
        try:
            import docx
            doc = docx.Document(str(file_path))
            full_text = "\n".join([p.text for p in doc.paragraphs if p.text.strip()])
            if full_text.strip():
                return full_text
        except Exception:
            pass
        # Fallback: extract word/document.xml directly from docx zip
        try:
            with zipfile.ZipFile(str(file_path)) as z:
                xml_content = z.read("word/document.xml")
                tree = ET.fromstring(xml_content)
                paragraphs = []
                for p in tree.iter('{http://schemas.openxmlformats.org/wordprocessingml/2006/main}p'):
                    texts = [node.text for node in p.iter('{http://schemas.openxmlformats.org/wordprocessingml/2006/main}t') if node.text]
                    if texts:
                        paragraphs.append("".join(texts))
                full_text = "\n\n".join(paragraphs)
                if full_text.strip():
                    return full_text
        except Exception as e:
            print(f"[AI Adapter] docx zip fallback failed: {e}")

    # 3. Final Draft XML (.fdx)
    if suffix == ".fdx":
        try:
            tree = ET.parse(str(file_path))
            root = tree.getroot()
            paragraphs = []
            for p in root.iter('Paragraph'):
                texts = [node.text for node in p.iter('Text') if node.text]
                if texts:
                    paragraphs.append("".join(texts))
            full_text = "\n\n".join(paragraphs)
            if full_text.strip():
                return full_text
        except Exception as e:
            print(f"[AI Adapter] FDX extraction failed: {e}")

    # 4. RTF extraction
    if suffix == ".rtf":
        try:
            raw_rtf = file_path.read_text(encoding="utf-8", errors="ignore")
            clean_text = re.sub(r"\{\*?\\[^{}]+?\}|[{}]|\\\n?[A-Za-z]+\d*|\\[^A-Za-z0-9]", " ", raw_rtf)
            clean_text = re.sub(r"\s+", " ", clean_text)
            if clean_text.strip():
                return clean_text
        except Exception as e:
            print(f"[AI Adapter] RTF extraction failed: {e}")

    # Binary formats must never silently turn into Latin-1 gibberish.
    if suffix in {'.pdf', '.epub', '.docx', '.doc', '.fdx'}:
        raise ValueError(f'No readable text could be extracted from {suffix}; retained source bytes are unchanged.')

    # 5. Plaintext fallback (.txt, .md, .markdown, .fountain, etc.)
    for enc in ["utf-8", "utf-8-sig", "latin-1", "cp1252"]:
        try:
            return file_path.read_text(encoding=enc)
        except UnicodeDecodeError:
            continue

    return file_path.read_text(encoding="utf-8", errors="ignore")


def _get_adaptation_rules(adaptation_type: str, book_style: str = "") -> str:
    """Returns specialized Hollywood, Television, Previs, and Theatrical adaptation directives, combining source style with target format."""
    norm_type = adaptation_type.strip().lower()
    norm_style = book_style.strip().lower()
    
    style_directives = ""
    if "autobiography" in norm_style or "memoir" in norm_style or "biopic" in norm_style:
        style_directives = """SOURCE MANUSCRIPT STYLE: AUTOBIOGRAPHY / MEMOIR / BIOPIC
1. VOICE-OVER TRANSLATION: Convert first-person introspective prose reflections into intimate Voice-Over dialogue (e.g. CHARACTER NAME (V.O.)).
2. FLASHBACK SEQUENCES: Convert historical recollections into dynamic flashback scenes with scene headings (e.g. FLASHBACK - INT. PARENT'S HOME - 1978).
3. SUBJECTIVE VISUALS: Translate internal thoughts and emotional states into external physical actions, sensory details, and character eye contact."""
    elif "non-fiction" in norm_style or "crime" in norm_style or "investigative" in norm_style or "history" in norm_style:
        style_directives = """SOURCE MANUSCRIPT STYLE: NON-FICTION / INVESTIGATIVE / TRUE CRIME
1. ON-SCREEN GRAPHICS & TIME: Use superimpositions for timestamps, locations, and declassified dossier details (e.g. SUPER: "BERLIN - NOVEMBER 9, 1989").
2. ARCHIVAL & MONTAGE: Translate explanatory exposition into visual montages and archival inserts (e.g. [MONTAGE: WIRE RECORDINGS & TRANSCRIPTS]).
3. FACTUAL DIALOGUE: Maintain high-stakes forensic realism in interrogations, briefing rooms, and journalistic dialogues."""
    elif "stage" in norm_style or "theatre" in norm_style:
        style_directives = """SOURCE MANUSCRIPT STYLE: THEATRICAL DRAMA / STAGE PLAY
1. DIALOGUE MUSICALITY: Preserve extended acoustic dialogue exchanges, character monologues, and dramatic subtext.
2. STAGE SPATIALITY: Convert literary narration into physical set blocking, exits, and entrances."""
    elif "short" in norm_style or "flash" in norm_style:
        style_directives = """SOURCE MANUSCRIPT STYLE: SHORT STORY / FLASH FICTION
1. CONCENTRATED PACING: Strip extraneous subplots, plunging directly into the core crisis.
2. SHARP RESOLUTION: Build towards a swift, memorable visual climax."""
    else:
        style_directives = """SOURCE MANUSCRIPT STYLE: FICTION NOVEL / NARRATIVE PROSE
1. DRAMATIZE EXPOSITION: Convert worldbuilding lore, psychological musings, and descriptive narration into cinematic action beats and subtext.
2. ACTIVE CONFRONTATION: Externalize character dilemmas through high-friction interactions, dialogue choices, and physical behavior."""

    format_directives = ""
    if "audio" in norm_type or "podcast" in norm_type:
        format_directives = """TARGET FORMAT: AUDIO DRAMA / SCRIPTED PODCAST
1. SOUND DESIGN CUES: Emphasize auditory storytelling. Insert uppercase sound effects markers on separate lines: [SFX: Sound of thunder echoing in the distance], [SFX: Footsteps crunching on gravel].
2. MUSICAL ATMOSPHERE: Insert cues for musical underscores (e.g., [MUSIC: Tension strings swell]).
3. ACOUSTIC ENVIRONMENT: Detail spatial acoustics in scene descriptions (e.g., "Muffled behind closed door", "Wide echoey cathedral")."""

    elif "tv" in norm_type or "pilot" in norm_type or ("drama" in norm_type and "audio" not in norm_type):
        if "comedy" in norm_type or "sitcom" in norm_type or "30" in norm_type:
            format_directives = """TARGET FORMAT: 30-MINUTE TV COMEDY / SITCOM PILOT
1. STRUCTURE: Cold Open, Act One, Act Two, and Tag.
2. COMEDY RHYTHM: Convert prose into crisp, dialogue-driven comedic banter. Keep action lines minimal (1-2 sentences maximum).
3. PARENTHETICALS: Use parentheticals for comedic delivery, pauses, and physical reactions (e.g. (deadpan), (beat), (spit-takes)).
4. ACT HEADERS: Clearly format act breaks on their own line: COLD OPEN, ACT ONE, ACT TWO, TAG."""
        else:
            format_directives = """TARGET FORMAT: 1-HOUR TV DRAMA PILOT (NETWORK / STREAMING)
1. STRUCTURE: Teaser + 5-Act or 6-Act episodic structure.
2. PACING & ACT BREAKS: Insert uppercase act headers on their own line where the prose hits a dramatic cliffhanger or revelation (TEASER, ACT ONE, ACT TWO, ACT THREE, ACT FOUR, ACT FIVE, TAG).
3. ENSEMBLE EXPOSURE: Establish distinct character introductions with age and physical traits in ALL CAPS upon first appearance.
4. COMMERCIAL CLIFFHANGERS: Build scene tension towards natural act break peaks."""
    
    elif "director" in norm_type or "shooting" in norm_type or "previs" in norm_type:
        format_directives = """TARGET FORMAT: DIRECTOR'S SHOOTING SCRIPT & 3D PREVIS
1. CINEMATOGRAPHY CUES: Integrate specific camera framing and lens movement into Action lines (e.g. [WIDE SHOT], [CLOSE-UP ON:], [TRACKING SHOT], [LOW ANGLE], [P.O.V.]).
2. LIGHTING & ATMOSPHERE: Explicitly specify lighting dynamics in Scene Headings and Action (e.g. "Chiaroscuro shadow", "Harsh fluorescent backlight", "Golden hour haze").
3. BLOCKING & COVERAGE: Detail physical actor vectors, sightlines, and movement cues to prepare the scene for 3D Unreal Engine sequencing."""

    elif "stage" in norm_type or "play" in norm_type:
        format_directives = """TARGET FORMAT: THEATRICAL STAGE PLAY
1. STAGE STRUCTURE: Use ACT I, SCENE I headers.
2. BLOCKING & ENTRANCES: Explicitly write stage directions, entrances, and exits in brackets or parentheticals (e.g., [ENTER STAGE LEFT], [CROSSES DOWNSTAGE RIGHT], [EXITS THROUGH FRENCH DOORS]).
3. THEATRICAL DIALOGUE: Prioritize monologue depth, acoustic projection, and physical set interaction over rapid cinematic cuts."""

    elif "short" in norm_type:
        format_directives = """TARGET FORMAT: SHORT FILM (10-15 MINUTE ARC)
1. TIGHT ECONOMY: Strip all non-essential exposition. Every action line must push the immediate visual conflict.
2. RAPID INCITING INCIDENT: Plunge characters directly into the core crisis within the first scene heading.
3. VISUAL CLIMAX: Build to a sharp, impactful thematic punchline or visual reversal."""

    elif "series" in norm_type or "limited" in norm_type or "mini" in norm_type:
        format_directives = """TARGET FORMAT: LIMITED SERIES / MINI-SERIES EPISODIC SCRIPT
1. SERIALIZED STORYTELLING: Weave A-plot and B-plot character subplots into cinematic scenes.
2. ATMOSPHERIC PACING: Allow scenes to breathe with descriptive sensory details, subtext-rich dialogue, and psychological depth.
3. EPISODIC CLIFFHANGER: Conclude scene sequences with strong hooks into subsequent episodes."""

    else:
        format_directives = """TARGET FORMAT: HOLLYWOOD FEATURE FILM (3-ACT SPEC SCRIPT)
1. 3-ACT STRUCTURE: Follow standard studio screenplay format. Convert internal prose into external visual actions and subtext-driven dialogue.
2. SHOW, DON'T TELL: Translate character feelings into physical behavior, eye contact, and vocal tone.
3. HOLLYWOOD SPEC STANDARDS: Strict Courier 12pt element hierarchy (Scene Heading, Action, Character, Dialogue, Parenthetical, Transition)."""

    return f"{style_directives}\n\n{format_directives}"


async def _chunk_text(text: str, max_chars: int = 6000):
    """Keep source order and bound even documents without paragraph breaks."""
    if max_chars < 1:
        raise ValueError('Chunk size must be positive')
    chunks, pending = [], ''
    for line in text.splitlines(keepends=True):
        while len(line) > max_chars:
            if pending.strip():
                chunks.append(pending.strip())
            pending = ''
            chunks.append(line[:max_chars])
            line = line[max_chars:]
        if len(pending) + len(line) > max_chars:
            if pending.strip():
                chunks.append(pending.strip())
            pending = line
        else:
            pending += line
    if pending.strip():
        chunks.append(pending.strip())
    return chunks


async def _generate_embedding(text: str) -> list[float]:
    """Generates an embedding vector using Ollama's nomic-embed-text."""
    url = f"{OLLAMA_HOST}/api/embeddings"
    payload = {
        "model": "nomic-embed-text",
        "prompt": text
    }
    async with httpx.AsyncClient() as client:
        try:
            r = await client.post(url, json=payload, timeout=30.0)
            if r.status_code == 200:
                return r.json().get("embedding", [])
        except httpx.RequestError as e:
            print(f"[AI Adapter] Embedding error: {e}")
    return []


async def _infer_chunk(prompt, project_name, job_id, worker_id, previous_summary):
    for target_model in FALLBACK_MODELS:
        for attempt in range(3):
            check_owned(project_name, job_id, worker_id)
            try:
                async with httpx.AsyncClient(timeout=httpx.Timeout(600.0, connect=10.0)) as client:
                    response = await client.post(
                        f"{OLLAMA_HOST}/api/chat",
                        json={"model": target_model, "messages": [{"role": "user", "content": prompt}],
                              "stream": False, "options": {"temperature": 0.3, "num_predict": 2500, "num_ctx": 8192}})
                check_owned(project_name, job_id, worker_id)
                if response.status_code == 404:
                    break
                if response.status_code != 200:
                    raise RuntimeError(f"Model returned HTTP {response.status_code}")
                candidate = response.json().get('message', {}).get('content', '').strip()
                if _is_model_refusal(candidate):
                    break
                candidate = re.sub(r"^```(?:fountain|markdown)?\s*\n", "", candidate, flags=re.IGNORECASE)
                candidate = re.sub(r"\n```\s*$", "", candidate)
                summary = previous_summary
                if '<SUMMARY>' in candidate and '</SUMMARY>' in candidate:
                    start, end = candidate.rfind('<SUMMARY>'), candidate.rfind('</SUMMARY>')
                    if end > start:
                        proposed = candidate[start + 9:end].strip()
                        if not _is_model_refusal(proposed):
                            summary = proposed
                        candidate = candidate[:start].strip()
                if not candidate.strip() or _is_model_refusal(candidate):
                    break
                return candidate, summary
            except (httpx.RequestError, RuntimeError, ValueError):
                check_owned(project_name, job_id, worker_id)
                if attempt < 2:
                    await asyncio.sleep(5)
                    check_owned(project_name, job_id, worker_id)
    raise RuntimeError('All configured models failed to produce an adaptation.')


async def adapt_book_to_screenplay(file_path: Path, project_name: str,
        adaptation_type: str = 'Feature Film (Spec Script)',
        book_style: str = 'Fiction Novel / Narrative', job_id: str = None):
    """Process only a durably reserved new-project job; legacy calls cannot write."""
    if not job_id:
        return
    try:
        directory, source, state = claim_job(project_name, job_id)
    except OwnershipLost:
        return
    worker_id = state['worker_id']
    try:
        # The durable source path and options are authoritative, never caller paths.
        adaptation_type, book_style = state['adaptation_type'], state['book_style']
        full_text = await asyncio.to_thread(_extract_text_from_file, source)
        check_owned(project_name, job_id, worker_id)
        if not full_text or not full_text.strip():
            raise ValueError(f'Could not extract readable text from {source.suffix} source')
        chunks = await _chunk_text(full_text)
        check_owned(project_name, job_id, worker_id)
        retain_chunks(project_name, job_id, worker_id, chunks)

        # A unique collection retains prior projects/jobs and never deletes a vault.
        collection = None
        try:
            import hashlib
            identity = hashlib.sha256((str(directory.resolve()) + job_id).encode()).hexdigest()[:40]
            client = chromadb.HttpClient(host='127.0.0.1', port=8001)
            collection = client.get_or_create_collection(name='screenplay_' + identity)
            for index, chunk in enumerate(chunks):
                check_owned(project_name, job_id, worker_id)
                embedding = await _generate_embedding(chunk)
                check_owned(project_name, job_id, worker_id)
                if not embedding:
                    raise RuntimeError('Embedding service returned no vector; no substitute vector was stored.')
                collection.add(ids=[f'chunk_{index}'], embeddings=[embedding],
                    documents=[chunk], metadatas=[{'chunk_index': index, 'job_id': job_id}])
            update_job(project_name, job_id, worker_id, rag_status='ready')
        except OwnershipLost:
            return
        except Exception as error:
            collection = None
            update_job(project_name, job_id, worker_id, rag_status='unavailable', rag_error=str(error))

        previous_summary = state['previous_summary']
        for i, chunk in enumerate(chunks):
            check_owned(project_name, job_id, worker_id)
            retrieved_memory = ''
            if collection is not None and i > 0:
                try:
                    vector = await _generate_embedding(chunk)
                    check_owned(project_name, job_id, worker_id)
                    if vector:
                        results = collection.query(query_embeddings=[vector], n_results=min(3, i),
                            where={'chunk_index': {'$lt': i}})
                        documents = results.get('documents') or []
                        if documents and documents[0]:
                            retrieved_memory = '\n\n'.join(documents[0])
                except OwnershipLost:
                    return
                except Exception as error:
                    update_job(project_name, job_id, worker_id, rag_status='retrieval_unavailable', rag_error=str(error))
            safe_context = (f'Relevant past source segments:\n{retrieved_memory}\n\n'
                            f'Immediate Rolling Summary:\n{previous_summary}') if retrieved_memory else previous_summary
            safe_chunk = chunk
            specific_rules = _get_adaptation_rules(adaptation_type, book_style)
            prompt = f"""EDITORIAL DIRECTIVE:
You are an expert Hollywood dramatic screenwriter and adaptation engine. You are adapting an authored personal memoir and biographical true story into a professional screenplay format for: {adaptation_type}.
This is creative biographical storytelling and dramatic film/television writing.

{specific_rules}

Universal Script Rules:
1. ABSOLUTELY NO PREAMBLE, introductions, title pages, or conversational text. Start directly with the first Scene Heading.
2. ABSOLUTELY NO MARKDOWN formatting (Do NOT use ** or * for bold/italics).
3. Transitions (e.g., CUT TO:, FADE IN:) must be UPPERCASE, on their own line, without any markdown asterisks. Use transitions where the prose indicates a significant shift in time or location.
4. SPACING AND ALIGNMENT:
   - If a character is speaking off-screen or in voiceover, append (O.S.) or (V.O.) appropriately to the Character Name (e.g., "CHARACTER NAME (V.O.)").
   - Use Parentheticals to convey essential tone, action, or emotion implied by the prose during dialogue.
5. ELEMENT SCANNING: Translate introspective prose and emotional reflections into (V.O.) voiceover dialogue, physical action beats, and actor blocking.

CRITICAL INSTRUCTION:
At the very end of your response, you MUST provide a brief 2-sentence narrative summary of the current plot state, active characters, and current location. You must wrap this summary exactly in <SUMMARY> and </SUMMARY> tags. This is crucial for narrative continuity in the next chunk.

Previous Plot Context:
{safe_context}

New Segment to Adapt:
{safe_chunk}"""
            adapted_text, new_summary = await _infer_chunk(prompt, project_name, job_id, worker_id, previous_summary)
            check_owned(project_name, job_id, worker_id)
            commit_chunk(project_name, job_id, worker_id, i, adapted_text, new_summary)
            previous_summary = new_summary
        update_job(project_name, job_id, worker_id, progress=100, status='complete')
    except OwnershipLost:
        return
    except asyncio.CancelledError:
        try:
            update_job(project_name, job_id, worker_id, status='interrupted', error='Worker stopped; retained files preserved.')
        except OwnershipLost:
            pass
        raise
    except Exception as error:
        try:
            update_job(project_name, job_id, worker_id, status='error', error=str(error))
        except OwnershipLost:
            pass
