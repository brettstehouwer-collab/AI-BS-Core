import fitz
import os

pdf_path = r"C:\AI-BS\FacebookData\20260803145022663 NIKE BOYS RECRUITING GUIDE.pdf"
doc = fitz.open(pdf_path)

out_dir = r"C:\AI-BS\scratch\ocr_test"
os.makedirs(out_dir, exist_ok=True)

for p_num in range(min(5, len(doc))):
    page = doc[p_num]
    pix = page.get_pixmap(dpi=150)
    img_path = os.path.join(out_dir, f"page_{p_num+1}.png")
    pix.save(img_path)
    print(f"Rendered page {p_num+1} -> {img_path} ({pix.width}x{pix.height})")
