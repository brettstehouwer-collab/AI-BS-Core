"""Authenticated shared BS-Chat transport; no local model, tool or subprocess execution."""
from __future__ import annotations
import re
import httpx
from native_studio.local_connection import local_service_headers

ORIGIN='http://127.0.0.1:8080'
ROUTE='/api/v1/hybrid-chat/stream'

class NativeChatError(RuntimeError):
    pass

class _VisibleStream:
    """Suppress split metadata comments without delaying ordinary visible text."""
    marker='<!--AI-BS-METADATA:'
    def __init__(self):self.pending='';self.hidden=False
    def feed(self,text,final=False):
        self.pending+=text;visible=''
        while self.pending:
            if self.hidden:
                end=self.pending.find('-->')
                if end<0:
                    self.pending=self.pending[-2:];break
                self.pending=self.pending[end+3:];self.hidden=False;continue
            start=self.pending.find(self.marker)
            if start>=0:
                visible+=self.pending[:start];self.pending=self.pending[start+len(self.marker):];self.hidden=True;continue
            hold=0
            if not final:
                for size in range(1,min(len(self.marker),len(self.pending))+1):
                    if self.marker.startswith(self.pending[-size:]):hold=size
            visible+=self.pending[:-hold]if hold else self.pending
            self.pending=self.pending[-hold:]if hold else '';break
        return visible

class NativeChatService:
    def __init__(self,*,headers_provider=None,transport=None):
        self.headers_provider=headers_provider or local_service_headers;self.transport=transport
    def execute_once(self,command,*,runtime='powershell',file_path=None):
        aliases={'auto':'powershell','ps':'powershell','ps1':'powershell','bat':'cmd','py':'python','js':'node'}
        runtime=aliases.get(runtime,runtime)
        if runtime not in {'powershell','cmd','wsl','bash','python','node','ts','go','rust','cpp','c','sql'}:
            raise NativeChatError('Choose a supported runtime before submitting this command.')
        if not isinstance(command,str)or not command.strip()or len(command)>128000:
            raise NativeChatError('Enter a bounded command to submit to the service.')
        try:
            headers=dict(self.headers_provider())
            if not headers:raise NativeChatError('The private command connection is not ready.')
            extra={'timeout_seconds':120}
            if file_path:extra['file_path']=file_path
            with httpx.Client(base_url=ORIGIN,headers=headers,trust_env=False,follow_redirects=False,
                              transport=self.transport,timeout=httpx.Timeout(130,connect=5))as client:
                response=client.post('/api/executive/run',json={'command_type':runtime,'target':command,'payload':extra})
            if response.status_code!=200:raise NativeChatError(f'The command service returned HTTP{response.status_code}; execution was not confirmed.')
            if len(response.content)>4*1024*1024:raise NativeChatError('The command output exceeds the display limit. Inspect service history before retrying.')
            result=response.json()
            if not isinstance(result,dict)or type(result.get('returncode'))is not int:
                raise NativeChatError('The service did not confirm a command exit code. Inspect service history before retrying.')
            return {key:result.get(key)for key in ('status','returncode','stdout','stderr','elapsed_ms')}
        except NativeChatError:raise
        except Exception:
            raise NativeChatError('Command execution was not confirmed. Inspect service history before retrying; no automatic retry was sent.')from None
    def stream(self,prompt,*,history=(),use_web_search=False,on_text=None):
        if not isinstance(prompt,str)or not prompt.strip()or len(prompt)>128000:
            raise NativeChatError('Enter a message of up to128000characters. Your draft is retained.')
        if type(use_web_search)is not bool:raise NativeChatError('Choose whether to use web search for this message.')
        messages=[];size=0
        for pair in reversed(list(history)[-10:]):
            if not isinstance(pair,(list,tuple))or len(pair)!=2 or not all(isinstance(x,str)for x in pair):
                raise NativeChatError('Conversation history needs attention. Existing copies are retained.')
            if size+sum(map(len,pair))>64000:break
            messages[0:0]=[{'role':'user','content':pair[0]},{'role':'assistant','content':pair[1]}];size+=sum(map(len,pair))
        try:
            headers=dict(self.headers_provider())
            if not headers:raise NativeChatError('The private chat connection is not ready. No API key entry is required.')
            payload={'prompt':prompt,'user_prompt':prompt,'messages':messages,'stream':True,'use_web_search':use_web_search,
                     'web_search_query':prompt[:500]if use_web_search else ''}
            output=[];received=0;visible=_VisibleStream()
            with httpx.Client(base_url=ORIGIN,headers=headers,trust_env=False,follow_redirects=False,
                              transport=self.transport,timeout=httpx.Timeout(300,connect=5))as client:
                with client.stream('POST',ROUTE,json=payload)as response:
                    if response.status_code in {401,403}:raise NativeChatError('The local chat service refused this connection. Your draft is retained.')
                    if response.status_code!=200:raise NativeChatError(f'The chat service returned HTTP{response.status_code}; no complete response was confirmed.')
                    for text in response.iter_text():
                        received+=len(text.encode('utf-8'))
                        if received>4*1024*1024:raise NativeChatError('The response exceeds the display limit. Partial text and your draft are retained.')
                        part=visible.feed(text)
                        if part:
                            output.append(part)
                            if on_text:on_text(part)
                    tail=visible.feed('',final=True)
                    if tail:
                        output.append(tail)
                        if on_text:on_text(tail)
            result=''.join(output)
            if not result.strip():raise NativeChatError('The service returned no visible response. Your draft is retained.')
            return result
        except NativeChatError:raise
        except Exception:
            raise NativeChatError('The chat response was not confirmed. Partial text and your draft are retained. No automatic retry was sent.')from None
