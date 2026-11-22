from rapidocr_onnxruntime import RapidOCR
import os

engine = RapidOCR()

for i in range(1, 6):
    img_path = f"C:\\AI-BS\\scratch\\ocr_test\\page_{i}.png"
    if os.path.exists(img_path):
        print(f"\n================ PAGE {i} ================")
        result, elapse_list = engine(img_path)
        if result:
            lines = [line[1] for line in result]
            print(f"Total lines detected: {len(lines)}")
            print("\n".join(lines[:30]))
            if len(lines) > 30:
                print(f"... and {len(lines)-30} more lines")
        else:
            print("No text detected.")
