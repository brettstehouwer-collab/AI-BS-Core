import os, re

count = 0
for root, dirs, files in os.walk('frontend/components'):
    for file in files:
        if file.endswith('.jsx'):
            path = os.path.join(root, file)
            with open(path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Patch { flex: 1, overflow: 'hidden' }
            new_content = re.sub(
                r"\{\{\s*flex:\s*1,\s*overflow:\s*'hidden'\s*\}\}", 
                "{{ flex: 1, display: 'flex', flexDirection: 'column', overflow: 'hidden' }}", 
                content
            )
            
            # Patch { flex: 1, overflow: 'hidden', position: 'relative' }
            new_content = re.sub(
                r"\{\{\s*flex:\s*1,\s*overflow:\s*'hidden',\s*position:\s*'relative'\s*\}\}", 
                "{{ flex: 1, display: 'flex', flexDirection: 'column', overflow: 'hidden', position: 'relative' }}", 
                new_content
            )
            
            if new_content != content:
                with open(path, 'w', encoding='utf-8') as f:
                    f.write(new_content)
                print(f'Patched {file}')
                count += 1

print(f'Total patched: {count}')
