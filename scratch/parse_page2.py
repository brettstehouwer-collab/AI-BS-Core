from rapidocr_onnxruntime import RapidOCR
import json

engine = RapidOCR()
result, _ = engine(r"C:\AI-BS\scratch\ocr_test\page_2.png")

print(f"=== FULL OCR ON PAGE 2 ({len(result)} elements) ===")
# Each element is [box, text, score]
for box, text, score in result:
    print(f"[{score:.2f}] {text}")
