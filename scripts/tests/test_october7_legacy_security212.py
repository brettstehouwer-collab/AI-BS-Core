"""Legacy HTTP security regressions: AST/VM only, no listener, app import or devices."""
import ast
from email.message import Message
import hmac
from http.cookies import SimpleCookie
from http.server import BaseHTTPRequestHandler, HTTPServer, ThreadingHTTPServer
import io
import ipaddress
import json
import math
from pathlib import Path
import re
import secrets
import socket
import subprocess
import sys
import threading
from types import SimpleNamespace
import unittest
import urllib.parse
import uuid

ROOT = Path('C:/AI-BS')
SOURCE = ROOT/'October7_VocalStudio_DAW/source'
WORK = ROOT/'backups/october7_audit212/security/fixtures'
TOKEN = 'NONSECRET-ISOLATED-TEST-SESSION'


def definitions(app):
    tree = ast.parse((SOURCE/'october7_core.py').read_text(encoding='utf-8-sig'))
    namespace = dict(Path=Path, json=json, math=math, re=re, secrets=secrets,
        hmac=hmac, SimpleCookie=SimpleCookie, ipaddress=ipaddress, threading=threading,
        urllib=SimpleNamespace(parse=urllib.parse), socket=socket,
        sys=SimpleNamespace(executable=str(app/'fake.exe')), APP_DIR=app,
        BaseHTTPRequestHandler=BaseHTTPRequestHandler, HTTPServer=HTTPServer,
        ThreadingHTTPServer=ThreadingHTTPServer, print=lambda *a, **k: None)
    nodes = []
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.ClassDef)):
            nodes.append(node)
        elif isinstance(node, ast.Assign) and all(isinstance(t, ast.Name) for t in node.targets):
            try:
                value = ast.literal_eval(node.value)
            except (ValueError, TypeError):
                continue
            for target in node.targets:
                namespace[target.id] = value
    exec(compile(ast.Module(body=nodes, type_ignores=[]), 'legacy_server_AST_only', 'exec'), namespace)
    return namespace


NODE_VM = r'''
const fs=require('fs'),path=require('path'),vm=require('vm'),{Writable}=require('stream');
const [source,root,requestJSON]=process.argv.slice(1),query=JSON.parse(requestJSON);
let handler,bindings=[],finished=false;
const server={listen(...args){bindings.push(args.filter(a=>typeof a!=='function'));return this},on(){return this},setTimeout(){return this}};
const moduleFixture={exports:{}};
function controlledRequire(name){
 if(name==='http')return {createServer(fn){handler=fn;return server}};
 if(name==='child_process')return {exec(){throw Error('GUI/SHELL FORBIDDEN IN TEST')}};
 return require(name);
}
controlledRequire.main=moduleFixture;
const context={require:controlledRequire,module:moduleFixture,exports:moduleFixture.exports,
 __dirname:root,__filename:source,Buffer,URL,setTimeout,clearTimeout,process,
 console:{log(){},error(){}}};
function report(result){if(!finished){finished=true;console.log(JSON.stringify({...result,bindings}));}}
process.once('uncaughtException',e=>report({status:null,uncaught:e.name}));
try {vm.runInNewContext(fs.readFileSync(source,'utf8'),context,{filename:source});}
catch(e){report({status:null,uncaught:e.name});}
if(!finished){
 const headers={host:'127.0.0.1:3000',...(query.headers||{})};
 const req={url:query.path,method:query.method||'GET',headers,
  socket:{remoteAddress:query.remote||'127.0.0.1'}};
 let status=200,responseHeaders={},chunks=[];
 const res=new Writable({write(chunk,encoding,next){chunks.push(Buffer.from(chunk));next();}});
 res.writeHead=(code,h={})=>{status=code;Object.assign(responseHeaders,h);res.headersSent=true;return res};
 res.setHeader=(name,value)=>{responseHeaders[name]=value;};
 res.on('finish',()=>report({status,headers:responseHeaders,body:Buffer.concat(chunks).toString('utf8')}));
 try {const pending=handler(req,res);if(pending&&pending.catch)pending.catch(e=>report({status:null,uncaught:e.name}));}
 catch(e){report({status:null,uncaught:e.name});}
 setTimeout(()=>report({status:null,incomplete:true}),500);
}
'''


class LegacySecurity212Tests(unittest.TestCase):
    def setUp(self):
        self.base = WORK/('legacy_'+uuid.uuid4().hex)
        self.app = self.base/'app'
        self.app.mkdir(parents=True)
        (self.app/'VOICECOACH PROGRAM.html').write_text('<html>TEST ONLY</html>')
        (self.app/'sound.wav').write_bytes(b'0123456789')
        (self.app/'private.json').write_text('{"TEST_ONLY_PRIVATE":true}')
        (self.base/'outside.wav').write_bytes(b'OUTSIDE TEST FIXTURE')
        self.ns = definitions(self.app)
        self.calls = []
        self.ns.update(get_audio_devices_list=lambda: self.calls.append('devices') or [],
            get_hardware_audio_info=lambda: self.calls.append('hardware') or {},
            get_cuda_vram_telemetry=lambda: {}, get_ai_service_health=lambda: {},
            transcribe_telemetry_to_auto_notes=lambda *a: [],
            write_standard_midi=lambda *a, **k: self.calls.append('midi'),
            separate_stems_backend=lambda *a: self.calls.append('stems') or {'success':True},
            generate_ai_music_backend=lambda *a, **k: self.calls.append('music') or {},
            lyric_assistant_backend=lambda *a: self.calls.append('lyrics') or {},
            HAS_CALIBRATOR=True, LoopbackCalibrator=lambda **k: SimpleNamespace(run_calibration=lambda: self.calls.append('calibration') or {}))

    def request(self, path='/', *, method='GET', headers=None, body=b'', authenticated=False, remote='127.0.0.1'):
        handler = object.__new__(self.ns['StudioCoreRequestHandler'])
        message = Message()
        values = {'Host':'127.0.0.1:3000'}
        if authenticated:
            values.update(Cookie='oct7_session='+TOKEN, Origin='http://127.0.0.1:3000')
        values.update(headers or {})
        for name, value in values.items(): message[name]=str(value)
        self.status = None
        self.response_headers = {}
        handler.path,handler.command,handler.headers = path,method,message
        handler.server=SimpleNamespace(server_port=3000,server_address=('127.0.0.1',3000),session_token=TOKEN,api_slots=threading.BoundedSemaphore(2))
        handler.client_address=(remote,12345)
        handler.rfile,handler.wfile=io.BytesIO(body),io.BytesIO()
        handler.close_connection=False
        def status(code,*args): self.status=code
        def send_error(code,*args,**kwargs): self.status=code
        handler.send_response=status
        handler.send_error=send_error
        handler.send_header=lambda key,value: self.response_headers.__setitem__(key,value)
        handler.end_headers=lambda: None
        getattr(handler,'do_'+method)()
        return self.status,handler.wfile.getvalue()

    def test_python_parent_traversal_denied(self):
        self.request('/../outside.wav')
        self.assertEqual(self.status,403)

    def test_python_encoded_drive_and_backslash_paths_denied(self):
        drive_path='/'+urllib.parse.quote(str(self.base/'outside.wav'),safe=':')
        for path in ('/..%5coutside.wav',drive_path,'/%2e%2e/outside.wav'):
            with self.subTest(path=path):
                self.request(path)
                self.assertEqual(self.status,403)

    def test_python_private_file_type_denied(self):
        self.request('/private.json')
        self.assertEqual(self.status,403)

    def test_python_dns_rebinding_and_remote_peer_denied(self):
        for headers,remote in (({'Host':'attacker.example:3000'},'127.0.0.1'),({},'192.0.2.2')):
            self.request(headers=headers,remote=remote)
            self.assertEqual(self.status,403)

    def test_python_foreign_origin_cannot_query_hardware(self):
        self.request('/api/audio_devices',headers={'Origin':'https://attacker.example'})
        self.assertEqual(self.status,403)
        self.assertEqual(self.calls,[])

    def test_python_session_required_before_calibration(self):
        self.request('/api/calibrate_latency')
        self.assertEqual(self.status,401)
        self.assertEqual(self.calls,[])

    def test_python_same_origin_session_allows_explicit_api(self):
        self.request('/api/audio_devices',authenticated=True)
        self.assertEqual(self.status,200)
        self.assertEqual(self.calls,['devices'])

    def test_python_studio_page_sets_private_strict_session_cookie(self):
        self.request()
        cookie=self.response_headers.get('Set-Cookie','')
        self.assertIn('oct7_session=',cookie)
        self.assertIn('HttpOnly',cookie)
        self.assertIn('SameSite=Strict',cookie)
        self.assertNotEqual(self.response_headers.get('Access-Control-Allow-Origin'),'*')

    def test_python_bad_content_length_is_controlled(self):
        for value in ('bogus','-1'):
            with self.subTest(value=value):
                try:
                    self.request('/api/process_auto_notes',method='POST',authenticated=True,
                        headers={'Content-Length':value,'Content-Type':'application/json'},body=b'{}')
                except Exception as exc:
                    self.fail('Malformed body framing escaped handler: '+type(exc).__name__)
                self.assertEqual(self.status,400)
        self.assertEqual(self.calls,[])

    def test_python_oversized_body_denied_before_backend(self):
        self.request('/api/process_auto_notes',method='POST',authenticated=True,
            headers={'Content-Length':4*1024*1024,'Content-Type':'application/json'},body=b'{}')
        self.assertEqual(self.status,413)
        self.assertEqual(self.calls,[])

    def test_python_json_must_be_object(self):
        self.request('/api/process_auto_notes',method='POST',authenticated=True,
            headers={'Content-Length':2,'Content-Type':'application/json'},body=b'[]')
        self.assertEqual(self.status,400)
        self.assertEqual(self.calls,[])

    def test_python_stem_filename_cannot_escape(self):
        data=json.dumps({'filename':'../outside.wav'}).encode()
        self.request('/api/split_stems',method='POST',authenticated=True,
            headers={'Content-Length':len(data),'Content-Type':'application/json'},body=data)
        self.assertEqual(self.status,400)
        self.assertEqual(self.calls,[])

    def test_python_ranges_return_416_or_correct_suffix(self):
        self.request('/sound.wav',headers={'Range':'bytes=999-1000'})
        self.assertEqual(self.status,416)
        status,body=self.request('/sound.wav',headers={'Range':'bytes=-3'})
        self.assertEqual((status,body),(206,b'789'))

    def test_python_port_probe_and_server_bind_loopback_only(self):
        bindings=[]
        class Probe:
            def __enter__(self): return self
            def __exit__(self,*args): pass
            def bind(self,address): bindings.append(address)
        self.ns['socket']=SimpleNamespace(AF_INET=1,SOCK_STREAM=1,socket=lambda *a:Probe())
        self.ns['find_available_port']()
        class Server:
            def __init__(self,address,handler): bindings.append(address)
            def serve_forever(self): pass
        self.ns.update(HTTPServer=Server,ThreadingHTTPServer=Server,is_admin=lambda:False)
        self.ns['start_server'](3000)
        self.assertTrue(bindings)
        self.assertTrue(all(address[0]=='127.0.0.1' for address in bindings),bindings)

    def node(self, path='/', **kwargs):
        result=subprocess.run(['node','-e',NODE_VM,str(SOURCE/'server.js'),str(self.app),json.dumps({'path':path,**kwargs})],capture_output=True,text=True,timeout=5)
        self.assertEqual(result.returncode,0,result.stderr[-200:])
        return json.loads(result.stdout.strip())

    def test_node_sibling_prefix_traversal_denied(self):
        sibling=self.base/'app_private'
        sibling.mkdir()
        (sibling/'outside.wav').write_bytes(b'PRIVATE TEST FIXTURE')
        result=self.node('/../app_private/outside.wav')
        self.assertEqual(result['status'],403,result)

    def test_node_dns_rebinding_and_foreign_origin_denied(self):
        for headers in ({'host':'attacker.example:3000'},{'origin':'https://attacker.example'}):
            result=self.node(headers=headers)
            self.assertEqual(result['status'],403,result)

    def test_node_malformed_uri_and_range_are_controlled(self):
        self.assertEqual(self.node('/%broken')['status'],400)
        result=self.node('/sound.wav',headers={'range':'bytes=broken'})
        self.assertEqual(result['status'],416,result)

    def test_node_private_file_denied_and_valid_suffix_supported(self):
        self.assertEqual(self.node('/private.json')['status'],403)
        result=self.node('/sound.wav',headers={'range':'bytes=-3'})
        self.assertEqual((result['status'],result['body']),(206,'789'),result)

    def test_node_declares_loopback_binding(self):
        result=self.node()
        self.assertTrue(result['bindings'])
        self.assertTrue(all(len(binding)>1 and binding[1]=='127.0.0.1' for binding in result['bindings']),result['bindings'])


if __name__=='__main__': unittest.main()
