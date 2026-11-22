"""Bounded, raw read-only acceptance; no browser, JS, forms or analytics execution."""
import concurrent.futures
import hashlib
import json
import re
import ssl
import time
from datetime import datetime, timezone
from pathlib import Path
import urllib.error
import urllib.request

ROOT = Path(__file__).resolve().parent
PRIOR = Path(r'C:\AI-BS\workspace\network_publishing_diagnostics_20261025T205656Z\restoration')
manifest = json.loads((PRIOR / 'static_manifest.json').read_text(encoding='utf-8-sig'))
public = Path(manifest['public'])
expected_entry = (public / 'index.html').read_bytes()
private_paths = ('/ledger.html', '/invoice.html', '/invoice.pdf', '/.env', '/indexnow_key.txt', '/analytics.js', '/security-shield.js', '/api/health')

class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None

def normalize(body):
    body, count = re.subn(rb'<script\b[^>]*\bsrc=[\"\']https://static\.cloudflareinsights\.com/[^\"\']+[\"\'][^>]*>\s*</script>', b'', body, flags=re.I)
    return re.sub(rb'>\s+<', b'><', body).strip(), count

def check_one(item):
    url, kind, host = item
    start = time.monotonic()
    out = {'url':url, 'kind':kind, 'observed_utc':datetime.now(timezone.utc).isoformat()}
    headers = {'User-Agent':'AI-BS-Owner-Recovery-ReadOnly/1.0', 'Accept-Encoding':'identity'}
    if host:
        headers['Host'] = host
    request = urllib.request.Request(url, headers=headers, method='GET')
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), NoRedirect(), urllib.request.HTTPSHandler(context=ssl.create_default_context()))
    try:
        try:
            response = opener.open(request, timeout=7)
        except urllib.error.HTTPError as error:
            response = error
        with response:
            out['status'] = response.code
            if kind == 'negative':
                out['pass'] = response.code == 404
                out['body_retained'] = False
            else:
                body = response.read(32769)
                out.update(bytes_read=len(body), sha256=hashlib.sha256(body).hexdigest(), bounded=len(body)<=32768)
                out['pass'] = response.code == 200 and len(body)<=32768
                if kind in ('public_entry','origin_entry'):
                    normalized, count = normalize(body)
                    out['recognized_cf_script_count'] = count
                    out['reviewed_origin_match'] = normalized == normalize(expected_entry)[0]
                    out['legacy_analytics_absent'] = b'/analytics.js' not in body and b'/security-shield.js' not in body
                    out['pass'] = out['pass'] and out['reviewed_origin_match'] and out['legacy_analytics_absent']
                    if kind == 'origin_entry':
                        out['byte_exact_entry_match'] = body == expected_entry
                        out['pass'] = out['pass'] and out['byte_exact_entry_match']
                if kind == 'api_health':
                    try:
                        data = json.loads(body)
                        out['json_object'] = isinstance(data,dict)
                        out['pass'] = out['pass'] and out['json_object']
                    except ValueError:
                        out['json_object'] = False
                        out['pass'] = False
    except Exception as error:
        out.update(pass_=False, error_type=type(error).__name__)
        out['pass'] = False
    out['elapsed_seconds'] = round(time.monotonic()-start,3)
    return out

items = [
    ('https://stehouwer-publishing.com/','public_entry',None),
    ('https://www.stehouwer-publishing.com/','public_entry',None),
    ('http://127.0.0.1/','origin_entry','stehouwer-publishing.com'),
    ('http://127.0.0.1/','origin_entry','www.stehouwer-publishing.com'),
    ('https://api.brettstehouwer.live/health','api_health',None),
    ('http://127.0.0.1:8000/health','api_health',None),
    ('http://127.0.0.1:8080/health','api_health',None),
    ('http://127.0.0.1:11434/api/version','api_health',None),
    ('http://127.0.0.1:5173/','frontend_root',None),
]
items += [('https://stehouwer-publishing.com'+path,'negative',None) for path in private_paths]
with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
    checks = list(pool.map(check_one,items))

hash_checks=[]
for entry in manifest['files']:
    file = public / entry['relative']
    try:
        data=file.read_bytes()
        ok=len(data)==entry['bytes'] and hashlib.sha256(data).hexdigest()==entry['sha256']
        hash_checks.append({'relative':entry['relative'],'pass':ok})
    except Exception as error:
        hash_checks.append({'relative':entry['relative'],'pass':False,'error_type':type(error).__name__})
out={'observed_utc':datetime.now(timezone.utc).isoformat(),'scope':'Raw bounded GET only; no JS execution, browser or submitted fields; no full response bodies retained','checks':checks,'static_hash_checks':hash_checks,'http_all_pass':all(c['pass'] for c in checks),'static_all_pass':all(c['pass'] for c in hash_checks),'requests':len(checks),'static_files':len(hash_checks)}
(ROOT/'http_acceptance.json').write_text(json.dumps(out,indent=2)+'\n',encoding='utf-8')
print(json.dumps({k:out[k] for k in ('observed_utc','requests','static_files','http_all_pass','static_all_pass')}))
for c in checks:
    print(json.dumps({k:c[k] for k in ('url','status','pass','reviewed_origin_match','error_type') if k in c}))
