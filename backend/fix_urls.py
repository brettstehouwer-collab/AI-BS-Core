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

    # Simple replacement of "http://127.0.0.1:8000" with
    # `http://${window.location.hostname}:8000`
    content = content.replace(
        '"http://127.0.0.1:8000"', "`http://${window.location.hostname}:8000`"
    )
    content = content.replace(
        '"http://127.0.0.1:8000/', "`http://${window.location.hostname}:8000/"
    )
    # fix the resulting string closures
    content = content.replace('`"', "`")
    content = content.replace('"`', "`")

    with open(f, "w", encoding="utf-8") as file:
        file.write(content)
