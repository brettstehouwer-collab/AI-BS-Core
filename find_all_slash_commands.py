with open('C:/AI-BS/frontend/src/components/ChatTab.jsx', 'r', encoding='utf-8') as f:
    text = f.read()

import re
matches = re.findall(r"command\s*===\s*['\"](/[a-zA-Z0-9_-]+)['\"]", text)
print("All slash commands in ChatTab.jsx:", sorted(list(set(matches))))
