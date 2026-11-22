import fitz # PyMuPDF
import re

pdf_path = r"C:\AI-BS\FacebookData\20260803145022663 NIKE BOYS RECRUITING GUIDE.pdf"
doc = fitz.open(pdf_path)

print(f"Total pages: {len(doc)}")

# Look at metadata
print("Metadata:", doc.metadata)

# Sample first 5 pages and some middle pages
for page_num in range(min(5, len(doc))):
    text = doc[page_num].get_text()
    print(f"\n--- PAGE {page_num + 1} (Length: {len(text)} chars) ---")
    print(text[:800])
