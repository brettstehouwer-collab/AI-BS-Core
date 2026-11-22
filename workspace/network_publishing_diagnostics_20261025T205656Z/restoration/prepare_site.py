"""Small allowlisted static restoration; original publishing tree remains unchanged."""
from pathlib import Path
from datetime import datetime,timezone
import hashlib,json,re,shutil,subprocess,sys
from html.parser import HTMLParser
SRC=Path(r'C:\StehouwerPublishing.com\website-rebuild\dist')
OUT=Path(__file__).resolve().parent
PREFIX=Path(r'C:\StehouwerPublishing.com\restoration_staging\20261025T205656Z')
PUBLIC=PREFIX/'public'
EXE=Path(r'C:\Users\footb\AppData\Local\Microsoft\WinGet\Packages\nginxinc.nginx_Microsoft.Winget.Source_8wekyb3d8bbwe\nginx-1.31.3\nginx.exe')
FILES=['index.html','assets/Preview-DG7rwkwP.js','assets/dash.all.min-BJ49VMfO.js','assets/hls-CoORUb_e.js','assets/index-B6_3PTYU.js','assets/index-DiVaW3ll.css','assets/index-NQ4u1ogD.js','assets/index-UzGUYM6D.js','assets/mixin-DIQKSja0.js','assets/react-BDl8_mUz.js','assets/react-BJcVQbmV.js','assets/react-BSmgMon5.js','assets/react-CWY_MlsN.js','assets/react-CaXKJ2qg.js','assets/react-D60ae7iM.js','assets/react-DbfVaVVq.js','assets/react-DjczQAhS.js','images/brett.jpg','images/julie.jpg']
def sha(b):return hashlib.sha256(b).hexdigest()
class Entry(HTMLParser):
 def __init__(self):super().__init__(convert_charrefs=False);self.parts=[];self.skip=0;self.removed=[]
 def handle_starttag(self,tag,attrs):
  values=dict(attrs)
  if tag=='script':
   source=values.get('src','')
   if values.get('type')=='module' and source.lstrip('/') in FILES and not source.startswith('//'):
    self.parts.append(self.get_starttag_text());return
   self.skip+=1;self.removed.append('non-entry-script');return
  if self.skip:return
  if tag=='link':
   source=values.get('href','')
   if source.startswith(('http:','https:','//')) or values.get('rel') in ('alternate','preconnect','dns-prefetch') or (source.startswith('/') and source.lstrip('/') not in FILES):
    self.removed.append('optional-or-unreviewed-link');return
  self.parts.append(self.get_starttag_text())
 def handle_endtag(self,tag):
  if tag=='script' and self.skip:self.skip-=1;return
  if not self.skip:self.parts.append('</'+tag+'>')
 def handle_data(self,text):
  if not self.skip:self.parts.append(text)
 def handle_entityref(self,name):
  if not self.skip:self.parts.append('&'+name+';')
 def handle_charref(self,name):
  if not self.skip:self.parts.append('&#'+name+';')
 def handle_decl(self,decl):
  if not self.skip:self.parts.append('<!'+decl+'>')
 def handle_comment(self,text):
  if not self.skip:self.parts.append('<!--'+text+'-->')
assert not PREFIX.exists(),'Fresh restoration prefix required'
disk=shutil.disk_usage('C:/')
assert disk.free>10*1024**3,'Insufficient reviewed working space'
assert EXE.is_file()
total=sum((SRC/f).stat().st_size for f in FILES)
assert total<4*1024**2
for relative in FILES:
 p=SRC/relative;assert p.is_file() and not p.is_symlink() and p.resolve().is_relative_to(SRC.resolve())
PREFIX.mkdir(parents=True);PUBLIC.mkdir();(PREFIX/'logs').mkdir()
for name in ('client_body_temp','proxy_temp','fastcgi_temp','uwsgi_temp','scgi_temp'):
 (PREFIX/'temp'/name).mkdir(parents=True,exist_ok=True)
rows=[]
patterns=[rb'-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----',rb'sk_aibs_[A-Za-z0-9_-]{8,}',rb'ghp_[A-Za-z0-9]{20,}',rb'(?i)(?:ledger\.html|invoice\.pdf|invoice\.html|site_analytics\.db)']
for relative in FILES:
 source=SRC/relative;raw=source.read_bytes();assert not any(re.search(pattern,raw) for pattern in patterns)
 content=raw
 if relative=='index.html':
  parser=Entry();parser.feed(raw.decode('utf-8-sig'));parser.close();content=''.join(parser.parts).encode('utf-8')
  assert b'analytics.js' not in content and b'security-shield.js' not in content and b'ld+json' not in content and b'index-NQ4u1ogD.js' in content
 target=PUBLIC/relative;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(content)
 assert source.read_bytes()==raw
 rows.append({'relative':relative,'source_bytes':len(raw),'source_sha256':sha(raw),'bytes':len(content),'sha256':sha(content)})
root=PUBLIC.as_posix()
config=f'''worker_processes 1;
daemon off;
master_process on;
error_log logs/error.log crit;
pid nginx.pid;
events {{ worker_connections 128; }}
http {{
 server_names_hash_bucket_size 64;
 types {{ text/html html; text/css css; application/javascript js mjs; image/jpeg jpg jpeg; image/png png; image/svg+xml svg; application/json json; }}
 default_type application/octet-stream;
 access_log off;
 sendfile on;
 keepalive_timeout 15;
 server {{ listen 127.0.0.1:80 default_server; listen [::1]:80 default_server; server_name _; return 404; }}
 server {{
  listen 127.0.0.1:80; listen [::1]:80;
  server_name stehouwer-publishing.com www.stehouwer-publishing.com;
  root "{root}";
  index index.html;
  add_header X-Content-Type-Options nosniff always;
  add_header Referrer-Policy strict-origin-when-cross-origin always;
  add_header X-Frame-Options SAMEORIGIN always;
  location = / {{ try_files /index.html =404; }}
  location ~ ^/(marketing|film-tv|library|authors|guestbook|live)/?$ {{ try_files /index.html =404; }}
  location / {{ try_files $uri $uri/ =404; }}
 }}
}}
'''
conf=PREFIX/'nginx.static.conf';conf.write_text(config,encoding='utf-8')
response=subprocess.run([str(EXE),'-t','-p',PREFIX.as_posix()+'/', '-c',conf.as_posix()],stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=15,creationflags=subprocess.CREATE_NO_WINDOW)
(OUT/'nginx_config_test.stdout.txt').write_bytes(response.stdout);(OUT/'nginx_config_test.stderr.txt').write_bytes(response.stderr)
receipt={'actor':'/root','utc':datetime.now(timezone.utc).isoformat(),'phase':'prepared_static_origin','prefix':str(PREFIX),'public':str(PUBLIC),'exe':str(EXE),'config':str(conf),'config_sha256':sha(conf.read_bytes()),'file_count':len(rows),'total_bytes':sum(r['bytes'] for r in rows),'source_total_bytes':total,'free_bytes_before':disk.free,'private_or_tracking_files_copied':False,'optional_structured_contact_data_removed':True,'ordinary_website_contact_copy':'retained under explicit owner request to restore intended website; no values exported','source_originals_unchanged':True,'config_test_exit':response.returncode,'files':rows}
(OUT/'static_manifest.json').write_text(json.dumps(receipt,indent=2),encoding='utf-8')
assert response.returncode==0,'Nginx config test failed; evidence retained'
print(json.dumps({k:receipt[k] for k in ('phase','prefix','file_count','total_bytes','config_test_exit','free_bytes_before')},indent=2))

