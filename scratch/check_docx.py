for pkg in ['docx', 'fitz', 'fpdf']:
    try:
        __import__(pkg)
        print(f"{pkg}: available")
    except Exception as e:
        print(f"{pkg}: {e}")
