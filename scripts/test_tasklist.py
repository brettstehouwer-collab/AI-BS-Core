import subprocess, csv, io, psutil

# Test tasklist /v /fo csv
print("=== Testing tasklist /v /fo csv ===")
res = subprocess.run(["tasklist", "/v", "/fo", "csv"], capture_output=True, text=True, errors='ignore')
reader = csv.DictReader(io.StringIO(res.stdout))

windows = []
for row in reader:
    title = row.get("Window Title", "")
    pname = row.get("Image Name", "")
    pid = row.get("PID", "")
    mem = row.get("Mem Usage", "")
    
    if title and title != "N/A" and title != "OleMainThreadWndName":
        windows.append({
            "title": title,
            "process_name": pname,
            "pid": pid,
            "mem": mem
        })

print(f"Total Window Titles from tasklist: {len(windows)}")
for w in windows:
    print(f"  🎮 [{w['process_name']}] PID {w['pid']}: \"{w['title']}\" ({w['mem']})")
