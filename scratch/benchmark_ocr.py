import fitz
from rapidocr_onnxruntime import RapidOCR
import time

engine = RapidOCR()
pdf_path = r"C:\AI-BS\FacebookData\20260803145022663 NIKE BOYS RECRUITING GUIDE.pdf"
doc = fitz.open(pdf_path)

t0 = time.time()
pages_to_test = 5
for idx in range(1, 1 + pages_to_test):
    page = doc[idx]
    pix = page.get_pixmap(dpi=120) # 120 DPI is very fast and plenty sharp for OCR
    img_bytes = pix.tobytes("png")
    res, _ = engine(img_bytes)
    print(f"Page {idx+1}: {len(res) if res else 0} elements")

elapsed = time.time() - t0
print(f"Total for {pages_to_test} pages: {elapsed:.2f}s ({elapsed/pages_to_test:.2f}s per page)")
