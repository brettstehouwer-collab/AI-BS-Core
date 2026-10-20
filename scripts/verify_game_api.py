import urllib.request
import json
import time

time.sleep(1)

for port in [8088, 8005]:
    for endpoint in ['/api/windows', '/api/active_game']:
        try:
            url = f'http://127.0.0.1:{port}{endpoint}'
            req = urllib.request.Request(url, headers={'X-Client-ID': 'stehouwer_publishing'})
            with urllib.request.urlopen(req, timeout=3) as resp:
                data = json.loads(resp.read().decode('utf-8'))
                print(f"=== Port {port}{endpoint} ===")
                if 'active_game' in data and data['active_game']:
                    ag = data['active_game']
                    print(f"  [ACTIVE GAME] {ag.get('game_name') or ag.get('title')} ({ag.get('process_name')}) PID: {ag.get('pid')}")
                if 'windows' in data:
                    print(f"  [WINDOWS] Total: {len(data['windows'])}")
                    for w in data['windows'][:4]:
                        title = w.get('title') if isinstance(w, dict) else w
                        pname = w.get('process_name', '') if isinstance(w, dict) else ''
                        is_g = w.get('is_game', False) if isinstance(w, dict) else False
                        print(f"    - {'[GAME]' if is_g else '[WIN]'} {title} ({pname})")
        except Exception as e:
            print(f"Port {port}{endpoint} Error: {e}")
