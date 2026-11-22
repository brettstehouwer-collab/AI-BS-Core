import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

with open(r"C:\AI-BS\frontend\src\components\ChatTab.jsx", "r", encoding="utf-8") as f:
    for i, line in enumerate(f, 1):
        if any(term in line.lower() for term in ["hybrid-chat", "/stream", "handlesubmit", "onsubmit", "sendmessage", "onkeypress", "enter"]):
            if any(term in line.lower() for term in ["hybrid-chat", "/stream", "fetch", "handlesubmit"]):
                print(f"{i}: {line.strip()[:100]}")
