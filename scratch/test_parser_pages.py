import fitz
from rapidocr_onnxruntime import RapidOCR
import re

engine = RapidOCR()
pdf_path = r"C:\AI-BS\FacebookData\20260803145022663 NIKE BOYS RECRUITING GUIDE.pdf"
doc = fitz.open(pdf_path)

phone_regex = re.compile(r'(\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4})')

def clean_phone(p):
    digits = re.sub(r'\D', '', p)
    if len(digits) == 10:
        return f"{digits[:3]}-{digits[3:6]}-{digits[6:]}"
    elif len(digits) == 11 and digits.startswith('1'):
        return f"{digits[1:4]}-{digits[4:7]}-{digits[7:]}"
    return p

for page_idx in [1, 2, 3, 4]: # 0-indexed: page 2, 3, 4, 5
    page = doc[page_idx]
    pix = page.get_pixmap(dpi=150)
    img_bytes = pix.tobytes("png")
    
    result, _ = engine(img_bytes)
    if not result:
        print(f"Page {page_idx+1}: No text")
        continue

    # Find athlete header Y position
    y_athlete_header = None
    team_name = ""
    for box, text, _ in result:
        y_min = min(pt[1] for pt in box)
        if "ATHLETE NAME" in text.upper():
            y_athlete_header = y_min
        if not team_name and y_min < 250 and ("ELITE" in text.upper() or "FUSION" in text.upper() or "15U" in text.upper() or "16U" in text.upper() or "17U" in text.upper()):
            team_name = text.strip()

    athletes_found = []
    coaches_excluded = []

    # Group elements into rows below athlete header
    athlete_items = []
    coach_items = []
    for box, text, score in result:
        y_min = min(pt[1] for pt in box)
        x_min = min(pt[0] for pt in box)
        
        # If above athlete header, it's a team/club coach!
        if y_athlete_header and y_min < y_athlete_header:
            m = phone_regex.search(text)
            if m:
                coaches_excluded.append({"type": "Club Coach", "phone": clean_phone(m.group(1)), "raw": text, "y": y_min, "x": x_min})
        elif y_athlete_header and y_min >= y_athlete_header:
            athlete_items.append({"box": box, "text": text, "y": y_min, "x": x_min, "score": score})

    # Group athlete items by Y coordinate (within 15px)
    athlete_rows = {}
    for item in athlete_items:
        # Skip the header row itself
        if abs(item["y"] - y_athlete_header) < 15:
            continue
        # Find matching row cluster
        matched_y = None
        for ry in athlete_rows:
            if abs(item["y"] - ry) < 16:
                matched_y = ry
                break
        if matched_y is None:
            matched_y = item["y"]
            athlete_rows[matched_y] = []
        athlete_rows[matched_y].append(item)

    print(f"\n================ PAGE {page_idx+1}: {team_name} ================")
    print(f"Club Coaches Excluded: {len(coaches_excluded)}")
    for c in coaches_excluded:
        print(f"   [EXCLUDED COACH] {c['phone']} (x={c['x']:.0f}, y={c['y']:.0f})")

    # Now parse each athlete row
    for ry in sorted(athlete_rows.keys()):
        row = sorted(athlete_rows[ry], key=lambda x: x["x"])
        # Columns:
        # x < 250: Name
        # x 250-320: Year
        # x 320-400: Height
        # x 400-530: ATHLETE PHONE
        # x 530-850: Email
        # x 850-1200: School
        # x 1200-1430: High School Coach Name
        # x >= 1430: High School COACH PHONE
        
        ath_name = ""
        ath_year = ""
        ath_phone = ""
        ath_email = ""
        ath_school = ""
        hs_coach_name = ""
        hs_coach_phone = ""

        for item in row:
            x = item["x"]
            t = item["text"].strip()
            if x < 260:
                if not t.isdigit() and len(t) > 2:
                    ath_name = t if not ath_name else f"{ath_name} {t}"
            elif 260 <= x < 330:
                ath_year = t
            elif 400 <= x < 540:
                m = phone_regex.search(t)
                if m:
                    ath_phone = clean_phone(m.group(1))
            elif 540 <= x < 850:
                if "@" in t:
                    ath_email = t
            elif 850 <= x < 1220:
                ath_school = t if not ath_school else f"{ath_school} {t}"
            elif 1220 <= x < 1440:
                hs_coach_name = t
            elif x >= 1440:
                m = phone_regex.search(t)
                if m:
                    hs_coach_phone = clean_phone(m.group(1))
                    coaches_excluded.append({"type": "HS Coach", "phone": hs_coach_phone, "name": hs_coach_name})

        if ath_name and (ath_phone or ath_email):
            athletes_found.append({
                "name": ath_name,
                "phone": ath_phone,
                "email": ath_email,
                "year": ath_year,
                "school": ath_school,
                "hs_coach": hs_coach_name,
                "hs_coach_phone": hs_coach_phone
            })

    print(f"Athletes Extracted: {len(athletes_found)}")
    for a in athletes_found[:5]:
        print(f"   [ATHLETE] {a['name']:<22} | Phone: {a['phone']:<14} | Year: {a['year']} | School: {a['school']}")
        if a['hs_coach_phone']:
            print(f"      -> Excluded HS Coach: {a['hs_coach']} ({a['hs_coach_phone']})")
