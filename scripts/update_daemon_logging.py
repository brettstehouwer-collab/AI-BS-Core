path = r"C:\AI-BS\scripts\noco_active_sniffer_daemon.py"
with open(path, "r", encoding="utf-8") as f:
    text = f.read()

text = text.replace("print(f", "log(f").replace("print(\"[", "log(\"[").replace("print(\"=\"", "log(\"=\"")
with open(path, "w", encoding="utf-8") as f:
    f.write(text)
print("Updated noco_active_sniffer_daemon.py with log() function.")
