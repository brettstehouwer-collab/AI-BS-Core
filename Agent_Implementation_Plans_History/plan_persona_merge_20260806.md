# Persona & Reasoning Dataset Integration Plan

This plan outlines how we will take your raw 1.7 MB WhatsApp transcript (over 16,000 lines of deep conversation) and transform it into a structured dataset that the AI can actually comprehend and use to emulate your psychological reasoning, conversational style, and dark humor.

## User Review Required
> [!WARNING]
> Raw WhatsApp logs are extremely noisy for LLMs. If we feed raw timestamps and `<Media omitted>` tags into the model, it will learn to output garbage. We must first run a strict Python parsing script to clean the data before the LLM can absorb the logic within it.

## Open Questions
> [!IMPORTANT]
> 1. Do you want me to automatically inject this cleaned text directly into your active RAG SQLite database, or should I just output the clean Markdown/JSONL files so you can review them first before the LLM starts reading them?
> 2. Should I immediately update the `stehouwer_llm` Modelfile system prompt to explicitly adopt "dark humor and deep psychological reasoning" as core operational directives?

## Proposed Changes

### 1. Data Sanitization & Parsing Engine
I will create a dedicated Python parser (`scratch/whatsapp_parser.py`) that will:
- Read all 16,800 lines of `WhatsApp Chat with Sean My Brother Who Never Leaves.txt`.
- Strip away all the useless `[Date/Time]` headers and `<Media omitted>` artifacts.
- Merge sequential, rapid-fire text messages from the same person into cohesive paragraphs (so the LLM understands the full thought, rather than fragmented sentences).

### 2. Output Dataset Compilation
The script will compile the cleaned conversation into two distinct, highly valuable formats:
- **`C:\AI-BS\database\WhatsApp_Reasoning_Corpus.md`**: A clean, readable Markdown version of the transcript, chunked into logical topics, perfect for RAG (Retrieval-Augmented Generation) memory ingestion.
- **`C:\AI-BS\database\Stehouwer_Persona_Dataset.jsonl`**: A structured JSONL file formatted specifically for LoRA fine-tuning. If you ever want to permanently bake this personality into a foundational model, this file is the exact format required to train it.

## Verification Plan
1. I will execute the Python script on the 1.7MB file.
2. We will review the first 50 lines of the output JSONL/Markdown to ensure the timestamps are gone and the logical reasoning of the conversation flows perfectly.
