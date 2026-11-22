"""One bounded local inference request. No backend app or execution tools loaded."""
import json
from pathlib import Path
import sys

from .coding_chat import _http_generate
from .coding_recovery import REQUESTS


def main():
    if len(sys.argv)!=2:raise ValueError('One admitted inference input is required')
    path=Path(sys.argv[1]).resolve()
    if not path.is_relative_to(REQUESTS.resolve()) or path.name!='input.json':
        raise ValueError('Inference input must be inside the admitted request store')
    if path.stat().st_size>262144:raise ValueError('Inference input exceeded limit')
    data=json.loads(path.read_text(encoding='utf-8'))
    answer=_http_generate(data['prompt'],data['context'],data['allowed'],
                          reference_context=data.get('reference_context',''))
    print(json.dumps(answer),flush=True)


if __name__=='__main__':
    try:main()
    except Exception as exc:
        print(str(exc),file=sys.stderr,flush=True)
        raise SystemExit(1)
