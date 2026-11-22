import fitz
import sys
sys.path.insert(0, r"C:\AI-BS\scratch")
from stream_extract_nike import parse_single_page, pdf_path

p_idx, team, athletes, coaches = parse_single_page((1, pdf_path))
print("Page 2 results:")
print(f"Team: {team}")
print(f"Athletes ({len(athletes)}):")
for a in athletes:
    print(" ", a)
print(f"Coaches ({len(coaches)}):")
for c in coaches:
    print(" ", c)
