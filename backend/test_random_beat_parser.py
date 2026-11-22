import requests
import json
import sys

sys.stdout.reconfigure(encoding='utf-8')

url = "http://127.0.0.1:8080/api/audio/assistant/chat"

# We must restart backend first for it to pick up the python changes or test direct import
from routers.music_assistant_router import parse_heuristic_actions

for prompt in [
    "now i want it to be able to randome a beat non of that cyber punk stuff",
    "random a beat",
    "give me a random groove no cyberpunk"
]:
    res = parse_heuristic_actions(prompt, None)
    print("=" * 60)
    print("PROMPT:", prompt)
    print("ACTIONS:", json.dumps(res.get("actions"), indent=2))
    print("REPLY:\n", res.get("reply"))
