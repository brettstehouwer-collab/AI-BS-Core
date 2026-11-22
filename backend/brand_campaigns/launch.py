"""User-invoked launcher for the local campaign service and its AI-BS tab."""
import json
import os
from pathlib import Path
import subprocess
import time
from urllib.request import urlopen
import webbrowser

ROOT = Path(__file__).resolve().parents[2]
PYTHON = ROOT / 'runtime/recovery-20261110/Scripts/python.exe'

def ready():
    try:
        with urlopen('http://127.0.0.1:5191/health', timeout=1) as response:
            status = json.loads(response.read(2048))
        return status.get('status') == 'ready' and status.get('dispatch_held') is True
    except (OSError, ValueError):
        return False

def main():
    if not ready():
        logs = ROOT / 'work/brand-campaign-manager-20261114/runtime'
        logs.mkdir(parents=True, exist_ok=True)
        stamp = time.strftime('%Y%m%d-%H%M%S')
        with (logs / (stamp + '.stdout.log')).open('ab') as out, (logs / (stamp + '.stderr.log')).open('ab') as err:
            subprocess.Popen([str(PYTHON), '-m', 'brand_campaigns.service'], cwd=ROOT / 'backend',
                stdout=out, stderr=err, creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0)
        deadline = time.monotonic() + 10
        while not ready():
            if time.monotonic() > deadline:
                raise RuntimeError('Campaign service did not start. Inspect its private runtime log.')
            time.sleep(0.2)
    webbrowser.open('http://localhost:5173/?tab=campaign_automation')

if __name__ == '__main__': main()
