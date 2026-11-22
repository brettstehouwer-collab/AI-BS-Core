"""Delivery boundaries for phone media; no models, originals or live services."""
import ast
import json
from pathlib import Path
import re
import sys
import tempfile
import unittest
import asyncio
from unittest.mock import patch
from types import SimpleNamespace
from typing import Dict, Any, Optional, Tuple
from urllib.parse import parse_qs, urlsplit

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'backend'))


class MobileMediaTests(unittest.TestCase):
    def test_pending_jobs_do_not_tell_the_user_to_submit_duplicates(self):
        from core.media_delivery import format_media_result
        text=format_media_result({'status':'queued','prompt_id':'fixture'},'cup')
        self.assertIn('processing',text)
        self.assertNotIn('retry',text.lower())

    def test_audio_output_and_special_filenames_have_round_trip_api_urls(self):
        from comfy_bridge import extract_output_media
        item=extract_output_media({'outputs':{'1':{'audio':[{'filename':'voice & music.wav','subfolder':'test folder','type':'output'}]}}})
        self.assertEqual(item['filename'],'voice & music.wav')
        self.assertEqual(parse_qs(urlsplit(item['image_url']).query)['filename'],['voice & music.wav'])

    def test_actual_stream_renderer_requires_success_and_uses_mobile_media_markdown(self):
        import core.media_delivery
        source=(ROOT/'backend/core/hybrid_reasoning_engine.py').read_text(encoding='utf-8')
        tree=ast.parse(source)
        function=next(n for n in tree.body if isinstance(n,ast.AsyncFunctionDef) and n.name=='stream_stehouwer_hybrid_response')
        for result in [{'status':'error','filename':'bad.png'}, {'status':'success','filename':'clip.webm'}]:
            async def thread_call(*args):return result
            async def yield_control(*args):await asyncio.sleep(0)
            bridge=SimpleNamespace(create_task=asyncio.create_task,to_thread=thread_call,sleep=yield_control)
            scope={'asyncio':bridge,'audit_prompt_safety':lambda p:(True,''),'detect_tool_intent':lambda p:('generate_comfy_video',{'prompt':p}),'is_coding_intent':lambda p:(False,p),'AsyncGenerator':__import__('typing').AsyncGenerator,'Optional':Optional,'json':json,'re':re}
            exec(compile(ast.Module(body=[function],type_ignores=[]),'<actual-stream-renderer>','exec'),scope)
            async def collect():return ''.join([chunk async for chunk in scope['stream_stehouwer_hybrid_response']('blue cup')])
            with patch.dict(sys.modules,{'tools.tool_registry':SimpleNamespace(ToolRegistry=SimpleNamespace(execute_tool=lambda *args:result))}):text=asyncio.run(collect())
            if result['status']=='error':self.assertNotIn('![',text);self.assertIn('did not complete',text)
            else:self.assertIn('![',text);self.assertNotIn('<video',text)

    def test_error_payload_paste_does_not_dispatch_a_second_generation(self):
        scope = dict(re=re, json=json, Dict=Dict, Any=Any, Optional=Optional, Tuple=Tuple)
        tree = ast.parse((ROOT/'backend/core/hybrid_reasoning_engine.py').read_text(encoding='utf-8'))
        funcs = [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name in {'clean_tool_prompt', 'detect_tool_intent'}]
        exec(compile(ast.Module(body=funcs, type_ignores=[]), '<actual-intent>', 'exec'), scope)
        error = {'status':'error', 'checkpoint_used':'sd_xl_base_1.0.safetensors', 'message':'ComfyUI execution error: Connection timeout to host http://127.0.0.1:8189/prompt'}
        for text in [json.dumps(error), '```json\n'+json.dumps(error)+'\n```']:
            self.assertEqual(scope['detect_tool_intent'](text), (None, None))
        self.assertEqual(scope['detect_tool_intent']('Create a photograph of a blue cup')[0], 'generate_comfy_image')

    def test_error_or_pending_never_becomes_a_successful_media_card(self):
        from core.media_delivery import format_media_result
        for result in [None, {'status':'error','filename':'bad.png','image_url':'/api/comfy/media?filename=bad.png','message':'timeout'}, {'status':'queued','filename':'bad.png'}, {'status':'success','image_url':json.dumps({'status':'error'})}, {'status':'success','filename':'../personal.db'}]:
            text = format_media_result(result, 'create image')
            self.assertNotIn('![', text)
            self.assertNotIn('Generated media', text)
            self.assertNotIn('Rendered in high resolution', text)

    def test_video_audio_images_use_encoded_api_links_without_invented_dimensions(self):
        from core.media_delivery import format_media_result
        for filename in ['cup & sun.png','clip.webm','voice.wav','model.glb']:
            text = format_media_result({'status':'success','filename':filename,'subfolder':'test folder'}, 'A [cup]')
            self.assertIn('Generated media', text)
            self.assertIn('/api/comfy/media?', text)
            self.assertNotIn('<video', text)
            self.assertNotIn('1024x1024', text)
            link = re.search(r'\]\(([^)]+)\)', text).group(1)
            self.assertEqual(parse_qs(urlsplit(link).query)['filename'], [filename])
            self.assertEqual(parse_qs(urlsplit(link).query)['subfolder'], ['test folder'])

    def test_media_paths_stay_inside_output_and_reject_redirects(self):
        from core.media_delivery import media_output_path
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)/'output';root.mkdir();(root/'ok.png').write_bytes(b'fixture')
            self.assertEqual(media_output_path(root,'ok.png',''), root/'ok.png')
            for filename, folder in [('../secret.db',''), ('ok.png','../other'), ('C:\\secret.png',''), ('ok.png','C:\\private'), ('x.png:secret','')]:
                with self.assertRaises(ValueError):media_output_path(root,filename,folder)


if __name__ == '__main__': unittest.main()
