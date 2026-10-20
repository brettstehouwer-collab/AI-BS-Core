import subprocess
import time
import urllib.request
import json

chrome_exe = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
proc = subprocess.Popen([
    chrome_exe,
    "--remote-debugging-port=9222",
    r'--user-data-dir=C:\Users\footb\.cache\chrome-devtools-mcp\chrome-profile',
    '--no-first-run',
    '--no-default-browser-check',
    '--disable-blink-features=AutomationControlled'
])
time.sleep(3)

try:
    with urllib.request.urlopen("http://127.0.0.1:9222/json/version", timeout=3) as resp:
        data = json.loads(resp.read().decode())
        print("SUCCESS! Connected to Chrome DevTools on Port 9222:")
        print(json.dumps(data, indent=2))
except Exception as e:
    print(f"FAILED to query port 9222: {e}")
