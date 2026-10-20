"""
Showcase & Tournament Roster Extractor for Recreational Debut
Parses publicly available camp booklets, tournament schedules, and exposure event rosters
for student-athletes actively seeking college coach evaluation (Classes of 2026-2030).
"""

import re
import csv
import json
import sys
import urllib.request
from pathlib import Path
from typing import List, Dict, Any

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

BASE_DIR = Path(__file__).resolve().parent.parent
SAVED_DATA = BASE_DIR / "saved_data"

def extract_roster_from_text(raw_text: str, event_source: str = "Exposure Showcase") -> List[Dict[str, Any]]:
    """
    Parses messy copy-pasted or exported text from tournament packets,
    Pangos camp sheets, ExposureEvents team pages, or MaxPreps rosters.
    Extracts Name, Jersey #, Grad Year, Height, Position, High School, and City/State.
    """
    prospects = []
    lines = [l.strip() for l in raw_text.split("\n") if l.strip()]
    
    # Common grad year pattern: 2026, 2027, 2028, 2029, 2030, '26, '27, '28, '29, '30
    grad_pattern = re.compile(r'\b(202[5-9]|203[0-2]|\'[23][0-9])\b')
    # Height pattern: 6'4, 6-4, 5'11, 6'10"
    height_pattern = re.compile(r'\b([5-7][\'\-]?[0-1]?[0-9]\"?)\b')
    # Position pattern: PG, SG, SF, PF, C, G, F, Guard, Forward, Center
    pos_pattern = re.compile(r'\b(PG|SG|SF|PF|CG|G|F|C|Guard|Forward|Center)\b', re.IGNORECASE)

    for line in lines:
        if any(header in line.lower() for header in ["jersey", "roster", "player name", "grad year", "height"]):
            continue
            
        grad_match = grad_pattern.search(line)
        height_match = height_pattern.search(line)
        pos_match = pos_pattern.search(line)
        
        grad_year = ""
        if grad_match:
            gy = grad_match.group(1).replace("'", "")
            grad_year = f"20{gy}" if len(gy) == 2 else gy
            
        height = height_match.group(1) if height_match else ""
        position = pos_match.group(1).upper() if pos_match else "G/F"
        
        # Clean line to isolate name
        tokens = line.split()
        if len(tokens) >= 2:
            # Check for leading jersey number
            if tokens[0].isdigit():
                tokens = tokens[1:]
            
            # Simple heuristic: first two capital words are typically First and Last Name
            name_parts = []
            for t in tokens:
                clean_t = re.sub(r'[^a-zA-Z\-\']', '', t)
                if clean_t and not grad_pattern.match(t) and not height_pattern.match(t) and not pos_pattern.match(t):
                    name_parts.append(clean_t)
                if len(name_parts) == 2:
                    break
                    
            if len(name_parts) >= 2:
                full_name = " ".join(name_parts).upper()
                prospects.append({
                    "name": full_name,
                    "sport": "Basketball",
                    "grad_year": grad_year or "2027",
                    "position": position,
                    "height": height,
                    "high_school": "",
                    "city_state": "",
                    "notes": f"Scouted from {event_source} (Seeking College Recruitment)",
                    "status": "Pending"
                })
                
    return prospects

def save_prospects_to_csv(prospects: List[Dict[str, Any]], filename: str = "new_scouted_prospects.csv") -> Path:
    """Saves parsed prospects to saved_data/ ready for 1-click import into rec_debut.db."""
    SAVED_DATA.mkdir(parents=True, exist_ok=True)
    out_path = SAVED_DATA / filename
    
    fieldnames = ["name", "sport", "grad_year", "position", "height", "high_school", "city_state", "notes", "status"]
    with open(out_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for p in prospects:
            writer.writerow({k: p.get(k, "") for k in fieldnames})
            
    print(f"✅ Successfully wrote {len(prospects)} prospects to {out_path}")
    return out_path

if __name__ == "__main__":
    sample_raw = """
    #12 Jalen Green 6'3 SG 2027 Prolific Prep
    #4  Marcus Miller 6'7 PF 2028 Detroit Renaissance
    #21 David Carter 6'1 PG 2029 Midwest Hoops
    #33 Amare Thomas 6'8 C 2027 East Kentwood
    """
    parsed = extract_roster_from_text(sample_raw, "Pangos Frosh/Soph Camp")
    save_prospects_to_csv(parsed, "sample_scouted_roster.csv")
