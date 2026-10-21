import csv
import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

paths = [
    Path(r"C:\Users\footb\OneDrive\Desktop\TextBee_RecDebut_Class_of_2027.csv"),
    Path(r"C:\Users\footb\OneDrive\Desktop\TextBee_RecDebut_Smart_Personalization_Part1_of_4.csv")
]

for p in paths:
    print(f"\n==================================================")
    print(f"FILE: {p.name}")
    print(f"==================================================")
    if not p.exists():
        print("Does not exist!")
        continue
    with open(p, "r", encoding="utf-8", errors="ignore") as f:
        reader = csv.DictReader(f)
        for i, row in enumerate(reader):
            if i >= 3:
                break
            print(f"Row {i}: id={row.get('athlete_id')} name={row.get('name')} phone={row.get('phone')}")
            print(f"  message: {row.get('message')}")
