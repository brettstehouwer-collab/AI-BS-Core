import os
import shutil

print("Checking OCR engines...")
# 1. Tesseract CLI
tesseract_bin = shutil.which("tesseract")
print("tesseract on PATH:", tesseract_bin)
common_tess = [
    r"C:\Program Files\Tesseract-OCR\tesseract.exe",
    r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
    os.path.expanduser(r"~\AppData\Local\Programs\Tesseract-OCR\tesseract.exe")
]
for p in common_tess:
    if os.path.exists(p):
        print(f"Found tesseract at: {p}")

# 2. Python packages
for pkg in ["pytesseract", "easyocr", "rapidocr_onnxruntime", "paddleocr", "PIL", "cv2"]:
    try:
        __import__(pkg)
        print(f"Python package {pkg}: AVAILABLE")
    except ImportError:
        print(f"Python package {pkg}: not installed")

# 3. Windows Media OCR check
try:
    import winrt
    print("winrt: AVAILABLE")
except ImportError:
    print("winrt: not installed")

try:
    import winsdk
    print("winsdk: AVAILABLE")
except ImportError:
    print("winsdk: not installed")
