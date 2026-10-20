import os, json, csv

saved_data = r"C:\AI-BS\saved_data"
for fname in ["nike_guide_email_blast_staged.json", "rec_debut_athlete_emails_master.csv", "rec_debut_athlete_emails.json"]:
    fpath = os.path.join(saved_data, fname)
    if os.path.exists(fpath):
        size = os.path.getsize(fpath)
        print(f"{fname}: {size} bytes")
        if fname.endswith(".json"):
            with open(fpath, "r", encoding="utf-8") as f:
                try:
                    data = json.load(f)
                    if isinstance(data, list):
                        print(f"  JSON list length: {len(data)}, sample item: {list(data[0].keys()) if data else None}")
                    elif isinstance(data, dict):
                        print(f"  JSON dict keys: {list(data.keys())[:5]}")
                except Exception as e:
                    print(f"  JSON error: {e}")
        elif fname.endswith(".csv"):
            with open(fpath, "r", encoding="utf-8", errors="ignore") as f:
                reader = csv.reader(f)
                header = next(reader, None)
                rows = list(reader)
                print(f"  CSV header: {header}, rows: {len(rows)}")
