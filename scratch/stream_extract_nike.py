import fitz
from rapidocr_onnxruntime import RapidOCR
import re
import os
import sqlite3
import time
from pathlib import Path
from multiprocessing import Pool, cpu_count

pdf_path = r"C:\AI-BS\FacebookData\20260803145022663 NIKE BOYS RECRUITING GUIDE.pdf"
db_path = r"C:\AI-BS\saved_data\rec_debut.db"

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

def init_tables():
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS rec_debut_athletes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            phone TEXT NOT NULL UNIQUE,
            email TEXT,
            sport TEXT DEFAULT 'Basketball',
            high_school TEXT,
            grad_year TEXT,
            city_state TEXT,
            status TEXT DEFAULT 'Pending',
            notes TEXT,
            team_name TEXT,
            created_at REAL,
            last_messaged_at REAL
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS rec_debut_excluded_coaches (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            phone TEXT NOT NULL,
            coach_type TEXT,
            team_name TEXT,
            school_name TEXT,
            page INTEGER,
            excluded_at REAL
        )
    """)
    try:
        cursor.execute("ALTER TABLE rec_debut_athletes ADD COLUMN team_name TEXT")
    except Exception:
        pass
    conn.commit()
    conn.close()

def parse_single_page(args):
    page_idx, pdf_path = args
    try:
        doc = fitz.open(pdf_path)
        page = doc[page_idx]
        pix = page.get_pixmap(dpi=120)
        img_bytes = pix.tobytes("png")
        engine = RapidOCR()
        result, _ = engine(img_bytes)
        if not result:
            return page_idx, "", [], []

        # Find team name & athlete header
        y_athlete_header = None
        team_name = ""
        for box, text, _ in result:
            y_min = min(pt[1] for pt in box)
            if "ATHLETE NAME" in text.upper():
                y_athlete_header = y_min
            if not team_name and y_min < 250 and len(text.strip()) > 3 and not any(kw in text.upper() for kw in ["SESSION", "JUL", "AUG", "NIKE", "BOYS"]):
                team_name = text.strip()

        coaches_excluded = []
        athlete_items = []

        for box, text, score in result:
            y_min = min(pt[1] for pt in box)
            x_min = min(pt[0] for pt in box)
            
            # Above athlete header is club coach info
            if y_athlete_header and y_min < y_athlete_header:
                m = phone_regex.search(text)
                if m:
                    coaches_excluded.append({
                        "name": "Club Coach",
                        "phone": clean_phone(m.group(1)),
                        "coach_type": "Club Coach",
                        "team_name": team_name,
                        "page": page_idx + 1
                    })
            elif y_athlete_header and y_min >= y_athlete_header:
                athlete_items.append({"box": box, "text": text, "y": y_min, "x": x_min, "score": score})

        # Group athlete items into rows by Y coordinate
        athlete_rows = {}
        for item in athlete_items:
            if abs(item["y"] - y_athlete_header) < 15:
                continue
            matched_y = None
            for ry in athlete_rows:
                if abs(item["y"] - ry) < 16:
                    matched_y = ry
                    break
            if matched_y is None:
                matched_y = item["y"]
                athlete_rows[matched_y] = []
            athlete_rows[matched_y].append(item)

        athletes = []
        for ry in sorted(athlete_rows.keys()):
            row = sorted(athlete_rows[ry], key=lambda x: x["x"])
            
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
                    if t.isdigit() and len(t) == 4:
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
                        coaches_excluded.append({
                            "name": hs_coach_name or "High School Coach",
                            "phone": hs_coach_phone,
                            "coach_type": "High School Coach",
                            "team_name": team_name,
                            "school_name": ath_school,
                            "page": page_idx + 1
                        })

            if ath_name and ath_phone:
                athletes.append({
                    "name": ath_name,
                    "phone": ath_phone,
                    "email": ath_email,
                    "year": ath_year or "2027",
                    "school": ath_school,
                    "team": team_name,
                    "page": page_idx + 1
                })

        return page_idx, team_name, athletes, coaches_excluded
    except Exception as e:
        return page_idx, "", [], []

if __name__ == "__main__":
    t0 = time.time()
    init_tables()
    doc = fitz.open(pdf_path)
    total_pages = len(doc)
    doc.close()

    print(f"Starting real-time streaming extraction across {total_pages} pages...", flush=True)
    pages_to_process = [(i, pdf_path) for i in range(1, total_pages)]
    num_workers = min(12, cpu_count())
    print(f"Active workers: {num_workers}", flush=True)

    conn = sqlite3.connect(db_path, timeout=30.0)
    cursor = conn.cursor()

    total_athletes_inserted = 0
    total_coaches_inserted = 0
    processed_count = 0
    known_coach_phones = set()

    with Pool(processes=num_workers) as pool:
        for p_idx, team, athletes, coaches in pool.imap_unordered(parse_single_page, pages_to_process, chunksize=2):
            now = time.time()
            
            # Save coaches
            for c in coaches:
                p = c.get("phone")
                if p:
                    known_coach_phones.add(p)
                    cursor.execute("""
                        INSERT INTO rec_debut_excluded_coaches (name, phone, coach_type, team_name, school_name, page, excluded_at)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                    """, (c.get("name"), p, c.get("coach_type"), c.get("team_name"), c.get("school_name", ""), c.get("page"), now))
                    total_coaches_inserted += 1

            # Save athletes (ONLY if phone not in coach set)
            for a in athletes:
                p = a.get("phone")
                if p and p not in known_coach_phones:
                    try:
                        cursor.execute("""
                            INSERT OR IGNORE INTO rec_debut_athletes
                            (name, phone, email, sport, high_school, grad_year, city_state, status, notes, team_name, created_at, last_messaged_at)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """, (
                            a["name"],
                            p,
                            a.get("email", ""),
                            "Basketball",
                            a.get("school", ""),
                            a.get("year", "2027"),
                            "National Recruit",
                            "Pending", # Uncontacted / Needs to be messaged
                            f"Page {a['page']} • {a.get('team', '')}",
                            a.get("team", ""),
                            now,
                            None
                        ))
                        if cursor.rowcount > 0:
                            total_athletes_inserted += 1
                    except Exception:
                        pass

            conn.commit()
            processed_count += 1
            if processed_count % 10 == 0 or processed_count == len(pages_to_process):
                print(f"[PROGRESS] {processed_count}/{len(pages_to_process)} pages | {total_athletes_inserted} Athletes Added | {total_coaches_inserted} Coaches Blocked", flush=True)

    conn.close()
    print(f"\nALL COMPLETED in {time.time() - t0:.2f}s! Total athletes: {total_athletes_inserted}, Total coaches blocked: {total_coaches_inserted}", flush=True)
