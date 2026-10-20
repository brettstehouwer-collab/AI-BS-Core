import win32gui
import win32process
import psutil

print('--- All Visible Top-Level Windows ---')
windows = []
def enum_all(hwnd, extra):
    try:
        if win32gui.IsWindowVisible(hwnd):
            rect = win32gui.GetWindowRect(hwnd)
            w = rect[2] - rect[0]
            h = rect[3] - rect[1]
            title = win32gui.GetWindowText(hwnd).strip()
            if w > 50 and h > 50 and title:
                try:
                    _, pid = win32process.GetWindowThreadProcessId(hwnd)
                    pname = psutil.Process(pid).name()
                    print(f'  - Title: "{title}" | Exe: {pname} | Size: {w}x{h} | PID: {pid}')
                    windows.append({'title': title, 'process_name': pname, 'pid': pid})
                except Exception:
                    print(f'  - Title: "{title}" | Size: {w}x{h}')
    except Exception:
        pass
    return True

try:
    win32gui.EnumWindows(enum_all, 0)
except Exception as e:
    print('EnumWindows error:', e)

print(f'\nTotal windows collected: {len(windows)}')

print('\n--- Running Processes with DirectX/GPU/Game names ---')
for p in psutil.process_iter(['pid', 'name', 'exe']):
    try:
        pname = p.info['name'].lower()
        if any(g in pname for g in ['game', 'fortnite', 'cod', 'warzone', 'valorant', 'apex', 'roblox', 'minecraft', 'steam', 'epic', 'overwatch', 'cyberpunk', 'unity', 'unreal']):
            print(f'  - Process: {p.info["name"]} (PID {p.info["pid"]})')
    except Exception:
        pass
