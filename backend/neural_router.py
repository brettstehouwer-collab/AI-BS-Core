import subprocess
import time
import socket
import os
import logging
import asyncio
import httpx
from typing import List, Optional

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s"
)


class NeuralRouter:
    def __init__(
        self,
        host: str = "localhost",
        port: int = 11435,
        model_name: str = "nomic-embed-text",
        generation_model: str = "stehouwer_llm",
    ):
        self.host = host
        self.port = port
        self.model_name = model_name
        self.generation_model = generation_model
        self.base_url = f"http://{self.host}:{self.port}"

    def is_port_open(self) -> bool:
        """Surgically checks if the network port is listening before sending heavy payloads."""
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(1.0)
            try:
                s.connect((self.host, self.port))
                return True
            except (socket.timeout, ConnectionRefusedError):
                return False

    async def check_service_health(self) -> bool:
        """Verifies if the server is not only listening but actually responding to HTTP queries."""
        if not self.is_port_open():
            return False
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(f"{self.base_url}/", timeout=1.5)
                return response.status_code == 200
        except httpx.RequestError:
            return False

    def kill_zombie_processes(self) -> None:
        """Forcibly clears out any hung processes occupying port 11435 without shell parsing."""
        logging.warning(f"🧹 Clearing out dead processes on port {self.port}...")
        try:
            if os.name == "nt":  # Windows environment
                netstat_output = subprocess.check_output(["netstat", "-ano"], text=True)
                for line in netstat_output.strip().split("\n"):
                    if f":{self.port}" in line and "LISTENING" in line:
                        parts = line.split()
                        pid = parts[-1]
                        logging.warning(f"💀 Terminating zombie PID {pid} on Windows.")
                        subprocess.run(["taskkill", "/F", "/PID", str(pid)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            else:  # Linux/MacOS environment
                subprocess.run(["fuser", "-k", f"{self.port}/tcp"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except subprocess.CalledProcessError:
            logging.info("No active processes detected on this port. Safe to proceed.")

    async def auto_restart_server(self) -> bool:
        """
        Launches the embedding server in an isolated background process.
        """
        logging.critical(
            "🚨 [Neural Router] Embedding Server Down! Triggering Autonomous Reboot..."
        )

        # 1. Clear the port first to prevent 'Address already in use' errors
        await asyncio.to_thread(self.kill_zombie_processes)
        await asyncio.sleep(1.0)

        # 2. Spawn the embedding server process
        try:
            env = os.environ.copy()
            env["OLLAMA_HOST"] = f"127.0.0.1:{self.port}"

            if os.name == "nt":
                subprocess.Popen(
                    ["ollama", "serve"],
                    env=env,
                    creationflags=subprocess.CREATE_NEW_PROCESS_GROUP
                    | subprocess.DETACHED_PROCESS,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
            else:
                subprocess.Popen(
                    ["ollama", "serve"],
                    env=env,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    preexec_fn=os.setpgrp,
                )

            # 3. Poll the port until it wakes up (Max 15 seconds)
            for attempt in range(15):
                logging.info(
                    f"⏳ Waiting for embedder to wake up... (Attempt {attempt + 1}/15)"
                )
                if await self.check_service_health():
                    logging.info(
                        f"🎉 [Neural Router] Embedder successfully restored on port {self.port}!"
                    )

                    # 4. Warm up the models
                    logging.info(
                        f"🔥 Warming up models: {self.generation_model} and {self.model_name}..."
                    )
                    async with httpx.AsyncClient() as client:
                        # Warmup generator
                        try:
                            await client.post(
                                f"{self.base_url}/api/generate",
                                json={
                                    "model": self.generation_model,
                                    "prompt": "",
                                    "stream": False,
                                },
                                timeout=30.0,
                            )
                        except httpx.RequestError:
                            pass

                        # Warmup embedder
                        try:
                            await client.post(
                                f"{self.base_url}/api/embeddings",
                                json={"model": self.model_name, "prompt": ""},
                                timeout=30.0,
                            )
                        except httpx.RequestError:
                            pass

                    return True
                await asyncio.sleep(1.0)

            logging.error("❌ Embedder started but failed health checks.")
            return False

        except Exception as e:
            logging.error(f"❌ Critical failure while launching embedding server: {e}")
            return False

    async def route_to_embedder(self, text: str) -> Optional[List[float]]:
        """
        Routes the text to the local embedding API.
        Auto-reboots the system if a connection failure occurs.
        """
        if not await self.check_service_health():
            if not await self.auto_restart_server():
                logging.error("❌ Cannot generate embedding: Server reboot failed.")
                return None

        payload = {"model": self.model_name, "prompt": text}
        endpoint = f"{self.base_url}/api/embeddings"

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(endpoint, json=payload, timeout=60.0)
                if response.status_code == 200:
                    return response.json().get("embedding")
                else:
                    logging.error(f"Embedding API error: {response.text}")
                    return None
        except httpx.RequestError as e:
            logging.warning(
                f"⚠️ Network error during vectorization: {e}. Retrying recovery..."
            )
            if await self.auto_restart_server():
                try:
                    async with httpx.AsyncClient() as client:
                        response = await client.post(
                            endpoint, json=payload, timeout=60.0
                        )
                        return response.json().get("embedding")
                except httpx.RequestError:
                    pass
            return None

    async def route_to_generator(
        self, prompt: str, agent_role: str = "Assistant"
    ) -> str:
        """
        Routes prompt to the generation API.
        """
        if not await self.check_service_health():
            if not await self.auto_restart_server():
                return "Error: Cannot generate text: Server reboot failed."

        system_prompt = f"You are an expert sub-agent. Your role is: {agent_role}."
        endpoint = f"{self.base_url}/api/generate"
        payload = {
            "model": self.generation_model,
            "prompt": f"{system_prompt}\n\nTask: {prompt}",
            "stream": False,
        }

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(endpoint, json=payload, timeout=120.0)
                if response.status_code == 200:
                    return response.json().get("response", "").strip()
                return f"Error: Generator returned status {response.status_code}"
        except httpx.RequestError as e:
            logging.warning(
                f"⚠️ Network error during generation: {e}. Retrying recovery..."
            )
            if await self.auto_restart_server():
                try:
                    async with httpx.AsyncClient() as client:
                        response = await client.post(
                            endpoint, json=payload, timeout=120.0
                        )
                        if response.status_code == 200:
                            return response.json().get("response", "").strip()
                except httpx.RequestError:
                    pass
            return f"Connection error to Generator: {e}"

    async def preheat_model(self, model_name: str = "stehouwer_llm") -> None:
        """
        Sends an ultra-lightweight call to pre-load the model's weights into VRAM
        if it was unloaded, eliminating cold-start latencies on actual requests.
        """
        try:
            # We check if the model is already running
            async with httpx.AsyncClient(timeout=2.0) as client:
                running_status = await client.get(
                    "http://127.0.0.1:11434/api/ps"
                )
                if running_status.status_code == 200:
                    models = running_status.json().get("models", [])
                    if any(m.get("name") == model_name for m in models):
                        return  # Model is hot, no preheat needed

            # If the model is cold, warm it up with a 1-token keep-alive call
            logging.info(f"🔥 Preheating '{model_name}' into GPU memory...")
            preheat_payload = {
                "model": model_name,
                "prompt": "ping",
                "options": {"num_predict": 1},
                "keep_alive": -1,  # Tell Ollama to keep it loaded indefinitely
            }
            # Fire and forget or allow a generous, isolated background load time
            async with httpx.AsyncClient() as client:
                await client.post(
                    "http://127.0.0.1:11434/api/generate",
                    json=preheat_payload,
                    timeout=30.0,
                )
            logging.info(f"✅ '{model_name}' is fully warmed up in VRAM!")
        except Exception as e:
            logging.warning(f"⚠️ Preheat failed (Ollama may be busy or booting): {e}")

    async def route_to_chat(
        self, messages: list, model_name: str = "stehouwer_llm"
    ) -> str:
        """
        Asynchronously routes the ReAct conversation to our fast, hardware-optimized stehouwer_llm.
        """
        chat_endpoint = f"http://127.0.0.1:11434/api/chat"
        payload = {"model": model_name, "messages": messages, "stream": False}

        try:
            # First, check and preheat the model if it was cold
            await self.preheat_model(model_name)

            # Generous 120s timeout to survive cold starts and background VRAM purges
            async with httpx.AsyncClient() as client:
                response = await client.post(chat_endpoint, json=payload, timeout=120.0)
                if response.status_code == 200:
                    data = response.json()
                    return data.get("message", {}).get("content", "")
                else:
                    logging.error(f"❌ Chat API error: {response.text}")
                    return "[Model Execution Error]"
        except httpx.TimeoutException:
            logging.critical(
                "🚨 Deep Timeout Detected! Falling back to lightweight executor..."
            )
            # FALLBACK: If the heavy model fails to respond in 120s, automatically
            # fall back to a smaller fallback model or return a clean, cached system report.
            return "[SYSTEM ALERT]: Local model load timeout. Environment busy. Please retry in 5 seconds."
        except httpx.RequestError as e:
            logging.warning(f"⚠️ Network error during chat generation: {e}")
            return "[Network Timeout or Connection Error]"


# Expose a global instance for easy importing by other modules
router_instance = NeuralRouter()
