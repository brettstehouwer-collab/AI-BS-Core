import fitz

pdf_path = r"C:\Users\footb\Desktop\book site\Echos Within.pdf"
doc = fitz.open(pdf_path)
full_text = ""
for page in doc:
    full_text += page.get_text()
doc.close()

print(f"Total characters: {len(full_text)}")
print(f"Chunks split by \\n\\n: {len(full_text.split('\n\n'))}")
print(f"Chunks split by \\n: {len(full_text.split('\n'))}")
