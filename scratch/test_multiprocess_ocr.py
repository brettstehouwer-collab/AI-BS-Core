import fitz
from rapidocr_onnxruntime import RapidOCR
from multiprocessing import Pool
import time

def process_page(args):
    page_idx, pdf_path = args
    doc = fitz.open(pdf_path)
    page = doc[page_idx]
    pix = page.get_pixmap(dpi=120)
    img_bytes = pix.tobytes("png")
    engine = RapidOCR()
    res, _ = engine(img_bytes)
    return page_idx, len(res) if res else 0

if __name__ == "__main__":
    pdf_path = r"C:\AI-BS\FacebookData\20260803145022663 NIKE BOYS RECRUITING GUIDE.pdf"
    pages_to_test = [(i, pdf_path) for i in range(1, 11)]
    t0 = time.time()
    with Pool(processes=8) as pool:
        results = pool.map(process_page, pages_to_test)
    elapsed = time.time() - t0
    print(f"Processed {len(results)} pages in {elapsed:.2f}s ({elapsed/len(results):.2f}s per page with 8 workers)")
    for p, c in sorted(results):
        print(f"  Page {p+1}: {c} elements")
