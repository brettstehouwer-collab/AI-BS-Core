import os
import time

def scan_media():
    start = time.time()
    root_dir = r"C:\AI-BS"
    excludes = {"node_modules", ".git", ".venv", "venv", ".gemini", "dist", "build", "__pycache__", ".vscode", "python_embeded"}
    media_extensions = {".png", ".mp4", ".webp", ".gif", ".jpg", ".jpeg"}
    
    found = []
    
    for dirpath, dirnames, filenames in os.walk(root_dir):
        # Prune excluded directories
        dirnames[:] = [d for d in dirnames if d not in excludes and not d.startswith('.')]
        
        for f in filenames:
            ext = os.path.splitext(f)[1].lower()
            if ext in media_extensions:
                found.append(os.path.join(dirpath, f))
                
    end = time.time()
    print(f"Found {len(found)} media files in {end - start:.2f} seconds.")
    for i, f in enumerate(found[:20]):
        print(f)
    if len(found) > 20:
        print("...")

if __name__ == "__main__":
    scan_media()
