for pkg in ['reportlab', 'weasyprint', 'fpdf', 'fitz', 'docx', 'playwright']:
    try:
        __import__(pkg)
        print(f"{pkg}: available")
    except ImportError:
        print(f"{pkg}: not available")
