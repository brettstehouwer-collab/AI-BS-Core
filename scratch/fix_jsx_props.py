import os
import re

components_dir = r"C:\AI-BS\frontend\components"

def fix_jsx_props(file_path):
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    original = content
    
    # Matches a prop assignment like backendUrl=`${backendUrl}/api/proxy/3000`
    # and replaces it with backendUrl={`${backendUrl}/api/proxy/3000`}
    # Regex looks for `word=`${...}`` where it's not wrapped in `{}`.
    # We can just look for `="` or `='` that got replaced by `=`` and wrap it in `={...}`.
    # Actually, the previous script replaced `['\"`]http...['\"`]` with ```${backendUrl}...```
    # If the original was `backendUrl="http..."` it became `backendUrl=`${backendUrl}...``
    # Let's fix this by finding `=(`\$\{backendUrl\}[^`]*`)` and replacing with `={$1}`
    
    content = re.sub(
        r"=(\`\$\{backendUrl\}[^\`]*\`)",
        r"={\1}",
        content
    )
    
    if content != original:
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"Fixed props in: {os.path.basename(file_path)}")

for root, _, files in os.walk(components_dir):
    for file in files:
        if file.endswith(".jsx"):
            fix_jsx_props(os.path.join(root, file))
            
print("Done fixing JSX props.")
