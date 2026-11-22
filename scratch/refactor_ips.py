import os
import glob

def refactor_ips():
    targets = glob.glob('C:/AI-BS/backend/**/*.py', recursive=True) + glob.glob('C:/AI-BS/backend/**/*.json', recursive=True)
    count = 0
    for file_path in targets:
        if not os.path.isfile(file_path): continue
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
            
            if 'localhost:11434' in content or '127.0.0.1:11434' in content:
                new_content = content.replace('localhost:11434', 'host.docker.internal:11434').replace('127.0.0.1:11434', 'host.docker.internal:11434')
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(new_content)
                print(f"Refactored: {file_path}")
                count += 1
        except Exception as e:
            print(f"Error on {file_path}: {e}")
            
    print(f"Total files refactored: {count}")

if __name__ == '__main__':
    refactor_ips()
