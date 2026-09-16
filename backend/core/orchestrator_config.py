"""Configuration loader for Bullshit Orchestrator."""

import os
from pathlib import Path

# Load .env file if it exists
ENV_FILE = Path(__file__).parent / ".env"
if ENV_FILE.exists():
    from dotenv import load_dotenv

    load_dotenv(ENV_FILE)


class OrchestratorConfig:
    """Central configuration for the orchestrator system."""

    # Neural Router
    GENERATION_MODEL: str = os.getenv("GENERATION_MODEL", "stehouwer_llm")
    EMBEDDING_MODEL: str = os.getenv("EMBEDDING_MODEL", "nomic-embed-text")
    OLLAMA_BASE_URL: str = os.getenv(
        "OLLAMA_BASE_URL", "http://127.0.0.1:11434/api"
    )

    # Backend Endpoints
    BACKEND_URL: str = os.getenv("BACKEND_URL", "http://localhost:8000")
    GENERATE_PROXY_ENDPOINT: str = os.getenv(
        "GENERATE_PROXY_ENDPOINT", "/api/v2/generate_proxy"
    )
    HEURISTICS_ENDPOINT: str = os.getenv(
        "HEURISTICS_ENDPOINT", "/api/heuristics/analyze_failure"
    )

    # Core Engine
    MAX_THREADS: int = int(os.getenv("MAX_THREADS", "32"))
    MAX_STAGES: int = int(os.getenv("MAX_STAGES", "25"))

    # Token Budget
    TOKEN_TARGET_LIMIT: int = int(os.getenv("TOKEN_TARGET_LIMIT", "3700"))
    TOKEN_MAX_LIMIT: int = int(os.getenv("TOKEN_MAX_LIMIT", "4000"))

    # Concurrency
    STAGE_SEMAPHORE_LIMIT: int = int(os.getenv("STAGE_SEMAPHORE_LIMIT", "5"))
    STAGE_TIMEOUT_SEC: float = float(os.getenv("STAGE_TIMEOUT_SEC", "120.0"))
    EMBEDDER_TIMEOUT_SEC: float = float(os.getenv("EMBEDDER_TIMEOUT_SEC", "60.0"))

    # Logging
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")

    @classmethod
    def get_generate_proxy_url(cls) -> str:
        """Get full URL for generate proxy endpoint."""
        return f"{cls.BACKEND_URL}{cls.GENERATE_PROXY_ENDPOINT}"

    @classmethod
    def get_heuristics_url(cls) -> str:
        """Get full URL for heuristics endpoint."""
        return f"{cls.BACKEND_URL}{cls.HEURISTICS_ENDPOINT}"

    @classmethod
    def get_embedder_url(cls) -> str:
        """Get full URL for embeddings endpoint."""
        return f"{cls.OLLAMA_BASE_URL}/embeddings"
