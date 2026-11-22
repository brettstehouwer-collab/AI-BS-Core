import os
import shutil
import json

SOURCE_DIR = "E:\\AI_BS_Resources\\Unreal_Scripts"
DEST_DIR = "C:\\AI-BS\\UnrealHub\\Assets"
INDEX_FILE = "C:\\AI-BS\\UnrealHub\\asset_index.json"

def populate_unreal_assets():
    print(f"Scanning Unreal Assets in {SOURCE_DIR}...")
    
    os.makedirs(DEST_DIR, exist_ok=True)
    
    asset_index = []
    
    if not os.path.exists(SOURCE_DIR):
        print(f"Error: {SOURCE_DIR} does not exist. Cannot populate assets.")
        return
        
    for root, dirs, files in os.walk(SOURCE_DIR):
        for file in files:
            source_path = os.path.join(root, file)
            # Create a relative path structure to maintain organization
            rel_path = os.path.relpath(source_path, SOURCE_DIR)
            dest_path = os.path.join(DEST_DIR, rel_path)
            
            # Ensure destination subdirectory exists
            os.makedirs(os.path.dirname(dest_path), exist_ok=True)
            
            # Copy or symlink (we will copy for safety on Windows, unless large)
            try:
                if not os.path.exists(dest_path):
                    shutil.copy2(source_path, dest_path)
                    print(f"Copied: {rel_path}")
                
                asset_index.append({
                    "name": file,
                    "category": rel_path.split("\\")[0] if "\\" in rel_path else "Root",
                    "path": dest_path,
                    "source_path": source_path
                })
            except Exception as e:
                print(f"Failed to process {file}: {e}")

    # Write the asset index for the Unreal Bridge
    with open(INDEX_FILE, "w", encoding="utf-8") as f:
        json.dump(asset_index, f, indent=4)
        
    print(f"Successfully populated {len(asset_index)} Unreal assets into {DEST_DIR}")
    print(f"Asset index written to {INDEX_FILE}")

if __name__ == "__main__":
    populate_unreal_assets()
