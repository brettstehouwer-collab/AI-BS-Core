"""Bounded direct-loopback model timing; never execute responses or write app stores."""
import hashlib
import http.client
import json
import math
from pathlib import Path
import statistics
import subprocess
import sys
import time
from datetime import datetime, timezone

ROOT = Path('C:/AI-BS')
OUT = Path((ROOT / 'scratch/phase6_model_baseline_checkpoint.txt').read_text().strip())
MODEL = 'stehouwer_llm:latest'
DIGEST = '5213ff76656a20b564e1001cc3cc4e9e9b7f8cc80dd837cde54b341127e60b12'
PROMPT = 'Compute 19 + 23. Reply with only the integer result.'
PAYLOAD = dict(model=MODEL, prompt=PROMPT, stream=True, keep_alive='5m',
               options=dict(num_ctx=4096, num_predict=32, temperature=0, seed=42))


def utc():
    return datetime.now(timezone.utc).isoformat()


def get(route):
    conn = http.client.HTTPConnection('127.0.0.1', 11434, timeout=5)
    try:
        conn.request('GET', route)
        response = conn.getresponse()
        if response.status != 200:
            raise RuntimeError(f'{route} HTTP {response.status}')
        return json.loads(response.read(1048576))
    finally:
        conn.close()


def gpu():
    try:
        return subprocess.run(['nvidia-smi', '--query-gpu=memory.used,utilization.gpu,temperature.gpu,power.draw',
                               '--format=csv,noheader,nounits'], capture_output=True,
                              text=True, timeout=5, check=True).stdout.strip()
    except Exception as exc:
        return {'unavailable': type(exc).__name__}


def one(label):
    record = dict(label=label, started_utc=utc(), gpu_before=gpu(), terminal=False)
    raw = OUT / f'{label}.ndjson'
    budget = 180 if label == 'warmup' else 60
    record['client_budget_seconds'] = budget
    conn = http.client.HTTPConnection('127.0.0.1', 11434, timeout=budget)
    first_output = first_text = None
    total_bytes = 0
    text = []
    start = time.perf_counter()
    try:
        conn.request('POST', '/api/generate', body=json.dumps(PAYLOAD),
                     headers={'Content-Type': 'application/json'})
        response = conn.getresponse()
        if response.status != 200:
            raise RuntimeError(f'Generate HTTP {response.status}')
        with raw.open('xb') as stream:
            while True:
                line = response.readline(65537)
                if not line:
                    break
                total_bytes += len(line)
                stream.write(line)
                if len(line) > 65536 or total_bytes > 1048576:
                    raise RuntimeError('Benchmark output limit exceeded')
                now = time.perf_counter() - start
                if now > budget:
                    raise TimeoutError('Benchmark client overall budget exceeded')
                item = json.loads(line)
                if 'error' in item:
                    raise RuntimeError('Model response error: ' + str(item['error'])[:300])
                if (item.get('response') or item.get('thinking')) and first_output is None:
                    first_output = now
                if item.get('response'):
                    first_text = now if first_text is None else first_text
                    text.append(item['response'])
                if item.get('done') is True:
                    record['terminal'] = True
                    record['metrics'] = {k: item.get(k) for k in (
                        'total_duration', 'load_duration', 'prompt_eval_count',
                        'prompt_eval_duration', 'eval_count', 'eval_duration', 'done_reason')}
                    break
        if not record['terminal']:
            raise RuntimeError('Stream ended without terminal done=true')
        output = ''.join(text)
        record.update(success=True, response_sha256=hashlib.sha256(output.encode()).hexdigest(),
                      exact_fixture_answer=output.strip() == '42', response_chars=len(output))
    except Exception as exc:
        record.update(success=False, error=type(exc).__name__ + ': ' + str(exc))
    finally:
        record.update(elapsed_seconds=time.perf_counter() - start,
                      first_output_seconds=first_output, first_text_seconds=first_text,
                      output_bytes=total_bytes, finished_utc=utc())
        conn.close()
        (OUT / f'{label}.json').write_text(json.dumps(record, indent=2))
    print(json.dumps({k: record.get(k) for k in ('label', 'success', 'elapsed_seconds', 'first_output_seconds', 'exact_fixture_answer', 'error')}), flush=True)
    return record


def main():
    metadata = dict(started_utc=utc(), request=PAYLOAD, prompt_bytes=len(PROMPT.encode()),
                    server_version=get('/api/version'), loaded_before=get('/api/ps'),
                    model=MODEL, expected_digest=DIGEST, scope='direct loopback synthetic inference only')
    tags = get('/api/tags')
    selected = [m for m in tags['models'] if m['name'] == MODEL]
    if len(selected) != 1 or selected[0]['digest'] != DIGEST:
        raise RuntimeError('Existing model digest differs; do not substitute or pull')
    metadata['model_metadata'] = selected[0]
    (OUT / 'metadata.json').write_text(json.dumps(metadata, indent=2))
    print('WARMUP_STARTED', flush=True)
    warmup = one('warmup')
    records = []
    if warmup.get('success'):
        for index in range(1, 11):
            loaded = get('/api/ps').get('models', [])
            if not any(m.get('digest') == DIGEST for m in loaded):
                raise RuntimeError('Warm model unavailable; stop instead of mixing conditions')
            record = one(f'warm_{index:02d}')
            records.append(record)
            if not record.get('success'):
                break  # Never repeat a failed model request automatically.
    successful = [r for r in records if r.get('success')]
    summary = dict(completed_utc=utc(), attempts_including_warmup=1+len(records),
                   failed_attempts_including_warmup=int(not warmup.get('success'))+len(records)-len(successful),
                   measured_runs=len(records), successes=len(successful),
                   failures=len(records)-len(successful), required_warm_runs=10,
                   comparable_warm_condition_complete=len(successful) == 10,
                   warmup=warmup, loaded_after=get('/api/ps'), gpu_after=gpu(),
                   exact_fixture_answers=sum(bool(r.get('exact_fixture_answer')) for r in successful),
                   limitations=['One synthetic repeated prompt; cache reuse is permitted, not independently measured.',
                                'No OS/network disconnection test or end-to-end app/code timing.',
                                'No real documents, app databases, or generated-code execution.',
                                'First output may include thinking; first text recorded separately.',
                                'Initial load observation is one warmup, not a cold-run distribution.',
                                'Concurrent host load observed, not fully controlled.'])
    if successful:
        for key in ('elapsed_seconds', 'first_output_seconds', 'first_text_seconds'):
            values = sorted(r[key] for r in successful if r.get(key) is not None)
            summary[key] = dict(n=len(values), median=statistics.median(values),
                                p95_nearest_rank=values[math.ceil(.95*len(values))-1]) if values else None
    (OUT / 'summary.json').write_text(json.dumps(summary, indent=2))
    print('BASELINE_FINISHED ' + json.dumps({k: summary[k] for k in ('measured_runs', 'successes', 'failures', 'comparable_warm_condition_complete')}), flush=True)


if __name__ == '__main__':
    try:
        main()
    except Exception as exc:
        (OUT / 'failure.json').write_text(json.dumps(dict(time_utc=utc(), error=type(exc).__name__ + ': ' + str(exc)), indent=2))
        raise
