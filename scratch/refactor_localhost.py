import os
import re

components_dir = r"C:\AI-BS\frontend\components"

def refactor_file(file_path):
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    original = content
    
    # 1. Replace http://localhost:8000 or http://127.0.0.1:8000 directly with ${backendUrl}
    # Handling cases like 'http://localhost:8000/api/chat' -> `${backendUrl}/api/chat`
    content = re.sub(
        r"['\"]http://(?:localhost|127\.0\.0\.1):8000(/?.*?)['\"]",
        r"`${backendUrl}\1`",
        content
    )
    
    # 2. Replace other ports with the proxy route
    # E.g. 'http://localhost:8001/api/v1/vault/query' -> `${backendUrl}/api/proxy/8001/api/v1/vault/query`
    def proxy_replacer(match):
        port = match.group(1)
        path = match.group(2) or ""
        # If the URL is inside a template literal already e.g. `http://localhost:3001/api/fetch`
        # we return `${backendUrl}/api/proxy/3001/api/fetch`
        # Wait, if it's already a backtick, we keep backticks. The regex matches the quote type but we will just output backticks.
        # Ensure path starts with / if it doesn't
        if path and not path.startswith('/'):
            path = '/' + path
        return f"`${{backendUrl}}/api/proxy/{port}{path}`"

    content = re.sub(
        r"['\"`]http://(?:localhost|127\.0\.0\.1):(\d{4,})(.*?)['\"`]",
        proxy_replacer,
        content
    )
    
    # Exclude AdminSecurityMonitorTab if it's just curl documentation blocks
    if "AdminSecurityMonitorTab.jsx" in file_path:
        # Revert the curl doc blocks if they got matched
        content = content.replace("`curl -X POST `${backendUrl}/v1/images", "`curl -X POST http://localhost:8000/v1/images")
        content = content.replace("`curl -X POST `${backendUrl}/v1/chat", "`curl -X POST http://localhost:8000/v1/chat")
        content = content.replace("Exposes <code>`${backendUrl}/v1`</code>", "Exposes <code>http://localhost:8000/v1</code>")
        content = content.replace("tunnel --url `${backendUrl}`", "tunnel --url http://localhost:8000")
        
    if content != original:
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"Refactored: {os.path.basename(file_path)}")

for root, _, files in os.walk(components_dir):
    for file in files:
        if file.endswith(".jsx"):
            refactor_file(os.path.join(root, file))
            
print("Done refactoring.")
