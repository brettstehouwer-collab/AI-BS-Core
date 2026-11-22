import os
import re

filepath = r'C:\AI-BS\frontend\components\ProjectNoCoStudioTab.jsx'
with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

content = re.sub(r"minHeight:\s*'100vh',", "height: '100%',\n      overflowY: 'auto',", content)

with open(filepath, 'w', encoding='utf-8') as f:
    f.write(content)

print("Scroll fix applied with regex!")
