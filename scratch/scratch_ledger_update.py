import datetime

ledger_path = r"C:\AI-BS\AI_BS_MASTER_ARCHITECTURAL_LEDGER.md"
manual_path = r"C:\AI-BS\docs\AI_BS_MASTER_ECOSYSTEM_MANUAL.md"
timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

with open(ledger_path, "a", encoding="utf-8") as f:
    f.write(f"\n### {timestamp} - AI Adapter Pipeline Resiliency Patch\n")
    f.write("**AI Rationale:** The PDF-to-Fountain ingestion pipeline in `ai_adapter.py` was brittle against database outages (ChromaDB) and local LLM timeouts/404s. It also crashed on unexpected Markdown outputs. Applied patches to handle these gracefully and ensure unattended overnight book adaptations succeed.\n")
    f.write("**Implementation:**\n")
    f.write("- Modified `backend/core/ai_adapter.py` to wrap ChromaDB `HttpClient` in try/except. Falls back to purely rolling summaries if vector memory is offline.\n")
    f.write("- Integrated LLM model cascade/fallback array (`stehouwer_llm`, `llama3`, `mistral`, `gemma`) for high-availability.\n")
    f.write("- Implemented strict Regex block stripping for `.fdx` Markdown output.\n")

with open(manual_path, "a", encoding="utf-8") as f:
    f.write(f"\n### Update: AI Adapter Fault Tolerance ({timestamp})\n")
    f.write("The AI Adapter pipeline now supports zero-downtime fallback for both Vector Memory (ChromaDB) and Inference (Ollama).\n")
    f.write("If a specific LLM model is missing or fails, it will seamlessly fall through to subsequent available models in the cascade array.\n")
