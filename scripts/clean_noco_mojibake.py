import re
import sys

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

path = r"C:\AI-BS\frontend\src\components\ProjectNoCoStudioTab.jsx"
with open(path, "r", encoding="utf-8") as f:
    text = f.read()

replacements = [
    ("dY?", "🏡"),
    ("dY-,?", "🗺️"),
    ("dYZ-", "🎭"),
    ("s", "⚡"),
    ("dYO", "🌱"),
    ("dYZY,?", "🎪"),
    ("s-,?", "⚖️"),
    ("dY\"S", "🔊"),
    ("dYZ ", "🎤"),
    ("dYZ", "🎪"),
    ("dY\"", "📡"),
    ("dY\"O", "🔌"),
    ("dY?>,?", "🏛️"),
    ("dYO_", "🌾"),
    ("dY?,", "🍸"),
    ("dYY", "📐"),
    ("dY?'", "🐴"),
    ("dY\"o", "📜"),
    ("dYZ\"", "🎨"),
    ("5A?\"7A", "5°–7°"),
    ("5A-7A", "5°–7°"),
    ("5A", "5°"),
    ("7A", "7°"),
    ("o.", "✅"),
    ("s,?", "⚠️"),
    ("60 Hz?\"120 Hz", "60 Hz–120 Hz"),
    ("0.90 ?\" 0.98", "0.90–0.98"),
    ("21.4 AC", "21.4°C"),
    ("A Finger Lakes", "• Finger Lakes"),
    ("8 A-A-D Pods", "8 ÖÖD Pods"),
    ("?\" ", "— "),
    ("?\"", "—"),
    ("Vicua", "Vicuña"),
    ("Vicuas", "Vicuñas"),
    ("?? CapEx & ROI", "📊 CapEx & ROI"),
    ("?? Poultry & Integrated", "🐔 Poultry & Integrated"),
    ("??? The Mycelial Radial", "🌀 The Mycelial Radial"),
    ("?? Futuristic Neon Lounge", "🍸 Futuristic Neon Lounge"),
]

for old, new in replacements:
    if old in text:
        count = text.count(old)
        text = text.replace(old, new)
        print(f"Replaced {count} occurrences of {repr(old)} with {repr(new)}")

with open(path, "w", encoding="utf-8") as f:
    f.write(text)

print("Finished cleaning ProjectNoCoStudioTab.jsx.")
