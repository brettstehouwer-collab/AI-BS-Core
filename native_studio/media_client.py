"""Owner-private, bounded authenticated media cache. Model URLs never select credential origins."""
from __future__ import annotations
from dataclasses import dataclass
import hashlib,os,re,uuid,threading
from pathlib import Path
from urllib.parse import urlsplit,parse_qsl,urlencode,unquote
import httpx
from native_studio.local_connection import local_service_headers

PATHS={'/api/comfy/media','/api/comfyui/view','/api/comfy/view'}
KINDS={'.png':'image','.jpg':'image','.jpeg':'image','.webp':'image','.mp4':'video','.webm':'video','.wav':'audio','.mp3':'audio','.ogg':'audio'}
class NativeMediaError(RuntimeError):pass

def file_sha256(path):
    with Path(path).open('rb')as stream:return hashlib.file_digest(stream,'sha256').hexdigest()

def media_route(value):
    if not isinstance(value,str)or not value or len(value)>4096 or re.search(r'[\x00-\x20<>"\']',value):return None
    try:
        url=urlsplit(value.replace('&amp;','&'))
        if url.fragment or url.username or url.password:return None
        if url.netloc:
            if (url.scheme,url.netloc)not in {('http','127.0.0.1:8080'),('https','api.brettstehouwer.live')}:return None
        elif url.scheme or not value.startswith('/'):return None
        if url.path not in PATHS:return None
        pairs=parse_qsl(url.query,keep_blank_values=True)
        if len({k for k,v in pairs})!=len(pairs)or any(k not in {'filename','type','subfolder'}for k,v in pairs):return None
        query=dict(pairs);filename=query.get('filename','');folder=query.get('subfolder','')
        if not filename or filename!=Path(filename).name or re.search(r'[/\\:\x00-\x1f]',filename)or '%'in filename:return None
        if Path(filename).suffix.lower()not in KINDS or query.get('type','output')!='output':return None
        if re.search(r'[\\:\x00-\x1f%]',folder)or folder.startswith('/')or any(p in {'.','..'}for p in folder.split('/')):return None
        return url.path+'?'+urlencode(pairs)
    except (ValueError,TypeError):return None

def media_references(text):
    if not isinstance(text,str)or text.lstrip().startswith(('{','['))and re.match(r'^\s*[\[{]\s*["\{]',text):return []
    values=re.findall(r'!?\[[^\]\r\n]*\]\(([^\s)]+)\)',text)
    values+=re.findall(r'<(?:video|audio|source|img)\b[^>]*\bsrc=["\']([^"\']+)["\']',text,flags=re.I)
    result=[]
    for value in values:
        route=media_route(value)
        if route and route not in result:result.append(route)
    return result[:16]

@dataclass(frozen=True)
class CachedMedia:
    path:Path
    filename:str
    kind:str
    mime:str
    size:int
    sha256:str
    route:str

def _signature(mime,data):
    if mime=='image/png':return data.startswith(b'\x89PNG\r\n\x1a\n')
    if mime=='image/jpeg':return data.startswith(b'\xff\xd8\xff')
    if mime=='image/webp':return data.startswith(b'RIFF')and data[8:12]==b'WEBP'
    if mime=='video/mp4':return data[4:8]==b'ftyp'
    if mime=='video/webm':return data.startswith(b'\x1a\x45\xdf\xa3')
    if mime in {'audio/wav','audio/x-wav'}:return data.startswith(b'RIFF')and data[8:12]==b'WAVE'
    if mime=='audio/mpeg':return data.startswith(b'ID3')or len(data)>1 and data[0]==255 and data[1]&224==224
    if mime=='audio/ogg':return data.startswith(b'OggS')
    return False

class NativeMediaClient:
    def __init__(self,*,root=None,headers_provider=None,transport=None,prepare_directory=None):
        self.root=Path(root)if root else None;self.headers_provider=headers_provider or local_service_headers
        self.transport=transport;self.prepare_directory=prepare_directory;self.max_bytes=256*1024*1024
        self._cache={};self._lock=threading.Lock()
    def _prepare(self):
        if self.root is None:
            from native_studio.local_connection import _current_identity
            profile=hashlib.sha256(_current_identity().owner_sid.encode()).hexdigest()[:24]
            local=Path(os.environ.get('LOCALAPPDATA',''))
            if not local.is_absolute():raise NativeMediaError('Private media storage is unavailable.')
            self.root=local/'AI-BS/NativeStudio/Media'/profile
        if any(p.is_symlink()or p.is_junction()for p in [self.root,*self.root.parents]):raise NativeMediaError('Private media storage is redirected.')
        if self.prepare_directory:self.prepare_directory(self.root)
        else:
            from native_studio.screenplay_client import _private_recovery_directory
            _private_recovery_directory(self.root,self.root.parent)
    def fetch(self,value):
        route=media_route(value)
        if not route:raise NativeMediaError('This media reference is not supported by the private service connection.')
        with self._lock:
            try:
                self._prepare()
                cached=self._cache.get(route)
                if cached and not cached.path.is_symlink()and cached.path.is_file()and cached.path.stat().st_size==cached.size and file_sha256(cached.path)==cached.sha256:return cached
                headers=dict(self.headers_provider())
                if not headers:raise NativeMediaError('The private media connection is not ready.')
                filename=dict(parse_qsl(urlsplit(route).query))['filename'];suffix=Path(filename).suffix.lower()
                partial=self.root/(uuid.uuid4().hex+suffix+'.partial');size=0;digest=hashlib.sha256();head=b''
                with httpx.Client(base_url='http://127.0.0.1:8080',headers=headers,trust_env=False,
                    follow_redirects=False,transport=self.transport,timeout=httpx.Timeout(120,connect=5))as client:
                    with client.stream('GET',route)as response:
                        if response.status_code in {401,403}:raise NativeMediaError('The media service refused this connection.')
                        if response.status_code!=200:raise NativeMediaError(f'Media unavailable (HTTP{response.status_code}).')
                        mime=response.headers.get('content-type','').split(';')[0].lower()
                        if mime.split('/')[0]!=KINDS[suffix]:raise NativeMediaError('The service did not return the expected media type.')
                        length=response.headers.get('content-length')
                        if length and int(length)>self.max_bytes:raise NativeMediaError('This file exceeds the256MiBnative preview limit.')
                        with partial.open('xb')as out:
                            for chunk in response.iter_bytes(65536):
                                size+=len(chunk)
                                if size>self.max_bytes:raise NativeMediaError('This file exceeds the256MiBnative preview limit.')
                                if len(head)<64:head=(head+chunk)[:64]
                                digest.update(chunk);out.write(chunk)
                            out.flush();os.fsync(out.fileno())
                if not size or length and int(length)!=size or not _signature(mime,head):raise NativeMediaError('The service returned an empty, incomplete or invalid media file. No successful preview was published.')
                target=partial.with_suffix('');partial.rename(target)
                result=CachedMedia(target,filename,KINDS[suffix],mime,size,digest.hexdigest(),route);self._cache[route]=result;return result
            except NativeMediaError:raise
            except Exception:
                raise NativeMediaError('Media could not be verified. Incomplete download evidence was retained; no automatic retry was sent.')from None
