import os
import re

filepath = r'C:\AI-BS\frontend\components\ProjectNoCoStudioTab.jsx'
with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

pattern = r"(activeSubTab === 'bioenergy_rd'.*?)(?=activeSubTab === '|$)"
match = re.search(pattern, content, re.DOTALL)
if match:
    with open(r'C:\AI-BS\scratch\bioenergy_block.txt', 'w', encoding='utf-8') as out_f:
        out_f.write(match.group(1))
    print("Wrote to file")
else:
    print("Not found")
