import win32gui

def _find_game(hwnd, ctx):
    title = win32gui.GetWindowText(hwnd)
    if "Call of Duty" in title or "Warzone" in title:
        ctx.append(title)
        
games = []
win32gui.EnumWindows(_find_game, games)
print(games)
