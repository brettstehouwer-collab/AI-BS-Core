import fitz
from rapidocr_onnxruntime import RapidOCR
import re
import os
import sqlite3
import time
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
        y_header = None
        x_header_coach_phone = None
        team_name = ""
        for box, text, _ in result:
            t = text.strip().upper()
            y = min(pt[1] for pt in box)
            x = min(pt[0] for pt in box)
            if "ATHLETE NAME" in t:
                y_header = y
            if "COACH PHONE" in t:
                x_header_coach_phone = x
            if not team_name and y < 250 and len(t) > 3 and not any(kw in t for kw in ["SESSION", "JUL", "AUG", "NIKE", "BOYS", "PAGE", "EXPOSURE"]):
                team_name = text.strip()

        if not y_header:
            return page_idx, team_name, [], []

        coaches_excluded = []
        athlete_items = []

        for box, text, score in result:
            y = min(pt[1] for pt in box)
            x = min(pt[0] for pt in box)
            t = text.strip()
            
            # Above athlete header is club coach info
            if y < y_header:
                m = phone_regex.search(t)
                if m:
                    coaches_excluded.append({
                        "name": "Club Coach",
                        "phone": clean_phone(m.group(1)),
                        "coach_type": "Club Coach",
                        "team_name": team_name,
                        "school_name": "",
                        "page": page_idx + 1
                    })
            elif y >= y_header:
                athlete_items.append({"box": box, "text": t, "x": x, "y": y})

        # Group athlete items into rows
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

        athletes = []
        for ry in sorted(rows.keys()):
            row_items = sorted(rows[ry], key=lambda x: x["x"])
            
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
                elif not t.isdigit() and len(t) > 1 and not any(kw in t.upper() for kw in ["HEIGHT", "YEAR", "NAME", "SCHOOL", "PHONE", "COACH"]):
                    if it["x"] < 250:
                        names_candidates.append(t)
                    else:
                        school_candidates.append(t)

            ath_name = " ".join(names_candidates).strip()
            school_name = " ".join(school_candidates).strip()
            ath_phone = ""
            coach_phone = ""

            if len(phones_in_row) == 2:
                ath_phone = phones_in_row[0][1]
                coach_phone = phones_in_row[1][1]
                coaches_excluded.append({
                    "name": "High School Coach",
                    "phone": coach_phone,
                    "coach_type": "High School Coach",
                    "team_name": team_name,
                    "school_name": school_name,
                    "page": page_idx + 1
                })
            elif len(phones_in_row) == 1:
                px, phone_val = phones_in_row[0]
                if x_header_coach_phone and px >= x_header_coach_phone - 50:
                    coach_phone = phone_val
                    coaches_excluded.append({
                        "name": "High School Coach",
                        "phone": coach_phone,
                        "coach_type": "High School Coach",
                        "team_name": team_name,
                        "school_name": school_name,
                        "page": page_idx + 1
                    })
                else:
                    ath_phone = phone_val

            if ath_name and ath_phone:
                athletes.append({
                    "name": ath_name,
                    "phone": ath_phone,
                    "email": email,
                    "year": year,
                    "school": school_name,
                    "team": team_name,
                    "page": page_idx + 1
                })

        return page_idx, team_name, athletes, coaches_excluded
    except Exception as e:
        return page_idx, "", [], []

if __name__ == "__main__":
    t0 = time.time()
    doc = fitz.open(pdf_path)
    total_pages = len(doc)
    doc.close()

    print(f"Starting master extraction across {total_pages} pages...", flush=True)
    pages_to_process = [(i, pdf_path) for i in range(1, total_pages)]
    num_workers = min(12, cpu_count())
    print(f"Workers: {num_workers}", flush=True)

    conn = sqlite3.connect(db_path, timeout=30.0)
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

    total_athletes = 0
    total_coaches = 0
    processed = 0
    now = time.time()

    with Pool(processes=num_workers) as pool:
        for p_idx, team, athletes, coaches in pool.imap_unordered(parse_single_page, pages_to_process, chunksize=2):
            # Save coaches
            for c in coaches:
                p = c.get("phone")
                if p:
                    cursor.execute("""
                        INSERT INTO rec_debut_excluded_coaches (name, phone, coach_type, team_name, school_name, page, excluded_at)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                    """, (c.get("name"), p, c.get("coach_type"), c.get("team_name"), c.get("school_name", ""), c.get("page"), now))
                    total_coaches += 1

            # Save athletes
            for a in athletes:
                p = a.get("phone")
                if p:
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
                            "Pending",
                            f"Page {a['page']} • {a.get('team', '')}",
                            a.get("team", ""),
                            now,
                            None
                        ))
                        if cursor.rowcount > 0:
                            total_athletes += 1
                    except Exception:
                        pass

            conn.commit()
            processed += 1
            if processed % 15 == 0 or processed == len(pages_to_process):
                print(f"[EXTRACT] {processed}/{len(pages_to_process)} pages | {total_athletes} Athletes Added | {total_coaches} Coaches Blocked", flush=True)

    # Final cleanup: Remove any athlete whose phone matches an excluded coach phone!
    cursor.execute("""
        DELETE FROM rec_debut_athletes 
        WHERE phone IN (SELECT phone FROM rec_debut_excluded_coaches)
    """)
    removed_coaches = cursor.rowcount
    if removed_coaches > 0:
        print(f"Purged {removed_coaches} coach numbers that matched athlete records!", flush=True)
    conn.commit()
    conn.close()

    print(f"\nFINISHED in {time.time() - t0:.2f}s! Total athletes in roster: {total_athletes}, Total coaches blocked: {total_coaches}", flush=True)
