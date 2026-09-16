import sys
import requests
import json
import re

sys.stdout.reconfigure(encoding='utf-8')

video_id = "rq2LZe3hcUU"
headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'}

r = requests.get(f"https://www.youtube.com/watch?v={video_id}", headers=headers)

# Extract apiKey and continuation token from initial data
api_key_match = re.search(r'"INNERTUBE_API_KEY":"([^"]+)"', r.text)
continuation_match = re.search(r'"liveChatRenderer":{"continuations":\[{"invalidationContinuationData":{"continuation":"([^"]+)"', r.text) or re.search(r'"continuation":"([^"]+)"', r.text)

print(f"API Key: {api_key_match.group(1) if api_key_match else 'Not found'}")
print(f"Continuation: {continuation_match.group(1)[:40] if continuation_match else 'Not found'}...")

if api_key_match and continuation_match:
    api_key = api_key_match.group(1)
    continuation = continuation_match.group(1)
    
    post_url = f"https://www.youtube.com/youtubei/v1/live_chat/get_live_chat?key={api_key}"
    payload = {
        "context": {
            "client": {
                "clientName": "WEB",
                "clientVersion": "2.20240826.01.00"
            }
        },
        "continuation": continuation
    }
    
    resp = requests.post(post_url, json=payload, headers=headers)
    if resp.status_code == 200:
        data = resp.json()
        actions = data.get("continuationContents", {}).get("liveChatContinuation", {}).get("actions", [])
        print(f"Chat actions retrieved: {len(actions)}")
        for a in actions[-15:]:
            item = a.get("addChatItemAction", {}).get("item", {}).get("liveChatTextMessageRenderer", {})
            if item:
                author = item.get("authorName", {}).get("simpleText", "Unknown")
                runs = item.get("message", {}).get("runs", [])
                msg = "".join([r.get("text", "") for r in runs])
                print(f"[{author}]: {msg}")
    else:
        print(f"Live chat request failed with status: {resp.status_code}")
