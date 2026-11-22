import zipfile
import xml.etree.ElementTree as ET
import glob
import os

folder = r"C:\AI-BS\docs\drive-download-20260820T180814Z-1-001"
docx_files = glob.glob(os.path.join(folder, "*.docx"))

for filepath in docx_files:
    print("=" * 80)
    print("FILE:", os.path.basename(filepath))
    print("=" * 80)
    try:
        with zipfile.ZipFile(filepath, 'r') as z:
            xml_content = z.read('word/document.xml')
            root = ET.fromstring(xml_content)
            # Find all paragraph elements (w:p)
            paragraphs = []
            for p in root.iter():
                if p.tag.endswith('p'):
                    texts = [node.text for node in p.iter() if node.tag.endswith('t') and node.text]
                    if texts:
                        paragraphs.append("".join(texts))
            print("\n".join(paragraphs))
    except Exception as e:
        print("ERROR:", e)
    print("\n\n")
