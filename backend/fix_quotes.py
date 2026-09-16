import os

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
files = [
    os.path.join(BASE_DIR, "frontend", "src", "App.jsx"),
    os.path.join(BASE_DIR, "frontend", "src", "BullshitTelemetrySuite.jsx"),
    os.path.join(BASE_DIR, "frontend", "src", "BullshitKnowledgeSuite.jsx"),
]


for f in files:
    with open(f, "r", encoding="utf-8") as file:
        content = file.read()

    # Fix the trailing double quote issue caused by previous partial string
    # replacements
    content = re.sub(
        r'(`http://\$\{window\.location\.hostname\}:8000/[^`"]*)"', r"\1`", content
    )

    with open(f, "w", encoding="utf-8") as file:
        file.write(content)
