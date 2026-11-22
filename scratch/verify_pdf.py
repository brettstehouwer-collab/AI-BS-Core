import fitz

p = r'C:\AI-BS\Documents\Stehouwer_Publishing_Robert_Costner_Master_NDA_Agreement.pdf'
doc = fitz.open(p)
print(f"Total Pages: {len(doc)}")
for i, page in enumerate(doc):
    txt = page.get_text()
    first_line = txt.split('\n')[0] if txt else ''
    print(f"Page {i+1}: {len(txt)} chars | Starts with: {first_line[:50]}")
