"""
vault_auto_ingestor.py — AI-BS Automated Knowledge Vault & LLM Training Pipeline (v5.32.0)
Extracts, organizes, and vaults user-submitted API code snippets, headers, endpoints, 
and JSON response payloads into AI-BS_Knowledge_Vaults/ for RAG and LLM fine-tuning.
"""

import os
import json
import time
import hashlib
from typing import Optional, Dict, Any, List
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

VAULT_DIR = r"C:\AI-BS\backend\AI-BS_Knowledge_Vaults"
SNIPPETS_FILE = os.path.join(VAULT_DIR, "api_code_snippets_vault.json")
LLM_DATASET_FILE = os.path.join(VAULT_DIR, "llm_training_dataset.jsonl")

os.makedirs(VAULT_DIR, exist_ok=True)

router = APIRouter(prefix="/api/vault", tags=["Knowledge Vault Ingestor"])


class SnippetIngestPayload(BaseModel):
    title: str
    language: str  # "go", "python", "javascript", "curl"
    host: str
    endpoint: str
    code_snippet: str
    sample_payload: Optional[Dict[str, Any]] = None
    category: Optional[str] = "RapidAPI"


# Initial Seed Snippets (Validated Weather & Google Trends)
SEED_SNIPPETS = [
    {
        "id": "snippet_weather_geocode_01",
        "title": "Reverse Geocoding & Weather API",
        "language": "go",
        "host": "geocoding-reverse-geocoding-and-weather.p.rapidapi.com",
        "endpoint": "/weather?lat=42.9634&lon=-85.6681",
        "category": "Weather & GIS",
        "code_snippet": """package main

import (
	"fmt"
	"io"
	"net/http"
)

func main() {
	url := "https://geocoding-reverse-geocoding-and-weather.p.rapidapi.com/weather?lat=42.9634&lon=-85.6681"

	req, _ := http.NewRequest("GET", url, nil)
	req.Header.Add("x-rapidapi-key", "YOUR_RAPIDAPI_KEY")
	req.Header.Add("x-rapidapi-host", "geocoding-reverse-geocoding-and-weather.p.rapidapi.com")

	res, _ := http.DefaultClient.Do(req)
	defer res.Body.Close()

	body, _ := io.ReadAll(res.Body)
	fmt.Println(string(body))
}""",
        "sample_payload": {
          "lat": 42.9634,
          "lon": -85.6681,
          "timezone": "America/Detroit",
          "elevationM": 204,
          "current": {
            "time": "2026-08-19T13:45",
            "tempC": 25.7,
            "feelsLikeC": 28.4,
            "humidityPct": 56,
            "precipitationMm": 0,
            "windKmh": 7.3
          }
        },
        "timestamp": time.time()
    },
    {
        "id": "snippet_google_trends_02",
        "title": "Google Trends Keywords API (YouTube Bitcoin Interest)",
        "language": "go",
        "host": "google-trends-keywords-api.p.rapidapi.com",
        "endpoint": "/api/googletrends/interest?page=1&limit=50&geo=US&property=youtube&category=finance&q=bitcoin&timeframe=12m",
        "category": "Market Trends",
        "code_snippet": """package main

import (
	"fmt"
	"io"
	"net/http"
)

func main() {
	url := "https://google-trends-keywords-api.p.rapidapi.com/api/googletrends/interest?page=1&limit=50&geo=US&property=youtube&category=finance&q=bitcoin&timeframe=12m"

	req, _ := http.NewRequest("GET", url, nil)
	req.Header.Add("x-rapidapi-key", "YOUR_RAPIDAPI_KEY")
	req.Header.Add("x-rapidapi-host", "google-trends-keywords-api.p.rapidapi.com")
	req.Header.Add("Content-Type", "application/json")

	res, _ := http.DefaultClient.Do(req)
	defer res.Body.Close()

	body, _ := io.ReadAll(res.Body)
	fmt.Println(string(body))
}""",
        "sample_payload": {
          "data": [
            { "date": "Aug 17, 2025", "values": [68], "formatted_values": ["68"] },
            { "date": "Aug 24, 2025", "values": [58], "formatted_values": ["58"] },
            { "date": "Aug 31, 2025", "values": [59], "formatted_values": ["59"] }
          ]
        },
        "timestamp": time.time()
    }
]


def load_vault_snippets() -> List[Dict[str, Any]]:
    if not os.path.exists(SNIPPETS_FILE):
        save_vault_snippets(SEED_SNIPPETS)
        return SEED_SNIPPETS
    try:
        with open(SNIPPETS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return SEED_SNIPPETS


def save_vault_snippets(snippets: List[Dict[str, Any]]):
    with open(SNIPPETS_FILE, "w", encoding="utf-8") as f:
        json.dump(snippets, f, indent=2)

    # Append to LLM Fine-Tuning JSONL
    with open(LLM_DATASET_FILE, "a", encoding="utf-8") as f_jsonl:
        for s in snippets:
            dataset_entry = {
                "instruction": f"Provide the {s.get('language', 'go').upper()} code snippet and sample JSON payload for connecting to {s.get('host')}.",
                "input": f"Endpoint: {s.get('endpoint')}",
                "output": f"Code:\n```go\n{s.get('code_snippet')}\n```\n\nSample Response JSON:\n```json\n{json.dumps(s.get('sample_payload', {}), indent=2)}\n```"
            }
            f_jsonl.write(json.dumps(dataset_entry) + "\n")


@router.get("/snippets")
def list_snippets():
    """Returns all vaulted API code snippets & payloads."""
    snippets = load_vault_snippets()
    return {"status": "success", "count": len(snippets), "snippets": snippets}


@router.post("/ingest")
def ingest_snippet(payload: SnippetIngestPayload):
    """Ingests a new code snippet & payload into Knowledge Vault & LLM training dataset."""
    snippets = load_vault_snippets()
    
    new_entry = {
        "id": f"snippet_{int(time.time())}_{hashlib.md5(payload.code_snippet.encode()).hexdigest()[:6]}",
        "title": payload.title,
        "language": payload.language,
        "host": payload.host,
        "endpoint": payload.endpoint,
        "category": payload.category or "RapidAPI",
        "code_snippet": payload.code_snippet,
        "sample_payload": payload.sample_payload or {},
        "timestamp": time.time()
    }
    
    snippets.append(new_entry)
    save_vault_snippets(snippets)
    
    return {"status": "success", "entry": new_entry}


# Initialize on import
load_vault_snippets()
