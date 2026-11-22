from rapidocr_onnxruntime import RapidOCR
import json

engine = RapidOCR()
result, _ = engine(r"C:\AI-BS\scratch\ocr_test\page_2.png")

print("=== BOX COORDINATES AND TEXT FOR PAGE 2 ===")
for box, text, score in result:
    # box is [[x1,y1], [x2,y2], [x3,y3], [x4,y4]]
    y_min = min(pt[1] for pt in box)
    x_min = min(pt[0] for pt in box)
    print(f"y={y_min:6.1f}, x={x_min:6.1f} | [{score:.2f}] {text}")
