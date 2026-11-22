import sys
from pathlib import Path

# Add C:\AI-BS root
sys.path.insert(0, r"C:\AI-BS")
sys.path.insert(0, r"C:\AI-BS\native_studio")

import traceback

with open(r"C:\AI-BS\native_studio\crash.log", "w", encoding="utf-8") as f:
    f.write("Starting crash diagnostic with sys.path...\n")
    try:
        from PyQt6.QtWidgets import QApplication
        app = QApplication(sys.argv)
        f.write("QApplication initialized\n")
        
        import app as a
        f.write("app module imported\n")
        
        win = a.MainWindow()
        f.write("MainWindow created\n")
        
        win.show()
        f.write("MainWindow.show() called\n")
    except Exception as e:
        f.write("EXCEPTION OCCURRED:\n")
        traceback.print_exc(file=f)

print("Diagnostic finished, check crash.log")
