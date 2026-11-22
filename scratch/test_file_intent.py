import re

def detect_file_read(prompt):
    p = prompt.strip()
    p_lower = p.lower()
    
    # Check slash commands first
    if p_lower.startswith(('/read', '/cat', '/view', '/file')):
        parts = p.split(maxsplit=1)
        if len(parts) > 1:
            target = parts[1].strip().strip('"\'`')
            return target, ''
        return '', ''
        
    # Natural language read patterns
    patterns = [
        r'(?:please\s+|can\s+you\s+|could\s+you\s+)?(?:read|view|cat|inspect|open|show(?:\s+me)?|display|check)(?:\s+the)?\s+(?:contents?\s+of\s+)?(?:file\s+)?([a-zA-Z]:\\[^\s"\'`]+|(?:\.{1,2}[\\/]|[a-zA-Z0-9_\-\.]+[\\/])[^\s"\'`]+|[a-zA-Z0-9_\-]+\.(?:txt|py|js|jsx|ts|tsx|json|md|html|css|env|bat|sh|yml|yaml|sql|csv|conf|toml))(?:\s+(?:and|to)\s+(.*))?',
        r'what(?:\'s|\s+is)\s+in(?:\s+the)?\s+(?:file\s+)?([a-zA-Z]:\\[^\s"\'`]+|(?:\.{1,2}[\\/]|[a-zA-Z0-9_\-\.]+[\\/])[^\s"\'`]+|[a-zA-Z0-9_\-]+\.(?:txt|py|js|jsx|ts|tsx|json|md|html|css|env|bat|sh|yml|yaml|sql|csv|conf|toml))(?:\s+(?:and|to)\s+(.*))?'
    ]
    for pat in patterns:
        m = re.search(pat, p, flags=re.IGNORECASE)
        if m:
            path = m.group(1).strip('"\'`')
            q = m.group(2).strip() if len(m.groups()) > 1 and m.group(2) else ''
            return path, q
    return None, None

def detect_file_write(prompt):
    p = prompt.strip()
    p_lower = p.lower()
    
    # Slash commands
    if p_lower.startswith(('/write', '/save', '/create_file')):
        parts = p.split(maxsplit=2)
        if len(parts) >= 3:
            path = parts[1].strip().strip('"\'`')
            content = parts[2].strip()
            return path, content
        elif len(parts) == 2:
            return parts[1].strip().strip('"\'`'), ''
            
    # Natural language write patterns
    # 1. Match code blocks: write to file <path> \n ```...```
    code_block_match = re.search(r'```(?:[a-zA-Z0-9_\-]+)?\r?\n([\s\S]*?)\r?\n```', prompt)
    path_match = re.search(r'(?:write|save|create|put|dump)(?:\s+(?:this|the)?(?:\s+(?:code|script|text|file))?)?\s+(?:to|in|into)?\s+(?:file\s+)?([a-zA-Z]:\\[^\s"\'`:]+|(?:\.{1,2}[\\/]|[a-zA-Z0-9_\-\.]+[\\/])[^\s"\'`:]+|[a-zA-Z0-9_\-]+\.(?:txt|py|js|jsx|ts|tsx|json|md|html|css|env|bat|sh|yml|yaml|sql|csv|conf|toml))(?::)?', prompt, flags=re.IGNORECASE)
    
    if path_match and code_block_match:
        target_path = path_match.group(1).strip('"\'`:')
        content = code_block_match.group(1)
        return target_path, content
        
    # 2. Match inline content: write to file <path> with content: <content>
    inline_match = re.search(r'(?:write|save|create)(?:\s+to)?\s+(?:file\s+)?([a-zA-Z]:\\[^\s"\'`:]+|(?:\.{1,2}[\\/]|[a-zA-Z0-9_\-\.]+[\\/])[^\s"\'`:]+|[a-zA-Z0-9_\-]+\.(?:txt|py|js|jsx|ts|tsx|json|md|html|css|env|bat|sh|yml|yaml|sql|csv|conf|toml))\s*(?::|\s+with(?:\s+the)?\s+(?:content|text|following):?\s*)([\s\S]+)', prompt, flags=re.IGNORECASE)
    if inline_match:
        return inline_match.group(1).strip('"\'`:'), inline_match.group(2).strip()
        
    return None, None

def detect_dir_scan(prompt):
    p = prompt.strip()
    p_lower = p.lower()
    
    if p_lower.startswith(('/ls', '/dir', '/tree', '/list_files')):
        parts = p.split(maxsplit=1)
        target = parts[1].strip().strip('"\'`') if len(parts) > 1 else '.'
        return target
        
    dir_match = re.search(r'(?:list|show(?:\s+me)?|display|scan|what\s+are)\s+(?:the\s+)?(?:files|contents|directory|folder)\s+(?:in|of|inside)\s+(?:the\s+)?(?:directory|folder\s+)?([a-zA-Z]:\\[^\s"\'`]+|(?:\.{1,2}[\\/]|[a-zA-Z0-9_\-\.]+[\\/])[^\s"\'`]+|[a-zA-Z0-9_\-\.\/\\]+)', p, flags=re.IGNORECASE)
    if dir_match:
        return dir_match.group(1).strip('"\'`')
        
    return None

read_tests = [
    '/read version.txt',
    'read C:\\AI-BS\\version.txt',
    'can you read the file backend/crypto_trader_bot.py and tell me what the resting order is',
    'what is in the file saved_checkpoint.md',
    'show me contents of file frontend/package.json',
    'cat version.txt',
    'tell me a joke'
]
print("=== READ TESTS ===")
for t in read_tests:
    path, q = detect_file_read(t)
    print(f"{t!r} -> path={path!r}, q={q!r}")

write_tests = [
    '/write scratch/test.txt Hello world from chat',
    'save this code to file scratch/hello.py:\n```python\nprint("hello world")\n```',
    'write to file scratch/notes.txt with content: Important meeting notes here',
    'can you write a song'
]
print("\n=== WRITE TESTS ===")
for t in write_tests:
    path, c = detect_file_write(t)
    print(f"{t[:40]!r} -> path={path!r}, content_len={len(c) if c else 0}")

dir_tests = [
    '/ls',
    '/ls backend',
    '/dir frontend/src',
    'list files in folder backend/core',
    'what are the files inside C:\\AI-BS\\scratch'
]
print("\n=== DIR TESTS ===")
for t in dir_tests:
    target = detect_dir_scan(t)
    print(f"{t!r} -> target={target!r}")
