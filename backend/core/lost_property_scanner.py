import json
import os
import requests
import re
from pathlib import Path
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

SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
CLIENT_SECRET_FILE = Path(os.path.join(BASE_DIR, "client_secret.json"))
TOKEN_FILE = Path(os.path.join(BASE_DIR, "token.json"))


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
            creds = flow.run_local_server(port=0)
        with open(str(TOKEN_FILE), "w") as token:
            token.write(creds.to_json())
    return build("gmail", "v1", credentials=creds)


def call_stehouwer_llm(sender, subject):
    prompt = f"""You are an expert at identifying companies from emails.
Analyze the following email metadata to determine the company name and its category.
Categories allowed: "Crypto", "Finance", "Social", "Utility", "Other".
Respond strictly in JSON format: {{"company": "CompanyName", "category": "CategoryName"}}
Do not include any other text.

Sender: {sender}
Subject: {subject}
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
            return json.loads(data)
    except Exception as e:
        print(f"LLM Error: {e}")
    return {"company": "Unknown", "category": "Other"}


def run_scan():
    if not CLIENT_SECRET_FILE.exists():
        return {"error": "client_secret.json not found in C:\\AI-BS\\"}

    cache_file = Path(os.path.dirname(__file__)) / "lost_property_cache.json"
    results = []

    try:
        print("Connecting to Gmail API via OAuth 2.0...")
        service = get_gmail_service()

        # Search criteria: "Welcome to" OR "Verify your email" OR "Account created" OR "Confirm your registration" OR "Registration successful"
        query = 'subject:("Welcome to" OR "Verify your email" OR "Account created" OR "Confirm your registration" OR "Registration successful")'

        res = (
            service.users()
            .messages()
            .list(userId="me", q=query, maxResults=100)
            .execute()
        )
        messages = res.get("messages", [])

        print(f"Found {len(messages)} potential account emails. Processing...")

        for msg in messages:
            msg_data = (
                service.users()
                .messages()
                .get(
                    userId="me",
                    id=msg["id"],
                    format="metadata",
                    metadataHeaders=["From", "Subject"],
                )
                .execute()
            )
            headers = msg_data.get("payload", {}).get("headers", [])

            subject = ""
            sender = ""
            for h in headers:
                if h["name"] == "Subject":
                    subject = h["value"]
                if h["name"] == "From":
                    sender = h["value"]

            if sender and subject:
                # Extract email address if format is "Name <email@domain.com>"
                match = re.search(r"<(.+?)>", sender)
                email_addr = match.group(1) if match else sender

                # Use LLM to classify
                analysis = call_stehouwer_llm(email_addr, subject)

                results.append(
                    {
                        "sender": email_addr,
                        "subject": subject,
                        "company": analysis.get("company", "Unknown"),
                        "category": analysis.get("category", "Other"),
                    }
                )

        # Save to cache
        with open(cache_file, "w") as f:
            json.dump(results, f, indent=4)

        return {"status": "success", "count": len(results), "data": results}

    except Exception as e:
        return {"error": str(e)}


def run_web_osint_scan(target_email: str, scan_type: str = "all"):
    """Scans public web index for mentions of the target email across DuckDuckGo, pastebins, and breach leaks."""
    try:
        from duckduckgo_search import DDGS
    except ImportError:
        return {"error": "duckduckgo_search module not installed."}

    if not target_email or "@" not in target_email:
        return {"error": "Invalid email address provided."}

    print(
        f"Starting OSINT Web Leak & Pastebin Scan for: {target_email} (Type: {scan_type})"
    )
    ddgs = DDGS()

    queries = []
    if scan_type == "pastebin":
        queries = [
            f'"{target_email}" site:pastebin.com OR site:ghostbin.com OR site:justpaste.it OR site:rentry.co'
        ]
    elif scan_type == "breach":
        queries = [
            f'"{target_email}" breach OR leaked OR password OR combo OR database OR dump'
        ]
    elif scan_type == "code_leaks":
        queries = [
            f'"{target_email}" site:github.com OR site:gitlab.com secrets OR key OR token OR password'
        ]
    else:
        queries = [
            f'"{target_email}"',
            f'"{target_email}" site:pastebin.com OR site:ghostbin.com OR site:justpaste.it',
            f'"{target_email}" breach OR leaked OR password OR combo OR dump',
            f'"{target_email}" site:github.com OR site:gitlab.com secrets OR token',
        ]

    results_list = []
    seen_urls = set()

    try:
        for q in queries:
            hits = list(ddgs.text(q, max_results=8))
            for h in hits:
                url = h.get("href", "")
                if url and url not in seen_urls:
                    seen_urls.add(url)
                    snippet = h.get("body", "")
                    title = h.get("title", "Unknown Title")

                    # Determine threat severity rating
                    severity = "PUBLIC_MENTION"
                    snippet_lower = snippet.lower()
                    url_lower = url.lower()

                    if any(
                        term in snippet_lower or term in url_lower
                        for term in [
                            "password",
                            "hash",
                            "combo",
                            "db dump",
                            "leaked",
                            "private key",
                            "secret",
                        ]
                    ):
                        severity = "CRITICAL_LEAK"
                    elif any(
                        term in url_lower
                        for term in [
                            "pastebin.com",
                            "ghostbin",
                            "justpaste.it",
                            "rentry.co",
                            "paste",
                        ]
                    ):
                        severity = "PASTEBIN_LEAK"
                    elif "github.com" in url_lower or "gitlab.com" in url_lower:
                        severity = "CODE_LEAK"

                    results_list.append(
                        {
                            "title": title,
                            "url": url,
                            "snippet": snippet,
                            "severity": severity,
                            "query_used": q,
                        }
                    )
        return {
            "status": "success",
            "count": len(results_list),
            "data": results_list,
            "target_email": target_email,
        }
    except Exception as e:
        return {"error": str(e)}


if __name__ == "__main__":
    import sys

    sys.stdout.reconfigure(encoding="utf-8")
    print(run_scan())
