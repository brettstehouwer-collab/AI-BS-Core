import zipfile
import os
from pathlib import Path

ZIPS = [r"F:\GTake1.zip", r"F:\GTake2.zip"]
DEST_DIR = Path(r"c:\Users\footb\AI-BS_Matrix\sandbox_scratch\takeout_extract")
ALLOWED_EXTENSIONS = {'.json', '.jsonl', '.csv', '.md', '.txt', '.html'}


def main():
    DEST_DIR.mkdir(parents=True, exist_ok=True)

    for zip_path in ZIPS:
        if not os.path.exists(zip_path):
            print(f"Zip file not found: {zip_path}")
            continue

        print(f"Extracting supported text files from {zip_path}...")
        try:
            with zipfile.ZipFile(zip_path, 'r') as zf:
                for file_info in zf.infolist():
                    # Skip directories
                    if file_info.is_dir():
                        continue

                    # Filter by extension
                    ext = os.path.splitext(file_info.filename)[1].lower()
                    if ext in ALLOWED_EXTENSIONS:
                        zf.extract(file_info, DEST_DIR)
                        print(f"  Extracted: {file_info.filename}")
        except Exception as e:
            print(f"Failed to extract {zip_path}: {e}")

    print(f"\nExtraction complete. Files saved to {DEST_DIR}")


if __name__ == "__main__":
    main()
