import os
import re

filepath = r'C:\AI-BS\frontend\components\ProjectNoCoStudioTab.jsx'
with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

pattern = r"(activeSubTab === 'master_plan_23acres'.*?)(?=activeSubTab === '|$)"
match = re.search(pattern, content, re.DOTALL)
if match:
    print(match.group(1)[:2000]) # Print the first 2000 chars of the block
else:
    print("Not found")
