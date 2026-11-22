import os
import re

backend_dir = r"c:\AI-BS\backend"
target_str = "host.docker.internal"
replacement_str = "127.0.0.1"

files_modified = 0
replacements_made = 0

for root, dirs, files in os.walk(backend_dir):
    for f in files:
        if f.endswith(".py") or f.endswith(".json"):
            filepath = os.path.join(root, f)
            try:
                with open(filepath, "r", encoding="utf-8") as file:
                    content = file.read()
                
                if target_str in content:
                    count = len(re.findall(re.escape(target_str), content))
                    new_content = content.replace(target_str, replacement_str)
                    
                    with open(filepath, "w", encoding="utf-8") as file:
                        file.write(new_content)
                    
                    files_modified += 1
                    replacements_made += count
                    print(f"Modified {f}: Replaced {count} instances.")
            except Exception as e:
                pass

print(f"\nSuccess! Modified {files_modified} files, replacing {replacements_made} instances of '{target_str}'.")
