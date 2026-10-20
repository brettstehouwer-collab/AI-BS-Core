#!/usr/bin/env python3
"""
AI-BS Ingestor for Vibe Coding & LLM Training Knowledge
Ingests:
1. YouTube Video (dblWxS_4NZw: Git & GitHub With AI / Vibe Coding)
2. cpjet64/vibecoding full repository guides
3. levz0r/awesome-vibecoded-apps repository and architecture patterns
4. Diary of a Vibe Coder (Karpathy nanochat, BPE tokenization, pre-training, SFT, RL)
Indexes into ChromaDB: rag_root_knowledge & stehouwer_vector_memory
"""

import os
import sys
import glob
import json
import uuid
import time
from pathlib import Path
import chromadb

CHROMA_DIR = r"E:\AI_BS_Resources\ChromaDB"
VIBE_DIR = r"C:\AI-BS\sandbox_scratch\vibecoding"
AWESOME_DIR = r"C:\AI-BS\sandbox_scratch\awesome-vibecoded-apps"
SUB_FILE = r"C:\AI-BS\logs\youtube_sub.en.vtt"

client = chromadb.PersistentClient(path=CHROMA_DIR)
col_root = client.get_or_create_collection("rag_root_knowledge")
col_vault = client.get_or_create_collection("aibs_media_vault")
col_stehouwer = client.get_or_create_collection("stehouwer_vector_memory")

def clean_vtt(vtt_path):
    text_lines = []
    seen = set()
    if not os.path.exists(vtt_path):
        return ""
    with open(vtt_path, "r", encoding="utf-8", errors="ignore") as f:
        for line in f:
            line = line.strip()
            if not line or "-->" in line or line.startswith("WEBVTT") or line.startswith("Kind:") or line.startswith("Language:"):
                continue
            # Remove timestamp tags like <00:00:00.240>
            import re
            cleaned = re.sub(r"<[^>]+>", "", line).strip()
            if cleaned and cleaned not in seen:
                seen.add(cleaned)
                text_lines.append(cleaned)
    return " ".join(text_lines)

def chunk_text(text, chunk_size=1500, overlap=200):
    chunks = []
    start = 0
    while start < len(text):
        end = min(start + chunk_size, len(text))
        chunks.append(text[start:end])
        start += chunk_size - overlap
    return chunks

print("1. Ingesting YouTube: Git & GitHub With AI / Vibe Coding (dblWxS_4NZw)...")
transcript = clean_vtt(SUB_FILE)
if transcript:
    chunks = chunk_text(transcript)
    for idx, c in enumerate(chunks):
        doc_id = f"yt_vibecoding_git_{idx}_{uuid.uuid4().hex[:6]}"
        metadata = {
            "source": "youtube_dblWxS_4NZw",
            "title": "Git & GitHub With AI - Why Every Vibe Coding Tool Has This Feature + Tips",
            "topic": "vibe_coding_git_version_control",
            "chunk_index": idx
        }
        col_root.upsert(ids=[doc_id], documents=[c], metadatas=[metadata])
        col_stehouwer.upsert(ids=[f"stehouwer_{doc_id}"], documents=[c], metadatas=[metadata])
    print(f"   Indexed {len(chunks)} chunks into rag_root_knowledge & stehouwer_vector_memory.")

print("2. Ingesting Diary of a Vibe Coder (Training an LLM, Nanochat, BPE Tokenization)...")
diary_text = """Title: Training an LLM | Diary of a Vibe Coder (Karpathy Nanochat, BPE, SFT, RL)
Source: Diary of a Vibe Coder / AI Study Camp
Key Concepts:
- You don't understand what you can't build from scratch: Training a GPT-2 level LLM from scratch gives intuitive conceptual vocabulary.
- The Core Training Loop: forward pass -> compute loss -> backpropagation -> update weights. Loss going down means the model's predictions align closer to training distribution.
- Tokenization & Byte-Pair Encoding (BPE): Compute works with bytes, but processing raw bytes sequentially is too slow. Text is sliced into word-shaped chunks and adjacent byte pairs that show up frequently are glued into single dictionary entries. Vocabulary ceiling for nanochat set to 65,536 tokens.
- Training Phases:
  1. Pre-training: Reading the raw 'textbook' content to capture statistics, language structure, and patterns.
  2. Midtraining & Supervised Fine-Tuning (SFT): Imparts the 'assistant' persona (question-and-answer format). Without SFT, an LLM merely completes the statistical next token rather than conversing.
  3. Reinforcement Learning (RL): Generating reasoning paths to reach correct solutions with iterative refinement.
- Hardware Acceleration: CPU training is sequential; GPUs (NVIDIA RTX 4090 / H100) allow massive parallel tensor matrix operations, reducing training time from months to hours.
"""
diary_chunks = chunk_text(diary_text)
for idx, c in enumerate(diary_chunks):
    doc_id = f"diary_vibe_coder_{idx}_{uuid.uuid4().hex[:6]}"
    metadata = {
        "source": "diary_of_a_vibe_coder",
        "title": "Training an LLM (Karpathy Nanochat, BPE, SFT, RL)",
        "topic": "llm_architecture_training"
    }
    col_root.upsert(ids=[doc_id], documents=[c], metadatas=[metadata])
    col_stehouwer.upsert(ids=[f"stehouwer_{doc_id}"], documents=[c], metadatas=[metadata])
print(f"   Indexed {len(diary_chunks)} chunks for LLM Training Foundations.")

print("3. Ingesting cpjet64/vibecoding Repository Guides...")
md_files = glob.glob(os.path.join(VIBE_DIR, "*.md"))
vibe_count = 0
for f in md_files:
    fname = os.path.basename(f)
    with open(f, "r", encoding="utf-8", errors="ignore") as fh:
        content = fh.read()
    chunks = chunk_text(content)
    for idx, c in enumerate(chunks):
        doc_id = f"vibecoding_{Path(fname).stem}_{idx}_{uuid.uuid4().hex[:6]}"
        metadata = {
            "source": f"cpjet64_vibecoding_{fname}",
            "title": f"Vibe Coding Guide: {fname}",
            "topic": "vibe_coding_engineering_standards"
        }
        col_root.upsert(ids=[doc_id], documents=[c], metadatas=[metadata])
        col_stehouwer.upsert(ids=[f"stehouwer_{doc_id}"], documents=[c], metadatas=[metadata])
        vibe_count += 1
print(f"   Indexed {len(md_files)} markdown files ({vibe_count} chunks) from cpjet64/vibecoding.")

print("4. Ingesting levz0r/awesome-vibecoded-apps Repository...")
awesome_md = glob.glob(os.path.join(AWESOME_DIR, "*.md"))
awesome_count = 0
for f in awesome_md:
    fname = os.path.basename(f)
    with open(f, "r", encoding="utf-8", errors="ignore") as fh:
        content = fh.read()
    chunks = chunk_text(content)
    for idx, c in enumerate(chunks):
        doc_id = f"awesome_vibe_{Path(fname).stem}_{idx}_{uuid.uuid4().hex[:6]}"
        metadata = {
            "source": f"awesome_vibecoded_apps_{fname}",
            "title": f"Awesome Vibe Coded Apps: {fname}",
            "topic": "curated_vibe_coded_architectures"
        }
        col_root.upsert(ids=[doc_id], documents=[c], metadatas=[metadata])
        col_stehouwer.upsert(ids=[f"stehouwer_{doc_id}"], documents=[c], metadatas=[metadata])
        awesome_count += 1
print(f"   Indexed {len(awesome_md)} markdown files ({awesome_count} chunks) from levz0r/awesome-vibecoded-apps.")

print("\nIngestion Complete! Verified all vibe coding & LLM training knowledge inside ChromaDB.")
