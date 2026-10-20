import json
from pathlib import Path

data_path = Path(r"C:\Recreational-Debut\data\recdebut_extracted_summary.json")
out_path = Path(r"C:\Recreational-Debut\frontend\src\recdebutData.js")

if data_path.exists():
    with open(data_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    content = data.get("https://recdebut.com/", {}).get("content", "")
    entries = []
    lines = content.split("\n")
    current = {}
    for line in lines:
        if line.startswith("Name:"):
            if current.get("name"):
                entries.append(current)
            current = {"name": line.replace("Name:", "").strip()}
        elif line.startswith("High :") and current:
            current["height"] = line.replace("High :", "").strip()
        elif line.startswith("School :") and current:
            current["school"] = line.replace("School :", "").strip()
        elif line.startswith("City and State:") and current:
            current["city_state"] = line.replace("City and State:", "").strip()
        elif line.startswith("Coach :") and current:
            current["coach"] = line.replace("Coach :", "").strip()
        elif line.startswith("Awards:") and current:
            current["awards"] = line.replace("Awards:", "").strip()
    if current.get("name"):
        entries.append(current)

    with open(out_path, "w", encoding="utf-8") as out:
        out.write("// Offline Athletes Data for Recreational Debut\n")
        out.write("export const RECENT_ATHLETES = " + json.dumps(entries, indent=2) + ";\n")
    print(f"Generated {len(entries)} athletes in {out_path}")
else:
    print("Data path not found.")
