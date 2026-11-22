import fitz
from rapidocr_onnxruntime import RapidOCR

pdf_path = r"C:\AI-BS\FacebookData\20260803145022663 NIKE BOYS RECRUITING GUIDE.pdf"
doc = fitz.open(pdf_path)
engine = RapidOCR()

for page_idx in [70, 76, 124]: # pages 71, 77, 125 (0-indexed)
    page = doc[page_idx]
    pix = page.get_pixmap(dpi=120)
    img_bytes = pix.tobytes("png")
    result, _ = engine(img_bytes)
    print(f"\n================ PAGE {page_idx + 1} ================")
    if result:
        sorted_items = sorted(result, key=lambda x: (min(pt[1] for pt in x[0]), min(pt[0] for pt in x[0])))
        for box, text, score in sorted_items:
            y = int(min(pt[1] for pt in box))
            x = int(min(pt[0] for pt in box))
            if any(k in text.upper() for k in ["WOODARD", "LEWIS", "LANDRY", "SAM", "WYNN", "COACH", "SCHOOL", "MORIN", "ANDRADE", "GRAVES"]):
                print(f"y={y:3d}, x={x:3d}: {text}")

doc.close()
