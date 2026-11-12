"""Authenticated shared BS-Chat transport; no local model, tool or subprocess execution."""
from __future__ import annotations
import json
import re
import httpx
from native_studio.local_connection import LocalConnectionError, local_service_headers

ORIGIN='http://127.0.0.1:8080'
ROUTE='/api/v1/hybrid-chat/stream'

class NativeChatError(RuntimeError):
    pass


def safe_chat_failure_notice(message):
    """Display curated causes, never arbitrary worker/transport/server details."""
    if not isinstance(message, str):
        message = ''
    if message.startswith('NativeChatError: '):
        message = message[len('NativeChatError: '):]
    notices = {
        'The private chat connection is not ready. No API key entry is required.':
            'The private local connection could not be verified. Check that the local AI-BS service is running; no API key entry is required.',
        'The local chat service refused this connection. Your draft is retained.':
            'The local chat service refused authentication. Your draft is retained.',
        'The chat service timed out before confirming a response. Your draft is retained.':
            'The chat service timed out before confirming a response. Your draft is retained.',
        'The local chat service could not be reached. Your draft is retained.':
            'The local chat service could not be reached. Your draft is retained.',
        'The service returned no visible response. Your draft is retained.':
            'The service returned no visible response. Your draft is retained.',
        'The chat service could not complete the reply. Your draft is retained.':
            'The chat service could not complete the reply. Your draft is retained.',
        'The local model context limit was reached before it produced an answer. Your draft is retained.':
            'The local model context limit was reached before it produced an answer. Your draft is retained.',
        'The selected model is unavailable in the local service. Your draft is retained.':
            'The selected model is unavailable in the local service. Your draft is retained.',
        'The response exceeds the display limit. Partial text and your draft are retained.':
            'The response exceeds the display limit. Partial text and your draft are retained.',
    }
    if message in notices:
        return notices[message]
    if re.fullmatch(r'The chat service returned HTTP[1-5][0-9]{2}; no complete response was confirmed\.', message):
        return message
    return 'The response was not confirmed. Check local service status before trying again.'

class _VisibleStream:
    """Suppress split metadata comments without delaying ordinary visible text."""
    marker='<!--AI-BS-METADATA:'
    def __init__(self):
        self.pending='';self.hidden=False;self.body=''
        self.latest_primary=None;self.invalid_metadata=False
    def _metadata(self,text,*,complete=False):
        if len(self.body)+len(text)>65536:
            self.invalid_metadata=True;self.body='';return
        self.body+=text
        if complete:
            try:
                frame=json.loads(self.body)
                if not isinstance(frame,dict):raise ValueError('metadata shape')
                if frame.get('role')=='primary':
                    self.latest_primary={key:frame.get(key) for key in ('status','generation_verified','completion_verified','error_code')}
            except ValueError:
                self.invalid_metadata=True
            self.body=''
    def feed(self,text,final=False):
        self.pending+=text;visible=''
        while self.pending:
            if self.hidden:
                end=self.pending.find('-->')
                if end<0:
                    self._metadata(self.pending[:-2] if len(self.pending)>2 else '')
                    if final:self.invalid_metadata=True
                    self.pending=self.pending[-2:];break
                self._metadata(self.pending[:end],complete=True)
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
            if result.lstrip().startswith('Error in sovereign reasoning matrix:'):
                raise NativeChatError('The chat service could not complete the reply. Your draft is retained.')
            failure=result.strip()
            if failure == 'Local inference did not complete (context_budget_exceeded). No answer is claimed.':
                raise NativeChatError('The local model context limit was reached before it produced an answer. Your draft is retained.')
            if re.fullmatch(r'Local inference did not complete \([a-z0-9_]{1,64}\)\. No answer is claimed\.',failure):
                raise NativeChatError('The chat service could not complete the reply. Your draft is retained.')
            receipt=visible.latest_primary
            if receipt and receipt.get('error_code')=='provider_http_404':
                raise NativeChatError('The selected model is unavailable in the local service. Your draft is retained.')
            if visible.invalid_metadata or (receipt is not None and not (
                    receipt.get('status')=='completed' and receipt.get('generation_verified') is True
                    and receipt.get('completion_verified') is True)):
                raise NativeChatError('The chat service could not complete the reply. Your draft is retained.')
            return result
        except NativeChatError:raise
        except LocalConnectionError:
            raise NativeChatError('The private chat connection is not ready. No API key entry is required.')from None
        except httpx.TimeoutException:
            raise NativeChatError('The chat service timed out before confirming a response. Your draft is retained.')from None
        except httpx.ConnectError:
            raise NativeChatError('The local chat service could not be reached. Your draft is retained.')from None
        except Exception:
            raise NativeChatError('The chat response was not confirmed. Partial text and your draft are retained. No automatic retry was sent.')from None
