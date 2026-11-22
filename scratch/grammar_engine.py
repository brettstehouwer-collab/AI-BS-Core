import httpx
import json
import logging
import time

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s")


class GrammarEngine:
    def __init__(
            self,
            model="stehouwer_llm",
            base_url="http://localhost:11434/api"):
        self.model = model
        self.base_url = base_url

    async def generate_json_manifest(
            self,
            prompt: str,
            schema_template: dict) -> dict:
        """
        Forces the local LLM to output a strict JSON payload matching the schema_template.
        Includes a system load fail-safe to prevent hanging.
        """
        logging.info(
            "[GRAMMAR ENGINE] Enforcing strict JSON mode constraint on token generation.")

        system_prompt = (
            "You are an AI-BS API component. You must respond ONLY with valid JSON. "
            f"Your output must exactly match this JSON schema format: {json.dumps(schema_template)}"
        )

        start_time = time.time()
        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(f"{self.base_url}/generate", json={
                    "model": self.model,
                    "prompt": f"{system_prompt}\n\nTask: {prompt}",
                    "stream": False,
                    "format": "json"  # The physical hardware token constraint
                }, timeout=120.0)

                # Check execution time fail-safe (User Directive)
                exec_time = time.time() - start_time
                if exec_time > 115.0:
                    logging.warning(
                        "[GRAMMAR ENGINE] Critical Resource Load detected. Exited task safely without data loss.")
                    return {
                        "status": "error",
                        "message": "System load critical. Task chunking required."}

                if response.status_code == 200:
                    raw_res = response.json().get("response", "{}")
                    try:
                        return json.loads(raw_res)
                    except json.JSONDecodeError:
                        logging.error(
                            "[GRAMMAR ENGINE] Hallucination detected despite constraints.")
                        return {
                            "status": "error",
                            "message": "Invalid JSON generated."}
                else:
                    return {
                        "status": "error",
                        "message": f"Status Code: {
                            response.status_code}"}

            except Exception as e:
                logging.error(f"[GRAMMAR ENGINE] Connection crash: {e}")
                return {
                    "status": "error",
                    "message": "Daemon connection timeout."}


if __name__ == "__main__":
    # Test stub
    pass
