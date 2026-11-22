import os
import shutil

src = r"C:\AI-BS\docs\Officeal start of_ The Bad Side Upside Down Writen By_ Julie Stehouwer 2525 (2).md"
dest_dir = r"C:\AI-BS\screenplay_projects\The_Bad_Side_Upside_Down"
os.makedirs(dest_dir, exist_ok=True)

dest_md = os.path.join(dest_dir, "the_bad_side_upside_down.md")
shutil.copyfile(src, dest_md)

with open(src, "r", encoding="utf-8") as f:
    content = f.read()

fountain_lines = [
    "Title: THE BAD SIDE UPSIDE DOWN",
    "Credit: Written by",
    "Author: Julie Stehouwer",
    "Property of: Stehouwer Publishing L.L.C",
    "Draft date: 2023 / 2026",
    "===",
    ""
]

for line in content.splitlines():
    stripped = line.strip()
    if stripped.startswith("**EXT.") or stripped.startswith("EXT."):
        fountain_lines.append("")
        fountain_lines.append(stripped.replace("**", ""))
        fountain_lines.append("")
    elif stripped.isupper() and len(stripped) < 30 and not stripped.startswith("("):
        fountain_lines.append("")
        fountain_lines.append(stripped)
    elif stripped:
        fountain_lines.append(stripped)

dest_fountain = os.path.join(dest_dir, "the_bad_side_upside_down.fountain")
with open(dest_fountain, "w", encoding="utf-8") as f:
    f.write("\n".join(fountain_lines))

print("Scaffolded successfully.")
print("MD:", dest_md, os.path.exists(dest_md))
print("Fountain:", dest_fountain, os.path.exists(dest_fountain))
