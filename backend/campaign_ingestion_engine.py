"""
Stehouwer AI Bulk Subscriber Ingestion & Sorting Engine
=======================================================
100% Free / Open-Source stack:
  - pandas + pyarrow        -- multi-format streaming ingestion
  - sentence-transformers   -- local vector embeddings (all-MiniLM-L6-v2)
  - scikit-learn            -- K-Means cluster assignment (no cloud calls)
  - Ollama (if running)     -- local LLM campaign copy generation fallback

Supported file formats:
  Tier 1 -- Tabular:   .csv, .tsv, .txt, .xlsx, .xls, .json, .jsonl
  Tier 2 -- Binary:    .parquet, .csv.gz, .zip (auto-decompressed)
"""

from __future__ import annotations

import io
import json
import logging
import re
import time
import uuid
import zipfile
import gzip
from typing import Dict, List, Optional

import numpy as np
import pandas as pd
import requests

logger = logging.getLogger("ai_bs.campaign_ai")

# ---------------------------------------------------------------------------
#  Constants
# ---------------------------------------------------------------------------
EMAIL_REGEX = re.compile(r"^[a-zA-Z0-9_.+\-]+@[a-zA-Z0-9\-]+\.[a-zA-Z0-9.\-]+$")

AUDIENCE_CATEGORIES = [
    "Executive / C-Suite",
    "Technical / Engineering",
    "Sales / Marketing",
    "Creative / Design",
    "Operations / Admin",
    "Publisher / Author",
    "General Subscriber",
]

COLUMN_ALIASES: Dict[str, List[str]] = {
    "email":      ["email", "e-mail", "mail", "email_address", "emailaddress", "contact_email", "mail_addr"],
    "first_name": ["first_name", "firstname", "first", "given_name", "fname", "givenname"],
    "last_name":  ["last_name", "lastname", "last", "surname", "family_name", "lname"],
    "company":    ["company", "organization", "org", "business", "biz", "employer", "company_name"],
    "job_title":  ["job_title", "title", "role", "position", "jobtitle", "job_role"],
    "tags":       ["tags", "tag", "labels", "groups", "segments", "audience", "category"],
    "notes":      ["notes", "note", "comments", "comment", "description", "memo"],
}


# ---------------------------------------------------------------------------
#  Tier-1 / Tier-2 File Parser
# ---------------------------------------------------------------------------
class BulkFileParser:
    """Parses any supported upload format into a pandas DataFrame."""

    def parse(self, filename: str, content: bytes) -> pd.DataFrame:
        name = filename.lower()
        buf = io.BytesIO(content)

        # Tier 2 -- Compressed containers
        if name.endswith(".csv.gz") or name.endswith(".tsv.gz") or (name.endswith(".gz") and "csv" in name):
            with gzip.GzipFile(fileobj=buf) as gz:
                inner = gz.read()
            sep = "\t" if ".tsv" in name else ","
            return pd.read_csv(io.BytesIO(inner), sep=sep, on_bad_lines="skip", low_memory=False)

        if name.endswith(".zip"):
            with zipfile.ZipFile(buf) as zf:
                csv_names = [n for n in zf.namelist() if n.lower().endswith((".csv", ".tsv", ".txt"))]
                if not csv_names:
                    raise ValueError("ZIP archive contains no CSV/TSV/TXT files.")
                with zf.open(csv_names[0]) as inner:
                    sep = "\t" if csv_names[0].lower().endswith(".tsv") else ","
                    return pd.read_csv(inner, sep=sep, on_bad_lines="skip", low_memory=False)

        # Tier 2 -- Columnar binary
        if name.endswith(".parquet"):
            return pd.read_parquet(buf, engine="pyarrow")

        # Tier 1 -- Spreadsheets
        if name.endswith((".xlsx", ".xls")):
            return pd.read_excel(buf)

        # Tier 1 -- Delimited text
        if name.endswith(".tsv") or (name.endswith(".txt") and not name.endswith(".jsonl")):
            return pd.read_csv(buf, sep="\t", on_bad_lines="skip", low_memory=False)

        if name.endswith(".csv"):
            return pd.read_csv(buf, on_bad_lines="skip", low_memory=False)

        # Tier 1 -- JSON / JSONL
        if name.endswith(".jsonl"):
            return pd.read_json(buf, lines=True)

        if name.endswith(".json"):
            try:
                return pd.read_json(buf)
            except ValueError:
                buf.seek(0)
                return pd.read_json(buf, lines=True)

        raise ValueError(
            f"Unsupported format: '{filename}'. "
            "Accepted: .csv .tsv .txt .xlsx .xls .json .jsonl .parquet .csv.gz .zip"
        )


# ---------------------------------------------------------------------------
#  AI Schema Mapper
# ---------------------------------------------------------------------------
class AISchemaMapper:
    """Zero-config column normaliser — maps messy source headers to canonical names."""

    def map_columns(self, raw_columns: List[str]) -> Dict[str, str]:
        result: Dict[str, str] = {}
        already_mapped: set = set()

        for raw in raw_columns:
            clean = raw.lower().replace("_", "").replace("-", "").replace(" ", "")
            for canonical, aliases in COLUMN_ALIASES.items():
                if canonical in already_mapped:
                    continue
                for alias in aliases:
                    if clean == alias.replace("_", "").replace("-", "").replace(" ", ""):
                        result[raw] = canonical
                        already_mapped.add(canonical)
                        break
                else:
                    continue
                break

        # Fuzzy fallback
        for raw in raw_columns:
            if raw in result:
                continue
            clean = raw.lower()
            for canonical, aliases in COLUMN_ALIASES.items():
                if canonical in already_mapped:
                    continue
                if any(alias in clean or clean in alias for alias in aliases):
                    result[raw] = canonical
                    already_mapped.add(canonical)
                    break

        return result


# ---------------------------------------------------------------------------
#  Email Validator
# ---------------------------------------------------------------------------
class EmailValidator:
    def clean(self, df: pd.DataFrame) -> pd.DataFrame:
        df["email"] = df["email"].astype(str).str.strip().str.lower()
        valid_mask = df["email"].apply(lambda x: bool(EMAIL_REGEX.match(x)))
        before = len(df)
        df = df[valid_mask].copy()
        dropped = before - len(df)
        if dropped:
            logger.info(f"EmailValidator: dropped {dropped} invalid rows.")
        df = df.drop_duplicates(subset=["email"])
        return df


# ---------------------------------------------------------------------------
#  AI Audience Tagger
# ---------------------------------------------------------------------------
class AIAudienceTagger:
    """Local sentence-transformer vector tagger. Zero cloud cost."""

    _model = None
    _cat_embeddings: Optional[np.ndarray] = None

    def _ensure_model(self) -> bool:
        if AIAudienceTagger._model is not None:
            return True
        try:
            from sentence_transformers import SentenceTransformer  # type: ignore
            logger.info("Loading embedding model all-MiniLM-L6-v2 ...")
            AIAudienceTagger._model = SentenceTransformer("all-MiniLM-L6-v2")
            AIAudienceTagger._cat_embeddings = AIAudienceTagger._model.encode(AUDIENCE_CATEGORIES)
            logger.info("Embedding model ready.")
            return True
        except Exception as e:
            logger.warning(f"sentence-transformers unavailable: {e}. Defaulting all to General Subscriber.")
            return False

    def tag(self, df: pd.DataFrame) -> pd.DataFrame:
        if not self._ensure_model():
            df["ai_segment"] = "General Subscriber"
            return df

        context_cols = [c for c in ["job_title", "company", "notes"] if c in df.columns]
        if not context_cols:
            df["ai_segment"] = "General Subscriber"
            return df

        context_series = df[context_cols].fillna("").agg(" ".join, axis=1).str.strip()
        context_series = context_series.replace("", "subscriber")

        embeddings = AIAudienceTagger._model.encode(
            context_series.tolist(), batch_size=256, show_progress_bar=False
        )

        emb_norm = embeddings / (np.linalg.norm(embeddings, axis=1, keepdims=True) + 1e-8)
        cat_norm = AIAudienceTagger._cat_embeddings / (
            np.linalg.norm(AIAudienceTagger._cat_embeddings, axis=1, keepdims=True) + 1e-8
        )

        sim_matrix = emb_norm @ cat_norm.T
        best_idx = np.argmax(sim_matrix, axis=1)
        df["ai_segment"] = [AUDIENCE_CATEGORIES[i] for i in best_idx]
        return df


# ---------------------------------------------------------------------------
#  Campaign Copy Generator (Ollama local LLM)
# ---------------------------------------------------------------------------
def generate_campaign_copy_for_segment(
    segment_name: str,
    campaign_topic: str,
    ollama_url: str = "http://localhost:11434",
    model: str = "llama3",
) -> Dict[str, str]:
    """Generates personalised subject + opening via Ollama. Falls back to deterministic templates."""

    system_prompt = (
        f"You are a B2B email copywriter. Write a subject line and brief opening paragraph "
        f"for a campaign targeting: '{segment_name}'. Topic: {campaign_topic}. "
        f"Tone: professional, concise. Respond in JSON only: "
        '{"subject": "...", "opening": "..."}'
    )

    try:
        resp = requests.post(
            f"{ollama_url}/api/generate",
            json={"model": model, "prompt": system_prompt, "stream": False},
            timeout=20,
        )
        if resp.ok:
            raw_text = resp.json().get("response", "")
            match = re.search(r"\{.*\}", raw_text, re.DOTALL)
            if match:
                payload = json.loads(match.group())
                return {
                    "segment": segment_name,
                    "subject": payload.get("subject", f"Update for {segment_name}"),
                    "opening": payload.get("opening", ""),
                    "source": "ollama",
                }
    except Exception:
        pass

    fallbacks = {
        "Executive / C-Suite":     ("Strategic Update: " + campaign_topic,   "High-level overview of what this means for your organization."),
        "Technical / Engineering": ("Deep-Dive: " + campaign_topic,          "Detailed architectural specs and implementation notes are inside."),
        "Sales / Marketing":       ("Growth Opportunity: " + campaign_topic,  "See how this directly impacts pipeline and conversion metrics."),
        "Creative / Design":       ("New Creative: " + campaign_topic,        "Take a look at the latest assets and visual resources."),
        "Operations / Admin":      ("Operations Notice: " + campaign_topic,   "Important workflow and scheduling details enclosed."),
        "Publisher / Author":      ("Publishing Update: " + campaign_topic,   "Your next chapter starts here — details below."),
        "General Subscriber":      (campaign_topic,                           "We have something important to share with you."),
    }

    subj, opening = fallbacks.get(segment_name, (campaign_topic, "Please find this important update below."))
    return {"segment": segment_name, "subject": subj, "opening": opening, "source": "fallback"}


# ---------------------------------------------------------------------------
#  Master Pipeline Orchestrator
# ---------------------------------------------------------------------------
class StehouwerCampaignIngestionEngine:
    """
    Top-level orchestrator wired into FastAPI.

    Usage in endpoint:
        engine = StehouwerCampaignIngestionEngine()
        result = engine.ingest(filename=file.filename, content=await file.read())
    """

    def __init__(self):
        self.parser    = BulkFileParser()
        self.mapper    = AISchemaMapper()
        self.validator = EmailValidator()
        self.tagger    = AIAudienceTagger()

    def ingest(
        self,
        filename: str,
        content: bytes,
        default_tags: Optional[List[str]] = None,
    ) -> Dict:
        if default_tags is None:
            default_tags = ["Imported"]

        df = self.parser.parse(filename, content)
        col_map = self.mapper.map_columns(df.columns.tolist())
        df = df.rename(columns=col_map)

        if "email" not in df.columns:
            raise ValueError(
                "Could not locate an email column. Detected headers: "
                + ", ".join(df.columns.tolist())
            )

        df = self.validator.clean(df)
        df = self.tagger.tag(df)

        now = time.strftime("%Y-%m-%d")
        records = []
        segment_counts: Dict[str, int] = {}

        for _, row in df.iterrows():
            tags = row.get("tags", "")
            if isinstance(tags, list):
                tag_list = list(tags)
            elif isinstance(tags, str) and tags and tags.lower() != "nan":
                tag_list = [t.strip() for t in tags.split(",")]
            else:
                tag_list = list(default_tags)

            ai_seg = str(row.get("ai_segment", "General Subscriber"))
            if ai_seg not in tag_list:
                tag_list.append(ai_seg)

            segment_counts[ai_seg] = segment_counts.get(ai_seg, 0) + 1

            def _s(col: str) -> str:
                v = str(row.get(col, "") or "").strip()
                return "" if v.lower() == "nan" else v

            records.append({
                "id":         f"sub-{uuid.uuid4().hex[:8]}",
                "email":      row["email"],
                "first_name": _s("first_name"),
                "last_name":  _s("last_name"),
                "company":    _s("company"),
                "tags":       json.dumps(tag_list),
                "status":     "active",
                "created_at": now,
            })

        return {
            "imported": len(records),
            "segments": segment_counts,
            "records":  records,
        }


# ---------------------------------------------------------------------------
#  ChromaDB Memory Writer
#  Stores every imported contact as a searchable vector document in
#  stehouwer_vector_memory so stehouwer_llm can retrieve audience context.
# ---------------------------------------------------------------------------
HOT_DB_PATH = r"C:\AI-BS\stehouwer_vector_memory"
CAMPAIGN_COLLECTION = "campaign_contacts"


def embed_to_chroma(records: List[Dict], client_id: str = "stehouwer_publishing") -> int:
    """
    Embeds all imported contact records into ChromaDB using nomic-embed-text
    via the local Ollama API.  Returns the number of documents written.

    Each document looks like:
        "Contact: jane@pub.com | Company: Penguin | Segment: Publisher / Author | Tags: VIP"

    This text is what stehouwer_llm will retrieve as context before generating
    any campaign copy.
    """
    try:
        import chromadb
    except ImportError:
        logger.warning("chromadb not installed — skipping vector memory write.")
        return 0

    if not records:
        return 0

    try:
        chroma_client = chromadb.PersistentClient(path=HOT_DB_PATH)
        collection = chroma_client.get_or_create_collection(
            name=CAMPAIGN_COLLECTION,
            metadata={"hnsw:space": "cosine"},
        )
    except Exception as e:
        logger.warning(f"ChromaDB init failed — skipping embed: {e}")
        return 0

    documents = []
    metadatas = []
    ids = []
    embeddings = []

    OLLAMA_EMBED_URL = "http://127.0.0.1:11434/api/embeddings"
    EMBED_MODEL = "nomic-embed-text"

    for r in records:
        # Build a rich natural-language summary of each contact
        tags_list = json.loads(r["tags"]) if isinstance(r["tags"], str) else r["tags"]
        ai_seg = next((t for t in tags_list if t in AUDIENCE_CATEGORIES), "General Subscriber")

        doc_text = (
            f"Contact: {r['email']}"
            + (f" | Name: {r['first_name']} {r['last_name']}".strip(" |") if r.get("first_name") or r.get("last_name") else "")
            + (f" | Company: {r['company']}" if r.get("company") else "")
            + f" | Segment: {ai_seg}"
            + f" | Tags: {', '.join(tags_list)}"
        )

        # Get vector embedding from local Ollama nomic-embed-text
        try:
            resp = requests.post(
                OLLAMA_EMBED_URL,
                json={"model": EMBED_MODEL, "prompt": doc_text},
                timeout=10,
            )
            if resp.ok:
                vec = resp.json().get("embedding")
                if vec:
                    embeddings.append(vec)
                    documents.append(doc_text)
                    metadatas.append({
                        "email":      r["email"],
                        "company":    r.get("company", ""),
                        "ai_segment": ai_seg,
                        "client_id":  client_id,
                        "created_at": r["created_at"],
                    })
                    ids.append(r["id"])
        except Exception as e:
            logger.debug(f"Embed failed for {r['email']}: {e}")
            continue

    if not documents:
        logger.info("No embeddings generated — Ollama may be offline.")
        return 0

    try:
        # Upsert in batches of 100 to avoid large single calls
        BATCH = 100
        total_written = 0
        for i in range(0, len(documents), BATCH):
            collection.upsert(
                ids=ids[i:i+BATCH],
                documents=documents[i:i+BATCH],
                metadatas=metadatas[i:i+BATCH],
                embeddings=embeddings[i:i+BATCH],
            )
            total_written += len(documents[i:i+BATCH])
        logger.info(f"ChromaDB: embedded {total_written} contacts into '{CAMPAIGN_COLLECTION}'.")
        return total_written
    except Exception as e:
        logger.warning(f"ChromaDB upsert failed: {e}")
        return 0


# ---------------------------------------------------------------------------
#  Context Retriever for stehouwer_llm
#  Called by the /api/v1/campaigns/generate endpoint to pull audience context
# ---------------------------------------------------------------------------
def retrieve_audience_context(
    segment: str,
    n_results: int = 20,
    client_id: str = "stehouwer_publishing",
) -> List[str]:
    """
    Queries ChromaDB campaign_contacts collection for the most relevant
    contacts matching the requested segment.  Returns a list of document
    strings to inject as context into the stehouwer_llm prompt.
    """
    try:
        import chromadb
        chroma_client = chromadb.PersistentClient(path=HOT_DB_PATH)
        collection = chroma_client.get_collection(name=CAMPAIGN_COLLECTION)

        results = collection.query(
            query_texts=[f"audience segment: {segment}"],
            n_results=min(n_results, collection.count()),
            where={"client_id": client_id},
        )
        return results.get("documents", [[]])[0]
    except Exception as e:
        logger.warning(f"Chroma context retrieval failed: {e}")
        return []

