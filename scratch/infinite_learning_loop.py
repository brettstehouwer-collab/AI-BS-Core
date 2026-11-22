import time
import threading
import logging
import psutil
import json
import shutil
import os
from memory_bank import store_heuristic
from telemetry_checkpoint_db import log_telemetry

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s")


class InfiniteLearningLoop:
    def __init__(self):
        self.running = False
        self.thread = None
        self.iteration = 0
        self.last_read_position = 0
        # Use workspace-relative path with env override for flexibility
        self.local_transcript_path = os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            os.getenv("TRANSCRIPT_PATH", "active_agent_transcript.jsonl")
        )
        self.system_transcript_path = os.getenv(
            "SYSTEM_TRANSCRIPT_PATH"
        )

        # Only sync if system path differs from local path
        if self.system_transcript_path and self.system_transcript_path != self.local_transcript_path:
            try:
                shutil.copy2(
                    self.system_transcript_path,
                    self.local_transcript_path)
            except Exception as e:
                logging.warning(f"Failed to sync transcript: {e}")

    def ingest_agent_transcript(self):
        """Reads the agent's live chat transcript and stores new actions in ChromaDB."""
        if not self.system_transcript_path or not os.path.exists(
                self.system_transcript_path):
            return []

        trigger_tasks = []

        try:
            # Sync to local workspace for user visibility
            shutil.copy2(
                self.system_transcript_path,
                self.local_transcript_path)

            with open(self.system_transcript_path, "r", encoding="utf-8") as f:
                f.seek(self.last_read_position)

                for line in f:
                    if not line.strip():
                        continue
                    try:
                        entry = json.loads(line)
                        step_type = entry.get("type", "")
                        content = entry.get("content", "")

                        if step_type in [
                                "USER_INPUT", "PLANNER_RESPONSE"] and content:
                            store_heuristic(
                                content,
                                metadata={
                                    "source": "agent_transcript",
                                    "type": step_type})
                            # Check for keywords to trigger swarm
                            lower_content = content.lower()
                            if "error" in lower_content or "bug" in lower_content or "analyze" in lower_content:
                                trigger_tasks.append(content)
                    except json.JSONDecodeError:
                        pass

                self.last_read_position = f.tell()
        except Exception as e:
            logging.error(f"Failed to ingest transcript: {e}")
        return trigger_tasks

    def get_telemetry(self):
        """Extracts current VRAM/RAM/CPU usage."""
        # Mock VRAM for now unless pynvml is available
        vram_mb = 0.0
        system_ram_mb = psutil.virtual_memory().used / (1024 * 1024)

        # Get CPU thread mask utilization
        cpu_percentages = psutil.cpu_percent(interval=None, percpu=True)
        cpu_dict = {f"core_{i}": p for i, p in enumerate(cpu_percentages)}

        return vram_mb, system_ram_mb, cpu_dict

    def learning_tick(self):
        """The core deduction tick generating heuristic solutions."""
        self.iteration += 1

        # 1. Telemetry Capture
        vram_mb, system_ram_mb, cpu_dict = self.get_telemetry()

        # Check constraints (Keep Alive logic)
        keep_alive = 1
        if system_ram_mb > 50000:  # 50GB threshold
            keep_alive = 0
            logging.warning("Memory threshold exceeded. Forced keep_alive=0")

        log_telemetry(
            vram_mb,
            system_ram_mb,
            cpu_dict,
            "infinite_learning_loop",
            keep_alive)

        if keep_alive == 0:
            self.stop()
            return

        # 2. Ingest Live Agent Transcript
        trigger_tasks = self.ingest_agent_transcript()

        # 3. Logic Simulation (The actual NLP / execution logic would go here)
        if trigger_tasks:
            try:
                import asyncio
                from bullshit_orchestrator import run_orchestration

                # Use the latest trigger task as the primary goal
                master_goal = f"Analyze and resolve the following context: {trigger_tasks[-1][:100]}..."
                logging.info(
                    f"Triggering Swarm Orchestrator for goal: {master_goal}")

                # Run the async orchestrator in the synchronous thread
                loop_result = asyncio.run(run_orchestration(master_goal))

                generated_solution = f"Swarm execution complete: Status {
                    loop_result.get('status')}, Stages: {
                    loop_result.get(
                        'total_stages_executed', 0)}"
            except Exception as e:
                generated_solution = f"Orchestrator invocation failed: {e}"
                logging.error(generated_solution)

            # 4. Memory Bank Sync
            store_heuristic(
                generated_solution,
                metadata={
                    "iteration": self.iteration,
                    "source": "infinite_loop"})

            # 4.5 Trigger Predictive Model Active Learning
            try:
                import requests
                requests.post("http://127.0.0.1:8002/api/train", timeout=5)
                logging.info("Triggered Predictive Model retraining (Active Learning)")
            except Exception as e:
                logging.warning(f"Predictive Model retraining failed: {e}")
        else:
            logging.debug(
                f"[LEARNING LOOP] Tick {
                    self.iteration}: No actionable triggers found.")

        logging.info(
            f"[LEARNING LOOP] Tick {
                self.iteration} complete. Throttling...")
        # 5. Throttling to prevent CPU locking
        time.sleep(2)

    def _run(self):
        logging.info("Infinite Learning Loop Activated ✅")
        while self.running:
            self.learning_tick()

    def start(self):
        if not self.running:
            self.running = True
            self.thread = threading.Thread(target=self._run, daemon=True)
            self.thread.start()

    def stop(self):
        self.running = False
        if self.thread and threading.current_thread() != self.thread:
            self.thread.join(timeout=2.0)
        logging.info("Learning loop terminated.")


if __name__ == "__main__":
    loop = InfiniteLearningLoop()
    loop.start()

    try:
        logging.info("Daemon running infinitely. Press Ctrl+C to stop.")
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        loop.stop()
