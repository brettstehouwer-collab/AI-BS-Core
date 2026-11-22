import sys
import traceback

with open(r"C:\AI-BS\native_studio\direct_run.log", "w", encoding="utf-8") as f:
    f.write("direct_run test starting\n")
    try:
        from PyQt6.QtWidgets import QApplication
        app = QApplication(sys.argv)
        f.write("QApp created\n")
        
        from native_studio.app import MainWindow
        win = MainWindow()
        f.write("MainWindow created\n")
        
        win.show()
        f.write("MainWindow shown\n")
        
        # Test 1 iteration of event loop
        app.processEvents()
        f.write("processEvents succeeded\n")
    except Exception as e:
        f.write("EXCEPTION in direct_run:\n")
        traceback.print_exc(file=f)

print("Finished direct_run test")
