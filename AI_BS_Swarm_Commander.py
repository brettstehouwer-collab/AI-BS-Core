"""
AI-BS Swarm Commander Module.

Manages autonomous agents monitoring 70 sector databases.
Generates world mutations using Ollama and Gemini APIs.
"""

import asyncio
import datetime
import os
import random
import sqlite3
import sys
import time

import chromadb
import requests


sys.path.append("C:\\AI-BS")
try:
    from discord_notifier import send_discord_update
except ImportError:
    def send_discord_update(msg):
        """Fallback for discord notifications."""
        print(msg)


RESOURCE_DIR = "E:\\AI_BS_Resources"
DB_DIR = os.path.join(RESOURCE_DIR, "Databases")
CHROMA_DIR = os.path.join(RESOURCE_DIR, "ChromaDB")
ACTIONS_DB_PATH = os.path.join(RESOURCE_DIR, "actions.db")

industry_keys = [
    "real_estate", "legal", "medical", "retail", "finance", "education",
    "manufacturing", "agriculture", "entertainment", "cybersecurity", "hr",
    "customer_support", "logistics", "insurance", "construction", "automotive",
    "travel", "gaming", "ngo", "journalism", "wellness", "events", "gov",
    "energy", "telecom", "mining", "aerospace", "pharma", "fashion", "foodbev",
    "audio", "video", "photography", "animation", "translation", "writing",
    "seo", "socialmedia", "pr", "sports", "landscaping", "realestatedev",
    "hvac", "plumbing", "electrical", "cleaning", "security", "pestcontrol",
    "wastemgmt", "delivery", "datacenter", "devops", "cloudfinops", "quantum",
    "robotics", "cv", "blockchain", "syntheticbio", "materials", "nlpresearch",
    "edgeiot", "observability", "embedded", "gamearch", "pentesting",
    "autovehicles", "ardev", "semiconductors", "nanotech", "deepspace"
]


def init_actions_db():
    """Initialize the SQLite ledger for autonomous actions."""
    conn = sqlite3.connect(ACTIONS_DB_PATH)
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS autonomous_actions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT,
            industry TEXT,
            trigger_metric TEXT,
            trigger_value REAL,
            rag_context TEXT,
            llm_decision TEXT,
            status TEXT
        )
    ''')
    try:
        c.execute(
            "ALTER TABLE autonomous_actions ADD COLUMN world_mutation TEXT"
        )
    except sqlite3.OperationalError:
        pass  # Column already exists
    conn.commit()
    conn.close()
    print(f"Initialized autonomous actions ledger at {ACTIONS_DB_PATH}")


def log_action(industry, metric, value, context, decision,
               world_mutation="None"):
    """Persist the autonomous action and mutation to the SQLite database."""
    conn = sqlite3.connect(ACTIONS_DB_PATH)
    c = conn.cursor()
    # Use timezone-aware UTC datetime
    timestamp = datetime.datetime.now(datetime.timezone.utc).isoformat()
    try:
        c.execute('''
            INSERT INTO autonomous_actions (
                timestamp, industry, trigger_metric, trigger_value, 
                rag_context, llm_decision, world_mutation, status
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (timestamp, industry, metric, value, context, decision,
              world_mutation, 'EXECUTED'))
    except sqlite3.OperationalError:
        c.execute('''
            INSERT INTO autonomous_actions (
                timestamp, industry, trigger_metric, trigger_value, 
                rag_context, llm_decision, status
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (timestamp, industry, metric, value, context, decision,
              'EXECUTED'))
    conn.commit()
    conn.close()


def query_chromadb(client, industry):
    """Retrieve standard operating procedures from ChromaDB."""
    try:
        collection = client.get_collection(f"rag_{industry}")
        results = collection.query(
            query_texts=[
                f"Standard Operating Procedure for emergency overrides in "
                f"{industry}"
            ],
            n_results=1
        )
        if results['documents'] and results['documents'][0]:
            return results['documents'][0][0]
    except Exception:
        pass
    return "No specific manual found."


def query_ollama(industry, metric, value, context):
    """Query local Llama3 model for autonomous decision-making."""
    prompt = (
        f"You are the AI-BS Swarm Commander overseeing the {industry} "
        f"sector. Metric '{metric}' is critically high at {value}. "
        f"Context from manual: {context}. What is your immediate "
        f"autonomous action?"
    )

    max_retries = 5
    base_delay = 11.0  # 11-second base delay per user mandate

    for attempt in range(max_retries):
        try:
            response = requests.post("http://localhost:11434/api/generate",
                                     json={
                                         "model": "llama3",
                                         "prompt": prompt,
                                         "stream": False
                                     }, timeout=10.0)

            if response.status_code == 200:
                return response.json().get("response",
                                           "ERROR: Empty LLM output.")
            if response.status_code == 429:
                delay = base_delay * (2 ** attempt)
                print(f"[RATE LIMIT] LLM exhausted. Backing off for "
                      f"{delay} seconds (Attempt {attempt+1}/{max_retries}).")
                time.sleep(delay)
                continue
        except Exception:
            delay = base_delay * (2 ** attempt)
            time.sleep(delay)
            continue

    return ("[Fallback Logic] Unable to reach LLM after retries. "
            "Initiating automated load-shedding sequence.")


def query_gemini_fallback(industry, decision):
    """Fallback to Google Gemini API for environment mutation generation."""
    api_key = os.environ.get("GEMINI_API_KEY", "")
    if not api_key:
        try:
            env_path = os.path.join("C:\\AI-BS", ".env")
            with open(env_path, "r", encoding="utf-8") as f:
                for line in f:
                    if line.startswith("GEMINI_API_KEY="):
                        api_key = line.strip().split("=", 1)[1]
                        break
        except Exception:
            pass

    if not api_key:
        return ('{"weather": "default", "lighting": "default", '
                '"alert_level": "normal"}')

    prompt = (
        f"Given the industry '{industry}' and the strategic decision: "
        f"'{decision}', generate a JSON payload describing the "
        f"environmental changes for a 3D simulation. Include keys for "
        f"'weather', 'lighting', and 'alert_level'."
    )

    try:
        url = (
            "https://generativelanguage.googleapis.com/v1beta/"
            "models/gemini-1.5-flash:generateContent?key=" + api_key
        )
        headers = {'Content-Type': 'application/json'}
        data = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {
                "responseMimeType": "application/json"
            }
        }
        response = requests.post(url, headers=headers, json=data, timeout=10.0)
        if response.status_code == 200:
            result = response.json()
            text = result['candidates'][0]['content']['parts'][0]['text']

            # Clean markdown fences so the DB stores valid, parseable JSON
            clean_json = text.strip()
            if clean_json.startswith("```json"):
                clean_json = clean_json[7:]
            if clean_json.startswith("```"):
                clean_json = clean_json[3:]
            if clean_json.endswith("```"):
                clean_json = clean_json[:-3]
            return clean_json.strip()

        return f'{{"error": "Gemini API failed status {response.status_code}"}}'
    except Exception as exc:
        return f'{{"error": "Gemini API exception: {str(exc)}"}}'


def query_genie3_environment(industry, metric, llm_decision):
    """Query the local Genie 3 endpoint to mutate the 3D environment."""
    url = "http://localhost:8888/genie/mutate"
    try:
        response = requests.post(url, json={
            "industry": industry,
            "metric": metric,
            "decision": llm_decision
        }, timeout=2.0)
        if response.status_code == 200:
            return response.text
        raise RuntimeError("Genie 3 unreachable")
    except Exception:
        print("[FALLBACK] Genie 3 unreachable. Falling back to Gemini...")
        return query_gemini_fallback(industry, llm_decision)


def process_target(chroma_client, target_industry):
    """Analyze a specific industry sector database for critical telemetry."""
    db_path = os.path.join(RESOURCE_DIR, f"{target_industry}.db")
    if os.path.exists(db_path):
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        c = conn.cursor()
        try:
            c.execute(
                "SELECT * FROM system_telemetry ORDER BY timestamp DESC LIMIT 1"
            )
            row = c.fetchone()
            if row:
                val = row['value']
                if val > 85.0:
                    metric = row['metric']
                    print(f"[ALERT] {target_industry.upper()} | "
                          f"{metric} spike at {val}!")
                    context = query_chromadb(chroma_client, target_industry)
                    decision = query_ollama(target_industry, metric,
                                            val, context)
                    print(f" -> Decision: {decision}")

                    world_mutation = query_genie3_environment(
                        target_industry, metric, decision
                    )
                    print(f" -> World Mutation: {world_mutation}")

                    log_action(target_industry, metric, val,
                               context, decision, world_mutation)
        except Exception:
            pass
        finally:
            conn.close()


async def worker_loop(worker_id, chroma_client):
    """Run continuous monitoring loop for a specific worker."""
    try:
        while True:
            target_industry = random.choice(industry_keys)
            await asyncio.to_thread(process_target, chroma_client,
                                    target_industry)
            await asyncio.sleep(1.0)
    except asyncio.CancelledError:
        print(f"Worker {worker_id} shutting down.")


async def main_async():
    """Initialize resources and start async Swarm Commander loops."""
    init_actions_db()

    print("Initializing ChromaDB connection...")
    chroma_client = chromadb.PersistentClient(path=CHROMA_DIR)

    print("Swarm Commander active. Monitoring 70 sector databases...")
    send_discord_update(
        "AI-BS Phase 17: Local LLM Autonomous Agents (Swarm Commander) active."
    )

    workers = [
        asyncio.create_task(worker_loop(i, chroma_client)) for i in range(5)
    ]
    try:
        await asyncio.gather(*workers)
    except KeyboardInterrupt:
        print("Swarm Commander shutting down.")
        for worker in workers:
            worker.cancel()


def main():
    """Application entry point."""
    try:
        asyncio.run(main_async())
    except KeyboardInterrupt:
        print("Swarm Commander shutting down.")


if __name__ == "__main__":
    main()
