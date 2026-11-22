import fitz
from rapidocr_onnxruntime import RapidOCR
import re

pdf_path = r"C:\AI-BS\FacebookData\20260803145022663 NIKE BOYS RECRUITING GUIDE.pdf"
doc = fitz.open(pdf_path)
page = doc[1] # page 2
pix = page.get_pixmap(dpi=150)
img_bytes = pix.tobytes("png")
engine = RapidOCR()
result, _ = engine(img_bytes)

# Find column headers
headers = {}
for box, text, _ in result:
    t = text.strip().upper()
    x = min(pt[0] for pt in box)
    y = min(pt[1] for pt in box)
    if any(h in t for h in ["ATHLETE NAME", "YEAR", "HEIGHT", "PHONE", "EMAIL", "SCHOOL", "COACH"]):
        print(f"HEADER: '{text}' at x={x:.1f}, y={y:.1f}")
