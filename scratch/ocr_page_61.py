import fitz
from rapidocr_onnxruntime import RapidOCR

pdf_path = r"C:\AI-BS\FacebookData\20260803145022663 NIKE BOYS RECRUITING GUIDE.pdf"
doc = fitz.open(pdf_path)

page = doc[60] # Page 61 (0-indexed 60)
pix = page.get_pixmap(dpi=120)
img_bytes = pix.tobytes("png")
engine = RapidOCR()
result, _ = engine(img_bytes)

print(f"Total OCR boxes found on Page 61: {len(result) if result else 0}")
if result:
    # Sort boxes top to bottom, left to right
    sorted_items = sorted(result, key=lambda x: (min(pt[1] for pt in x[0]), min(pt[0] for pt in x[0])))
    for box, text, score in sorted_items:
        y = int(min(pt[1] for pt in box))
        x = int(min(pt[0] for pt in box))
        print(f"y={y:3d}, x={x:3d}: {text}")

doc.close()
