import fitz

pdf_path = r"C:\AI-BS\FacebookData\20260803145022663 NIKE BOYS RECRUITING GUIDE.pdf"
doc = fitz.open(pdf_path)

text_pages = []
image_counts = []

for i, page in enumerate(doc):
    txt = page.get_text().strip()
    imgs = page.get_images()
    if txt:
        text_pages.append((i+1, len(txt)))
    if imgs:
        image_counts.append((i+1, len(imgs)))

print(f"Total pages: {len(doc)}")
print(f"Pages with selectable text: {len(text_pages)}")
if text_pages:
    print("First 5 pages with text:", text_pages[:5])
print(f"Pages with images: {len(image_counts)}")
if image_counts:
    print("First 5 pages with images:", image_counts[:5])
