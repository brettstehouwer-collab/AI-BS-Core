import fitz

pdf_path = r"C:\AI-BS\FacebookData\20260803145022663 NIKE BOYS RECRUITING GUIDE.pdf"
doc = fitz.open(pdf_path)

print(f"Total pages in PDF: {len(doc)}")

for page_num in [24, 61, 77, 125]:
    if page_num <= len(doc):
        p = doc[page_num - 1] # 0-indexed
        text = p.get_text("text")
        print(f"\n================ PAGE {page_num} ================")
        print(text[:2500])

doc.close()
