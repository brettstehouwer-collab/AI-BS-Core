import subprocess, csv, io

res = subprocess.run(["tasklist", "/v", "/fo", "csv"], capture_output=True, text=True, errors='ignore')
reader = csv.DictReader(io.StringIO(res.stdout))

windows = []
for row in reader:
    title = row.get("Window Title", "")
    pname = row.get("Image Name", "")
    pid = row.get("PID", "")
    mem = row.get("Mem Usage", "")
    
    if title and title != "N/A" and title != "OleMainThreadWndName" and title != "Default IME" and title != "MSCTFIME UI":
        windows.append({
            "title": title,
            "process_name": pname,
            "pid": pid,
            "mem": mem
        })

print(f"Total Visible Window Titles: {len(windows)}")
for w in windows:
    print(f"  - [{w['process_name']}] (PID {w['pid']}): {repr(w['title'])} ({w['mem']})")
