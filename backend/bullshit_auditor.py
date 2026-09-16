import asyncio
import json
import concurrent.futures
import httpx


async def audit_code(code_content: str, model: str = "stehouwer_llm") -> bool:
    """Enforces REOP Phase I: Sovereignty Check & Efficiency Delta Analysis.

    Returns True if approved, False if rejected. Uses httpx.AsyncClient
    to avoid blocking the event loop.
    """
    # --- Pre-flight checks (synchronous, no I/O) ---
    restricted_keywords = [
        "import openai",
        "import boto3",
        "import google.cloud",
        "api.openai.com",
        "amazonaws.com",
    ]
    for keyword in restricted_keywords:
        if keyword in code_content:
            print(f"[Bullshit Auditor] SOVEREIGNTY VIOLATION: '{keyword}'. Rejecting.")
            return False

    if "http://" in code_content or "https://" in code_content:
        if "localhost" not in code_content and "127.0.0.1" not in code_content:
            print(
                "[Bullshit Auditor] SOVEREIGNTY VIOLATION: External URL detected. Rejecting."
            )
            return False

    prompt = (
        "You are the Stehouwer Reality Standard Audit Agent. "
        "Review this code. 1) Check for placeholders, lacking logic, or syntax errors. "
        "2) Perform Efficiency Delta Analysis: estimate Big O complexity, token consumption, and VRAM overhead. "
        "Output strictly as JSON with keys 'verdict' (APPROVE/REJECT) and 'analysis'.\n\n"
        f"Code:\n{code_content}"
    )

    # --- Async HTTP call (non-blocking) ---
    try:
        async with httpx.AsyncClient() as client:
            r = await client.post(
                "http://127.0.0.1:11434/api/generate",
                json={
                    "model": model,
                    "prompt": prompt,
                    "stream": False,
                    "format": "json",
                },
                timeout=30.0,
            )

        if r.status_code != 200:
            print(f"[Bullshit Auditor] LLM returned {r.status_code}")
            return False

        # --- Parse response with fallback ---
        try:
            parsed = json.loads(r.json().get("response", ""))
            verdict = parsed.get("verdict", "").upper()
            analysis = parsed.get("analysis", "")
            print(f"[Bullshit Auditor] Efficiency Analysis:\n{analysis}")
            return "APPROVE" in verdict
        except (json.JSONDecodeError, KeyError):
            # Fallback: check raw response text
            response_upper = r.json().get("response", "").upper()
            if "REJECT" in response_upper and "APPROVE" not in response_upper:
                print("[Bullshit Auditor] Code REJECTED (fallback parse).")
                return False
            print("[Bullshit Auditor] Code APPROVED (fallback parse).")
            return True

    except httpx.TimeoutException:
        print("[Bullshit Auditor] LLM call timed out (30s). Rejecting.")
        return False
    except httpx.ConnectError as e:
        print(f"[Bullshit Auditor] Cannot connect to Ollama: {e}. Rejecting.")
        return False
    except Exception as e:
        print(f"[Bullshit Auditor] Unexpected error during audit: {e}. Rejecting.")
        return False


# --- Backward-compat sync wrapper ---
def _audit_code_sync(code_content: str, model: str = "stehouwer_llm") -> bool:
    """Sync wrapper for callers that cannot use async."""
    with concurrent.futures.ThreadPoolExecutor() as pool:
        future = pool.submit(
            lambda: asyncio.run(_audit_code_async(code_content, model))
        )
        return future.result()


# Public API — sync by default (safe for any caller)
_audit_code_async = audit_code  # Capture original async function before rebinding
audit_code = _audit_code_sync
