import fitz
import os

pdf_path = r'C:\AI-BS\Documents\Stehouwer_Publishing_Robert_Costner_Master_NDA_Agreement.pdf'
doc = fitz.open(pdf_path)

# Render Page 1
page1 = doc[0]
pix1 = page1.get_pixmap(dpi=150)
p1_img = r'C:\AI-BS\Documents\nda_page_1_preview.png'
pix1.save(p1_img)

# Render Page 6 (Signatures)
page6 = doc[5]
pix6 = page6.get_pixmap(dpi=150)
p6_img = r'C:\AI-BS\Documents\nda_page_6_preview.png'
pix6.save(p6_img)

print("Saved preview images:")
print(f"Page 1: {p1_img}")
print(f"Page 6: {p6_img}")
