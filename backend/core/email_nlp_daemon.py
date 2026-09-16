import os
import json
import requests
import re
import time
import base64
from pathlib import Path
from datetime import datetime
from bs4 import BeautifulSoup
try:
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    from googleapiclient.discovery import build
except ImportError:
    Request = None
    Credentials = None
    InstalledAppFlow = None
    build = None

SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/gmail.compose",
    "https://www.googleapis.com/auth/gmail.modify",
]
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
CLIENT_SECRET_FILE = Path(os.path.join(BASE_DIR, "client_secret.json"))
TOKEN_FILE = Path(os.path.join(BASE_DIR, "token.json"))
CACHE_FILE = Path(os.path.join(os.path.dirname(__file__), "emails_cache.json"))
NLP_LEDGER = Path(os.path.join(os.path.dirname(__file__), "nlp_learning_ledger.jsonl"))


def index_email_thread_to_chroma(msg_id, sender, subject, body, nlp_analysis):
    """Indexes email thread into ChromaDB email_vector_vault for semantic context memory."""
    try:
        import chromadb

        client = None
        try:
            client = chromadb.HttpClient(host="localhost", port=8001)
        except Exception:
            chroma_dir = os.path.join(BASE_DIR, "saved_data", "chroma_db")
            os.makedirs(chroma_dir, exist_ok=True)
            client = chromadb.PersistentClient(path=chroma_dir)

        collection = client.get_or_create_collection(name="email_vector_vault")
        doc_text = f"From: {sender}\nSubject: {subject}\nSummary: {nlp_analysis.get('summary', '')}\nTone: {nlp_analysis.get('tone', '')}\nBody: {body[:1000]}"

        metadata = {
            "msg_id": str(msg_id),
            "sender": str(sender),
            "subject": str(subject),
            "urgency": str(nlp_analysis.get("urgency", "Low")),
            "category": str(nlp_analysis.get("category", "Other")),
            "client_id": "stehouwer_publishing",
        }

        collection.upsert(ids=[str(msg_id)], documents=[doc_text], metadatas=[metadata])
        print(f"[NLP Daemon] Indexed email {msg_id} into ChromaDB email_vector_vault.")
    except Exception as e:
        print(f"[NLP Daemon] ChromaDB indexing warning: {e}")


def get_gmail_service():
    creds = None
    if TOKEN_FILE.exists():
        creds = Credentials.from_authorized_user_file(str(TOKEN_FILE), SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                str(CLIENT_SECRET_FILE), SCOPES
            )
            # This pops open the browser for OAuth
            creds = flow.run_local_server(port=0)
        with open(str(TOKEN_FILE), "w") as token:
            token.write(creds.to_json())
    return build("gmail", "v1", credentials=creds)


def clean_text(text):
    if not text:
        return ""
    text = re.sub(r"[\r\n\t]+", " ", text).strip()
    return text


def extract_text_from_html(html):
    soup = BeautifulSoup(html, "html.parser")
    return clean_text(soup.get_text(separator=" "))


def parse_parts(service, parts, folder_name, message):
    """
    Utility function that parses the content of an email partition
    """
    if parts:
        for part in parts:
            mimeType = part.get("mimeType")
            body = part.get("body")
            data = body.get("data")
            if part.get("parts"):
                return parse_parts(service, part.get("parts"), folder_name, message)
            if mimeType == "text/plain":
                if data:
                    text = base64.urlsafe_b64decode(data).decode()
                    return text
            elif mimeType == "text/html":
                if data:
                    html = base64.urlsafe_b64decode(data).decode()
                    return extract_text_from_html(html)
    return ""


def call_stehouwer_llm_nlp(sender, subject, body):
    prompt = f"""You are Stehouwer LLM. Analyze the following email for Natural Language Processing (NLP) patterns, communication tone, urgency, category, sentiment, action items, and key entities.
Respond strictly in JSON format matching this schema:
{{
  "summary": "1-2 sentence concise executive summary",
  "tone": "Communication tone (e.g., Professional, Urgent, Friendly, Formal)",
  "urgency": "High", "Medium", or "Low",
  "category": "Work", "Financial", "Crypto", "Social", "Utility", or "Other",
  "sentiment": "Positive", "Neutral", or "Negative",
  "action_items": ["Action task 1", "Action task 2"],
  "entities": ["Extracted name/date/link/code 1", "Extracted name/date/link/code 2"],
  "style_patterns": ["Linguistic pattern 1", "Pattern 2"],
  "nlp_learning": "Key takeaway regarding sender's communication style"
}}
Do not include any markdown framing or extra text outside the JSON.

Sender: {sender}
Subject: {subject}
Body Snippet: {body[:1500]}
"""
    try:
        resp = requests.post(
            "http://127.0.0.1:11434/api/generate",
            json={
                "model": "stehouwer_llm",
                "prompt": prompt,
                "format": "json",
                "stream": False,
            },
            timeout=30,
        )
        if resp.status_code == 200:
            data = resp.json().get("response", "{}")
            parsed = json.loads(data)
            # Ensure defaults for keys
            return {
                "summary": parsed.get("summary", "No summary generated."),
                "tone": parsed.get("tone", "Professional"),
                "urgency": parsed.get("urgency", "Low"),
                "category": parsed.get("category", "Other"),
                "sentiment": parsed.get("sentiment", "Neutral"),
                "action_items": (
                    parsed.get("action_items", [])
                    if isinstance(parsed.get("action_items"), list)
                    else []
                ),
                "entities": (
                    parsed.get("entities", [])
                    if isinstance(parsed.get("entities"), list)
                    else []
                ),
                "style_patterns": (
                    parsed.get("style_patterns", [])
                    if isinstance(parsed.get("style_patterns"), list)
                    else []
                ),
                "nlp_learning": parsed.get(
                    "nlp_learning", "Extracted structural metrics."
                ),
            }
    except Exception as e:
        print(f"[NLP Daemon] LLM Error: {e}")
    return {
        "summary": "Analysis pending or LLM unavailable.",
        "tone": "Neutral",
        "urgency": "Low",
        "category": "Other",
        "sentiment": "Neutral",
        "action_items": [],
        "entities": [],
        "style_patterns": [],
        "nlp_learning": "Failed to analyze.",
    }


def run_email_daemon_cycle():
    print(
        f"[{datetime.now().isoformat()}] [NLP Daemon] Waking up to check Gmail API via OAuth..."
    )

    if not CLIENT_SECRET_FILE.exists():
        print("[NLP Daemon] Error: client_secret.json not found in C:\\AI-BS\\")
        return

    try:
        service = get_gmail_service()

        # Load existing cache to preserve existing NLP analyses if available
        existing_cache_by_id = {}
        if CACHE_FILE.exists():
            try:
                with open(CACHE_FILE, "r", encoding="utf-8") as f:
                    cached_data = json.load(f)
                    for item in cached_data:
                        if isinstance(item, dict) and "id" in item:
                            existing_cache_by_id[item["id"]] = item
            except Exception as e:
                print(f"[NLP Daemon] Warning loading existing cache: {e}")

        # Fetch the last 50 emails
        results = service.users().messages().list(userId="me", maxResults=50).execute()
        messages = results.get("messages", [])

        if not messages:
            print("[NLP Daemon] Inbox is empty.")
            return

        emails_list = []
        newest_ids = []

        for msg in messages:
            msg_data = (
                service.users()
                .messages()
                .get(userId="me", id=msg["id"], format="full")
                .execute()
            )
            payload = msg_data.get("payload", {})
            headers = payload.get("headers", [])

            subject = ""
            sender = ""
            date = ""
            for d in headers:
                if d["name"] == "Subject":
                    subject = d["value"]
                if d["name"] == "From":
                    sender = d["value"]
                if d["name"] == "Date":
                    date = d["value"]

            parts = payload.get("parts", [])
            body = ""
            if parts:
                body = parse_parts(service, parts, "Inbox", msg_data)
            else:
                body_data = payload.get("body", {}).get("data")
                if body_data:
                    decoded = base64.urlsafe_b64decode(body_data).decode()
                    if payload.get("mimeType") == "text/html":
                        body = extract_text_from_html(decoded)
                    else:
                        body = clean_text(decoded)

            clean_body = clean_text(body)
            snippet = msg_data.get("snippet", "")

            # Check if we already have NLP analysis cached
            existing_nlp = existing_cache_by_id.get(msg["id"], {}).get("nlp_analysis")

            emails_list.append(
                {
                    "id": msg["id"],
                    "sender": sender,
                    "subject": subject,
                    "date": date,
                    "snippet": snippet,
                    "body": clean_body,
                    "nlp_analysis": existing_nlp,
                }
            )
            newest_ids.append(msg["id"])

        # NLP Learning on new or un-analyzed emails
        processed_ids = set()
        PROCESSED_TRACKER = Path(
            os.path.join(os.path.dirname(__file__), "nlp_processed_ids.json")
        )
        if PROCESSED_TRACKER.exists():
            try:
                with open(PROCESSED_TRACKER, "r") as f:
                    processed_ids = set(json.load(f))
            except Exception:
                pass

        for em in emails_list:
            if em["id"] not in processed_ids or not em.get("nlp_analysis"):
                print(
                    f"[{datetime.now().isoformat()}] [NLP Daemon] Analyzing email via Stehouwer LLM: {em['subject'][:30]}..."
                )
                nlp_result = call_stehouwer_llm_nlp(
                    em["sender"], em["subject"], em["body"]
                )
                em["nlp_analysis"] = nlp_result

                log_entry = {
                    "timestamp": datetime.now().isoformat(),
                    "email_id": em["id"],
                    "sender": em["sender"],
                    "nlp_analysis": nlp_result,
                }

                with open(NLP_LEDGER, "a", encoding="utf-8") as f:
                    f.write(json.dumps(log_entry) + "\n")

                # Index into ChromaDB email_vector_vault
                index_email_thread_to_chroma(
                    em["id"], em["sender"], em["subject"], em["body"], nlp_result
                )

                processed_ids.add(em["id"])
                # Zero Limits Policy: No rate limit delay on processing

        with open(PROCESSED_TRACKER, "w", encoding="utf-8") as f:
            json.dump(list(processed_ids), f)

        # Update cache for the UI with full NLP data
        with open(CACHE_FILE, "w", encoding="utf-8") as f:
            json.dump(emails_list, f, indent=4)
        print(
            f"[{datetime.now().isoformat()}] [NLP Daemon] Cached {len(emails_list)} emails with NLP analysis for UI."
        )

    except Exception as e:
        print(f"[{datetime.now().isoformat()}] [NLP Daemon] Fatal Error: {e}")


if __name__ == "__main__":
    import sys

    sys.stdout.reconfigure(encoding="utf-8")
    print("==================================================")
    print("Booting NLP Email Learning Daemon (OAuth 2.0 Edition)...")
    print("==================================================")
    while True:
        run_email_daemon_cycle()
        print(
            f"[{datetime.now().isoformat()}] [NLP Daemon] Sleeping for 300 seconds..."
        )
        time.sleep(300)
