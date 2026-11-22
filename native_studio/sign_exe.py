"""Legacy entry point: require an explicit pinned candidate and new output path."""
from pathlib import Path
import runpy

if __name__ == '__main__':
    runpy.run_path(str(Path(__file__).resolve().parents[1] / 'scripts/sign_native_candidate.py'),
                   run_name='__main__')
