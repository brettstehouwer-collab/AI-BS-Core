"""Native executive service adapter: observed state and acknowledged actions.

No backend imports, database access, process activation, Git or host execution.
Local credentials target only the owned literal IPv4 backend, never its peers.
"""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
import socket,time
from urllib.parse import quote
import httpx
from native_studio.local_connection import local_service_headers

ORIGIN='http://127.0.0.1:8080'
PREFIX='/api/v1/executive'
PORTS=(8080,8000,5173,8188,8189,8888,8007,11434,11435,8002,8013)
MODES={'SAFE','SEMI_AUTO','FULL_AUTO'}


class ExecutiveServiceError(RuntimeError):
    pass


def _probe(port):
    try:
        with socket.create_connection(('127.0.0.1',port),timeout=0.2):return True
    except OSError:return False


class ExecutiveService:
    def __init__(self,*,headers_provider=None,transport=None,port_probe=None,hardware_provider=None):
        self.headers_provider=headers_provider or local_service_headers
        self.transport=transport
        self.port_probe=port_probe or _probe
        self.hardware_provider=hardware_provider or self._hardware
        self._gpu=None

    def _hardware(self):
        from native_studio.engine import GpuProbe,sample_system
        if self._gpu is None:self._gpu=GpuProbe()
        return {'system':sample_system(),'gpu':self._gpu.sample()}

    def _request(self,method,path,*,payload=None,peer=False):
        origin='http://127.0.0.1:11434' if peer else ORIGIN
        try:
            headers={} if peer else dict(self.headers_provider())
            if not peer and not headers:
                raise ExecutiveServiceError('The private executive connection is not ready. No API key entry is required.')
            with httpx.Client(base_url=origin,headers=headers,transport=self.transport,
                              trust_env=False,follow_redirects=False,timeout=180 if path==PREFIX+'/chat' else 3) as client:
                response=client.request(method,path,json=payload)
            if response.status_code in {401,403}:
                raise ExecutiveServiceError('The executive service refused this connection.')
            if response.status_code!=200:
                raise ExecutiveServiceError(f'The executive service returned HTTP {response.status_code}; no result was confirmed.')
            if len(response.content)>2*1024*1024:
                raise ExecutiveServiceError('The executive response exceeds the display limit.')
            data=response.json()
            if not isinstance(data,dict) or data.get('status') in {'error','failed'} or data.get('success') is False:
                raise ExecutiveServiceError('The executive service did not confirm this result.')
            return data
        except ExecutiveServiceError:raise
        except Exception:
            raise ExecutiveServiceError('The executive service did not confirm this request. Refresh state before retrying an action.') from None

    def _list(self,path,key,*,peer=False):
        data=self._request('GET',path,peer=peer)
        if not isinstance(data.get(key),list) or len(data[key])>10000 or any(not isinstance(row,dict)for row in data[key]):
            raise ExecutiveServiceError('The executive service returned an invalid list.')
        return data

    def get_autonomy(self):
        data=self._request('GET',PREFIX+'/settings/autonomy')
        if data.get('autonomy_mode')not in MODES:
            raise ExecutiveServiceError('The service did not identify its current governance mode.')
        return data

    def _cloud(self):
        data=self._request('GET',PREFIX+'/cloud/status')
        if not isinstance(data.get('gpu_sovereignty'),dict):
            raise ExecutiveServiceError('The service did not return its spend policy.')
        return data

    def _sentinel(self):
        data=self._list(PREFIX+'/sentinel/alerts?limit=10','alerts')
        if not isinstance(data.get('engine_status'),dict):
            raise ExecutiveServiceError('The service did not identify the sentinel state.')
        return data

    @staticmethod
    def _observe(fn):
        try:return {'ok':True,'data':fn()}
        except Exception:return {'ok':False,'error':'Unavailable; no current observation.'}

    def snapshot(self):
        # Avoid legacy matrix/status: it dispatches crypto and asserts media
        # readiness. Refresh is observational and never calls action endpoints.
        jobs={
            'backend':lambda:self._request('GET','/health'),
            'pending':lambda:self._list(PREFIX+'/actions/pending','pending_actions'),
            'history':lambda:self._list(PREFIX+'/actions/history?limit=25','history'),
            'autonomy':self.get_autonomy,
            'sentinel':self._sentinel,
            'cloud':self._cloud,
            'installed_models':lambda:self._list('/api/tags','models',peer=True),
            'loaded_models':lambda:self._list('/api/ps','models',peer=True),
            'hardware':self.hardware_provider,
        }
        def port_state(port):
            try:state=bool(self.port_probe(port))
            except Exception:state=None
            return {'listening':state,'onDemand':port==8888}
        with ThreadPoolExecutor(max_workers=6)as pool:
            futures={key:pool.submit(self._observe,fn)for key,fn in jobs.items()}
            ports={port:pool.submit(port_state,port)for port in PORTS}
            sections={key:f.result()for key,f in futures.items()}
            observed={port:f.result()for port,f in ports.items()}
        return {'observedAt':time.time(),'observedMonotonic':time.monotonic(),'sections':sections,'ports':observed}

    def set_autonomy(self,mode):
        if mode not in MODES:raise ValueError('Choose an established governance mode.')
        data=self._request('POST',PREFIX+'/settings/autonomy',payload={'mode':mode})
        if data.get('status')!='success' or data.get('autonomy_mode')!=mode:
            raise ExecutiveServiceError('The service did not acknowledge the requested governance mode.')
        return data

    def halt(self):
        data=self._request('POST',PREFIX+'/actions/halt',payload={})
        if data.get('status')!='HALTED' or data.get('autonomy_mode')!='SAFE':
            raise ExecutiveServiceError('The service did not acknowledge a halt. Treat pending actions as unconfirmed.')
        return data

    def resolve(self,action_id,decision):
        if (not isinstance(action_id,str) or not action_id or len(action_id)>256 or action_id in {'.','..'}
                or any(c in action_id for c in '/\\') or any(ord(c)<32 for c in action_id)
                or decision not in {'APPROVE','REJECT'}):
            raise ValueError('A valid action and decision are required.')
        data=self._request('POST',PREFIX+'/actions/'+quote(action_id,safe='')+'/resolve',payload={'decision':decision})
        if data.get('status')!='success' or not isinstance(data.get('resolution'),dict):
            raise ExecutiveServiceError('The service did not acknowledge the action decision.')
        return data

    def chat(self,prompt,model):
        if not isinstance(prompt,str)or not prompt.strip()or not isinstance(model,str)or not model.strip():
            raise ValueError('A prompt and an available model are required.')
        data=self._request('POST',PREFIX+'/chat',payload={'prompt':prompt,'model':model})
        if data.get('status')!='success' or not isinstance(data.get('response'),str)or not isinstance(data.get('tool_calls'),list):
            raise ExecutiveServiceError('The executive service did not return a confirmed response. Your draft is retained.')
        return data
