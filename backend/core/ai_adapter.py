"""AI Adapter core logic."""

import asyncio
import json
import os
import re
from pathlib import Path

import chromadb
import fitz
import httpx

from core.matrix_docs import init_project

# Track global progress in-memory (synced with disk)
ADAPTATION_TASKS = {}
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
    """Chunking by lines to handle PDF extraction"""
    paragraphs = text.split('\n')
    chunks = []
    current_chunk = ""
    for p in paragraphs:
        if len(current_chunk) + len(p) > max_chars:
            if current_chunk.strip():
                chunks.append(current_chunk.strip())
            current_chunk = p + "\n"
        else:
            current_chunk += p + "\n"
    if current_chunk.strip():
        chunks.append(current_chunk.strip())
    return chunks


def _save_state(project_dir: Path, project_name: str, state_dict: dict):
    """Save the adaptation state to disk."""
    state_file = project_dir / "adaptation_state.json"
    with open(state_file, "w", encoding="utf-8") as f:
        json.dump(state_dict, f, indent=2)
    ADAPTATION_TASKS[project_name] = state_dict


def load_all_states(projects_dir: Path = Path("C:/AI-BS/screenplay_projects")):
    """Load all adaptation states from disk on startup."""
    if not projects_dir.exists():
        return
    for proj_path in projects_dir.iterdir():
        if proj_path.is_dir():
            state_file = proj_path / "adaptation_state.json"
            if state_file.exists():
                try:
                    with open(state_file, "r", encoding="utf-8") as f:
                        state = json.load(f)
                        ADAPTATION_TASKS[proj_path.name] = state
                except OSError:
                    pass


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


def cancel_adaptation(project_name: str) -> bool:
    """Cancels an ongoing adaptation task for a project."""
    if project_name in ADAPTATION_TASKS:
        ADAPTATION_TASKS[project_name]["status"] = "canceled"
        ADAPTATION_TASKS[project_name]["error"] = "Adaptation canceled by user"
    project_dir = Path(f"C:/AI-BS/screenplay_projects/{project_name}")
    state_file = project_dir / "adaptation_state.json"
    if state_file.exists():
        try:
            with open(state_file, "r", encoding="utf-8") as f:
                s = json.load(f)
            s["status"] = "canceled"
            s["error"] = "Adaptation canceled by user"
            with open(state_file, "w", encoding="utf-8") as f:
                json.dump(s, f, indent=2)
        except Exception:
            pass
    return True

def reset_adaptation(project_name: str) -> bool:
    """Clears in-memory and on-disk state so a fresh adaptation can start."""
    if project_name in ADAPTATION_TASKS:
        del ADAPTATION_TASKS[project_name]
    project_dir = Path(f"C:/AI-BS/screenplay_projects/{project_name}")
    state_file = project_dir / "adaptation_state.json"
    if state_file.exists():
        try:
            state_file.unlink()
        except Exception:
            pass
    return True

def get_all_adaptation_tasks():
    """Returns a dict of all known adaptation tasks from memory and disk."""
    tasks = dict(ADAPTATION_TASKS)
    projects_dir = Path("C:/AI-BS/screenplay_projects")
    if projects_dir.exists():
        for p in projects_dir.iterdir():
            if p.is_dir() and p.name not in tasks:
                sf = p / "adaptation_state.json"
                if sf.exists():
                    try:
                        with open(sf, "r", encoding="utf-8") as f:
                            tasks[p.name] = json.load(f)
                    except Exception:
                        pass
    return tasks


async def adapt_book_to_screenplay(
        file_path: Path,
        project_name: str,
        adaptation_type: str = "Feature Film (Spec Script)",
        book_style: str = "Fiction Novel / Narrative"):
    """Background task to process PDF/documents and write to project."""

    # Initialize project
    project = init_project(project_name)
    state_file = project.project_dir / "adaptation_state.json"
    chunks_file = project.project_dir / "chunks.json"

    # Check if we're resuming
    is_resuming = False
    state = {
        "status": "processing",
        "progress": 0,
        "current_chunk": 0,
        "total_chunks": 0,
        "previous_summary": "This is the very beginning of the story.",
        "adaptation_type": adaptation_type,
        "book_style": book_style
    }

    if state_file.exists() and chunks_file.exists():
        with open(state_file, "r", encoding="utf-8") as f:
            saved_state = json.load(f)
            if saved_state.get("status") in ["processing", "error"]:
                state = saved_state
                state["status"] = "processing"
                if "error" in state:
                    del state["error"]
                is_resuming = True

    _save_state(project.project_dir, project_name, state)

    try:
        chunks = []
        if is_resuming:
            # Load chunks from disk
            with open(chunks_file, "r", encoding="utf-8") as f:
                chunks = json.load(f)
        else:
            # 1. Extract Text from any supported format (.pdf, .docx, .epub, .txt, .rtf, .md, .fdx)
            full_text = _extract_text_from_file(file_path)
            if not full_text or not full_text.strip():
                raise ValueError(f"Could not extract readable text from {file_path.name}")

            # 2. Chunk text
            chunks = await _chunk_text(full_text)

            # Save chunks to disk
            with open(chunks_file, "w", encoding="utf-8") as f:
                json.dump(chunks, f)

            # --- PHASE 4.7 RAG Ingestion ---
            try:
                chroma_client = chromadb.HttpClient(
                    host="127.0.0.1", port=8001
                )
                safe_name = "".join([c for c in project_name if c.isalnum()])
                collection_name = f"screenplay_{safe_name.lower()}"
                try:
                    chroma_client.delete_collection(name=collection_name)
                except Exception:
                    pass
                collection = chroma_client.create_collection(
                    name=collection_name
                )

                chunk_embeddings = []
                for chunk in chunks:
                    emb = await _generate_embedding(chunk)
                    chunk_embeddings.append(emb if emb else [0.0] * 768)

                collection.add(
                    ids=[f"chunk_{idx}" for idx in range(len(chunks))],
                    embeddings=chunk_embeddings,
                    documents=chunks,
                    metadatas=[{"chunk_index": idx} for idx in range(len(chunks))]
                )
                print(
                    f"[AI Adapter] Ingested {len(chunks)} chunks into ChromaDB."
                )
            except Exception as e:
                print(f"[AI Adapter] ChromaDB ingestion skipped/failed: {e}")

            # Ensure file starts clean
            project.write_screenplay(f"Title: {project_name}\n\n")

        total_chunks = len(chunks)
        state["total_chunks"] = total_chunks
        _save_state(project.project_dir, project_name, state)

        start_idx = int(state.get("current_chunk", 0))
        previous_summary = state.get(
            "previous_summary", "This is the very beginning of the story."
        )

        # 3. Process each chunk
        for i in range(start_idx, total_chunks):
            # Check for user cancellation
            if ADAPTATION_TASKS.get(project_name, {}).get("status") == "canceled":
                print(f"[AI Adapter] Adaptation for {project_name} was canceled.")
                return

            chunk = chunks[i]

            state["current_chunk"] = i
            state["progress"] = int((i / total_chunks) * 100)
            _save_state(project.project_dir, project_name, state)

            # --- PHASE 4.7 RAG Retrieval ---
            retrieved_memory = ""
            try:
                chroma_client = chromadb.HttpClient(
                    host="127.0.0.1", port=8001
                )
                safe_name = "".join([c for c in project_name if c.isalnum()])
                collection_name = f"screenplay_{safe_name.lower()}"
                collection = chroma_client.get_or_create_collection(
                    name=collection_name
                )

                current_vector = await _generate_embedding(chunk)
                if current_vector:
                    results = collection.query(
                        query_embeddings=[current_vector],
                        n_results=3,
                        where={"chunk_index": {"$lt": i}}  # Only PAST chunks
                    )
                    if results and results.get('documents'):
                        if results['documents'][0]:
                            retrieved_memory = "\n\n".join(
                                results['documents'][0]
                            )
                            print("[AI Adapter] Retrieved past context.")
            except httpx.RequestError as e:
                print(f"[AI Adapter] ChromaDB Retrieval offline: {e}")

            if retrieved_memory:
                safe_context = (
                    f"High-Speed SSD Memory (Relevant past chunks):\n"
                    f"{retrieved_memory}\n\nImmediate Rolling Summary:\n"
                    f"{previous_summary}"
                )
            else:
                safe_context = previous_summary

            # Pass chunk directly as Ollama natively supports UTF-8
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

            max_retries = 3
            success = False
            adapted_text = ""
            new_summary = ""
            for target_model in FALLBACK_MODELS:
                if success:
                    break
                for attempt in range(max_retries):
                    try:
                        async with httpx.AsyncClient(timeout=None) as client:
                            response = await client.post(
                                f"{OLLAMA_HOST}/api/chat",
                                json={
                                    "model": target_model,
                                    "messages": [
                                        {"role": "user", "content": prompt}
                                    ],
                                    "stream": False,
                                    "options": {
                                        "temperature": 0.3,
                                        "num_predict": 2500,
                                        "num_ctx": 8192
                                    }
                                }
                            )

                            if response.status_code == 404:
                                print(
                                    f"[AI Adapter] Model "
                                    f"'{target_model}' not found in Ollama pool."
                                )
                                break  # Break retry loop and try next model

                            if response.status_code != 200:
                                raise RuntimeError(
                                    f"HTTP {response.status_code}"
                                )

                            result = response.json()
                            candidate_text = result.get("message", {}).get("content", "").strip()

                            # Refusal check: NEVER allow canned LLM refusal boilerplate to enter the screenplay
                            if _is_model_refusal(candidate_text):
                                print(f"[AI Adapter] Detected canned refusal on model '{target_model}' for chunk {i+1}. Attempting next model...")
                                break

                            adapted_text = candidate_text

                            # Robust Markdown Stripper
                            adapted_text = re.sub(
                                r"^```(?:fountain|markdown)?\s*\n",
                                "", adapted_text, flags=re.IGNORECASE
                            )
                            adapted_text = re.sub(
                                r"\n```\s*$", "", adapted_text
                            )

                            # Extract summary
                            if ("<SUMMARY>" in adapted_text and
                                    "</SUMMARY>" in adapted_text):
                                start_idx = adapted_text.rfind("<SUMMARY>")
                                end_idx = adapted_text.rfind("</SUMMARY>")
                                new_summary = adapted_text[
                                    start_idx + 9:end_idx
                                ].strip()
                                adapted_text = adapted_text[:start_idx].strip()
                            else:
                                # Fallback: keep previous valid summary rather than raw text
                                new_summary = previous_summary

                            # Secondary validation on extracted summary
                            if _is_model_refusal(new_summary):
                                new_summary = previous_summary

                            success = True
                            break  # Success, break out of retry loop
                    except (httpx.RequestError, RuntimeError, ValueError) as e:
                        if attempt == max_retries - 1:
                            err_msg = (
                                f"[AI Adapter Error] Inference failed for "
                                f"{target_model} after 3 attempts: {str(e)}"
                            )
                            print(err_msg)
                            with open(
                                "C:/AI-BS/ai_error.log",
                                "a",
                                encoding="utf-8"
                            ) as err_log:
                                err_log.write(err_msg + "\n")
                        else:
                            print(
                                f"[AI Adapter] Chunk {i + 1} "
                                f"with {target_model} failed "
                                f"({e}), retrying in 5s..."
                            )
                            await asyncio.sleep(5)

            if not success:
                raise RuntimeError("All fallback models and retries failed.")

            # Append to current screenplay
            current_script = project.read_screenplay()
            new_script = current_script + "\n\n" + adapted_text
            project.write_screenplay(new_script)

            # Save context for next chunk
            previous_summary = new_summary

            # Update state after chunk success
            state["current_chunk"] = i + 1
            state["previous_summary"] = previous_summary
            state["progress"] = int(((i + 1) / total_chunks) * 100)
            _save_state(project.project_dir, project_name, state)

        state["progress"] = 100
        state["status"] = "complete"
        _save_state(project.project_dir, project_name, state)

    except (httpx.RequestError, RuntimeError, OSError, ValueError) as e:
        state["status"] = "error"
        state["error"] = str(e)
        _save_state(project.project_dir, project_name, state)
        print(f"[AI Adapter Error] {e}")
