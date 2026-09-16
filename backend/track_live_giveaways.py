import requests
import json
import re
import sys
from datetime import datetime

sys.stdout.reconfigure(encoding='utf-8')

API_KEY = "AIzaSyAO_FJ2SlqU8Q4STEHLGCilw_Y9_11qcW8"
VIDEO_ID = "rq2LZe3hcUU"

def get_live_chat():
    url_stream = f"https://www.youtube.com/watch?v={VIDEO_ID}"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36'
    }
    r = requests.get(url_stream, headers=headers)
    match = re.search(r'"continuation":"([^"]+)"', r.text)
    if not match:
        return []
    
    continuation = match.group(1)
    url_chat = f"https://www.youtube.com/youtubei/v1/live_chat/get_live_chat?key={API_KEY}"
    payload = {
        "context": {
            "client": {
                "clientName": "WEB",
                "clientVersion": "2.20260828.01.00",
                "hl": "en",
                "gl": "US"
            }
        },
        "continuation": continuation
    }
    
    r_chat = requests.post(url_chat, json=payload, headers=headers)
    data = r_chat.json()
    
    actions = data.get('continuationContents', {}).get('liveChatContinuation', {}).get('actions', [])
    messages = []
    
    for a in actions:
        item = a.get('addChatItemAction', {}).get('item', {})
        # Text message
        text_renderer = item.get('liveChatTextMessageRenderer')
        if text_renderer:
            author = text_renderer.get('authorName', {}).get('simpleText', '')
            badges = text_renderer.get('authorBadges', [])
            is_mod = any('moderator' in str(b).lower() or 'owner' in str(b).lower() for b in badges)
            runs = text_renderer.get('message', {}).get('runs', [])
            text = "".join([r.get('text', '') for r in runs])
            messages.append({"author": author, "text": text, "is_mod": is_mod, "type": "chat"})
        
        # Q&A / Banner action
        qna = a.get('showLiveChatActionPanelAction') or a.get('addLiveChatTickerItemAction')
        if qna:
            messages.append({"author": "SYSTEM_QNA", "text": str(qna), "is_mod": True, "type": "qna"})
            
    return messages

msgs = get_live_chat()
print(f"[{datetime.now().strftime('%H:%M:%S')}] Monitored {len(msgs)} live stream messages.")

mod_msgs = [m for m in msgs if m['is_mod'] or m['author'].lower() in ['cymatics', 'cymaticsfm', 'stevencymatics', 'devincymatics']]
trivia_triggers = [m for m in msgs if any(w in m['text'].lower() for w in ['question', 'trivia', 'guess', 'who wrote', 'what pack', 'what year', 'what suite', 'giveaway', 'winner'])]

if mod_msgs:
    print("\n👑 MODERATOR / HOST MESSAGES:")
    for m in mod_msgs[-5:]:
        print(f"  [@{m['author']}]: {m['text']}")

if trivia_triggers:
    print("\n🎯 RECENT TRIVIA / GIVEAWAY CHAT SIGNALS:")
    for t in trivia_triggers[-5:]:
        print(f"  [@{t['author']}]: {t['text']}")
