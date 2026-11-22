import os, glob
import subprocess
import sys

try:
    import docx
except ImportError:
    subprocess.check_call([sys.executable, "-m", "pip", "install", "python-docx"])
    import docx

folder = r'C:\Users\footb\AI-BS\zmomreasarch\ActionGlass'
for file in glob.glob(os.path.join(folder, '*.docx')):
    try:
        doc = docx.Document(file)
        text = '\n'.join([p.text for p in doc.paragraphs if p.text.strip()])
        print(f'\n--- {os.path.basename(file)} ---')
        print(text[:1500] + ('...' if len(text) > 1500 else ''))
    except Exception as e:
        print(f'Error reading {os.path.basename(file)}: {e}')
