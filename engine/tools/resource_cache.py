"""Verify Drive downloads before admitting them to an on-demand local cache.

The connector supplies a fresh temporary download URL on stdin. URLs and cloud
credentials are never stored in the catalog. This tool never removes originals.
"""
from pathlib import Path
import hashlib,json,os,re,shutil,sys,tempfile,urllib.parse,urllib.request

def plain(path):
 p=Path(path)
 if '..' in p.parts:raise ValueError('Parent traversal rejected')
 p=p.absolute()
 if any(x.is_symlink() or x.is_junction() for x in (p,*p.parents)):raise ValueError('Redirected cache path rejected')
 return p

def matches(path,size,sha):
 path=plain(path)
 if not path.is_file() or path.stat().st_size!=size:return False
 with path.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()==sha

def admit(source,root,size,sha):
 if type(size) is not int or not 0<=size<=16*1024**3 or not re.fullmatch('[0-9a-f]{64}',sha):raise ValueError('Invalid resource identity')
 source,root=plain(source),plain(root)
 if not root.is_dir() or not matches(source,size,sha):raise ValueError('Downloaded resource size/SHA mismatch')
 target=plain(root/(sha+'.zip'))
 if target.exists():
  if not matches(target,size,sha):raise ValueError('Existing cached revision is damaged')
  return target
 fd,name=tempfile.mkstemp(prefix='.admit-',dir=root);temporary=Path(name)
 try:
  with os.fdopen(fd,'wb') as out,source.open('rb') as inp:
   shutil.copyfileobj(inp,out,1024*1024);out.flush();os.fsync(out.fileno())
  if not matches(temporary,size,sha):raise ValueError('Cache copy changed')
  try:os.link(temporary,target)
  except FileExistsError:
   if not matches(target,size,sha):raise ValueError('Conflicting cached revision')
  return target
 finally:temporary.unlink(missing_ok=True)

def main():
 request=json.load(sys.stdin);url=request['download_url'];parsed=urllib.parse.urlparse(url)
 if parsed.scheme!='https' or not parsed.hostname or not parsed.hostname.endswith('.oaiusercontent.com') or parsed.username:raise ValueError('Expected connector-issued HTTPS download reference')
 root=plain('D:/AI-BS-Game-Resources/cache');root.mkdir(parents=True,exist_ok=True)
 if type(request['bytes']) is not int or not 0<=request['bytes']<=16*1024**3:raise ValueError('Invalid resource byte budget')
 if shutil.disk_usage(root).free<request['bytes']*2+2*1024**3:raise ValueError('Insufficient cache/staging space')
 fd,name=tempfile.mkstemp(prefix='.download-',dir=root);temporary=Path(name)
 try:
  count=0
  with os.fdopen(fd,'wb') as output,urllib.request.urlopen(url,timeout=60) as response:
   while chunk:=response.read(1024*1024):
    count+=len(chunk)
    if count>request['bytes']:raise ValueError('Download exceeds catalog length')
    output.write(chunk)
  result=admit(temporary,root,request['bytes'],request['sha256'])
  print(json.dumps({'status':'passed','cache_path':str(result),'bytes':count,'sha256':request['sha256']}))
 finally:temporary.unlink(missing_ok=True)

if __name__=='__main__':main()
