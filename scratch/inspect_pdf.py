import os
import sys

pdf_path = r"C:\AI-BS\FacebookData\20260803145022663 NIKE BOYS RECRUITING GUIDE.pdf"
print("File exists:", os.path.exists(pdf_path))
if os.path.exists(pdf_path):
    print("File size:", os.path.getsize(pdf_path), "bytes")

# Check available PDF libraries
for lib in ["pypdf", "pypdf2", "pdfplumber", "fitz", "pdfminer"]:
    try:
        __import__(lib)
        print(f"Library {lib}: AVAILABLE")
    except ImportError:
        print(f"Library {lib}: not installed")
