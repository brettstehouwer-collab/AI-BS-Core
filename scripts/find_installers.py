import os
import glob
import time

check_dirs = [
    r'c:\AI-BS',
    r'c:\AI-BS\installers',
    r'c:\AI-BS\scripts',
    r'c:\AI-BS\BroadcastStudioApp',
    r'c:\AI-BS\BroadcastStudioApp\dist-electron',
    r'c:\AI-BS\frontend\desktop-build',
    r'C:\Users\footb\Downloads',
    r'C:\Users\footb\Desktop',
    r'E:\\'
]

print("Scanning for installers and executable setups...")
for d in check_dirs:
    if os.path.exists(d):
        print(f"\n=== {d} ===")
        try:
            entries = os.scandir(d)
            matches = []
            for e in entries:
                if e.is_file():
                    name_l = e.name.lower()
                    if name_l.endswith(('.exe', '.msi', '.iss', '.nsi', '.bat', '.cmd', '.zip', '.tar.gz', '.iso', '.7z', '.json')) or any(k in name_l for k in ['install', 'setup', 'asio', 'fl', 'ableton', 'reaper', 'obs', 'studio']):
                        stat = e.stat()
                        matches.append((stat.st_mtime, e.name, stat.st_size / (1024*1024), e.path))
            matches.sort(key=lambda x: x[0], reverse=True)
            for mtime, name, sz, path in matches[:15]:
                t_str = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(mtime))
                print(f"  [{t_str}] {name} ({sz:.2f} MB)")
        except Exception as err:
            print(f"  Error: {err}")
