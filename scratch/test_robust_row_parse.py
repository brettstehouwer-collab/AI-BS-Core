import fitz
from rapidocr_onnxruntime import RapidOCR
import re

pdf_path = r"C:\AI-BS\FacebookData\20260803145022663 NIKE BOYS RECRUITING GUIDE.pdf"
doc = fitz.open(pdf_path)

phone_regex = re.compile(r'(\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4})')

def clean_phone(p):
    if not p:
        return ""
    digits = re.sub(r'\D', '', str(p))
    if len(digits) == 10:
        return f"{digits[:3]}-{digits[3:6]}-{digits[6:]}"
    elif len(digits) == 11 and digits.startswith('1'):
        return f"{digits[1:4]}-{digits[4:7]}-{digits[7:]}"
    return p.strip()

for page_idx in [1, 2]: # page 2, 3
    page = doc[page_idx]
    pix = page.get_pixmap(dpi=120)
    img_bytes = pix.tobytes("png")
    engine = RapidOCR()
    result, _ = engine(img_bytes)
    
    # 1. Find athlete header Y
    y_header = None
    x_header_phone = None
    x_header_coach_phone = None
    for box, text, _ in result:
        t = text.strip().upper()
        y = min(pt[1] for pt in box)
        x = min(pt[0] for pt in box)
        if "ATHLETE NAME" in t:
            y_header = y
        if "COACH PHONE" in t:
            x_header_coach_phone = x
        elif "PHONE" in t and "COACH" not in t:
            x_header_phone = x

    print(f"\nPAGE {page_idx+1}: y_header={y_header}, x_phone={x_header_phone}, x_coach_phone={x_header_coach_phone}")

    # Separate items above and below header
    coaches_excluded = []
    athlete_items = []
    for box, text, score in result:
        y = min(pt[1] for pt in box)
        x = min(pt[0] for pt in box)
        if y_header and y < y_header:
            m = phone_regex.search(text)
            if m:
                coaches_excluded.append(clean_phone(m.group(1)))
        elif y_header and y >= y_header:
            athlete_items.append({"box": box, "text": text.strip(), "x": x, "y": y})

    # Group into rows
    rows = {}
    for it in athlete_items:
        if abs(it["y"] - y_header) < 15:
            continue
        matched_y = None
        for ry in rows:
            if abs(it["y"] - ry) < 14:
                matched_y = ry
                break
        if matched_y is None:
            matched_y = it["y"]
            rows[matched_y] = []
        rows[matched_y].append(it)

    print(f"Total athlete rows: {len(rows)}")
    for ry in sorted(rows.keys()):
        row_items = sorted(rows[ry], key=lambda x: x["x"])
        
        # Extract phones in this row
        phones_in_row = []
        names_candidates = []
        school_candidates = []
        email = ""
        year = "2027"

        for it in row_items:
            t = it["text"]
            m = phone_regex.search(t)
            if m:
                phones_in_row.append((it["x"], clean_phone(m.group(1))))
            elif "@" in t:
                email = t
            elif t.isdigit() and len(t) == 4 and t.startswith("20"):
                year = t
            elif not t.isdigit() and len(t) > 2 and not any(kw in t.upper() for kw in ["HEIGHT", "YEAR", "NAME", "SCHOOL", "PHONE", "COACH"]):
                if it["x"] < 250:
                    names_candidates.append(t)
                else:
                    school_candidates.append(t)

        ath_name = " ".join(names_candidates)
        ath_phone = ""
        coach_phone = ""

        if len(phones_in_row) == 2:
            # First is athlete, second is coach!
            ath_phone = phones_in_row[0][1]
            coach_phone = phones_in_row[1][1]
            coaches_excluded.append(coach_phone)
        elif len(phones_in_row) == 1:
            px, phone_val = phones_in_row[0]
            # Check if closer to athlete phone header or coach phone header
            if x_header_coach_phone and px >= x_header_coach_phone - 50:
                coach_phone = phone_val
                coaches_excluded.append(coach_phone)
            else:
                ath_phone = phone_val

        print(f"Row y={ry:.0f}: Athlete='{ath_name}' | AthPhone='{ath_phone}' | CoachPhone='{coach_phone}' | Yr={year}")
