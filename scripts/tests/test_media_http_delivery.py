"""Exercise the actual media handler with a temporary synthetic output store."""
import ast
from pathlib import Path
import sys
import tempfile
import unittest
from fastapi import FastAPI
from fastapi.testclient import TestClient

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'backend'))

class MediaHttpTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.store=Path(self.temp.name)
        for ext in ['png','webm','wav']:
            p=self.store/'output'/('test.'+ext);p.parent.mkdir(exist_ok=True);p.write_bytes(b'0123456789')
        tree=ast.parse((ROOT/'backend/AI_BS_Backend.py').read_text(encoding='utf-8'))
        function=next(n for n in tree.body if isinstance(n,ast.AsyncFunctionDef) and n.name=='root_proxy_comfy_media')
        function.decorator_list=[]
        store=str(self.store)
        class StoreLocation(ast.NodeTransformer):
            def visit_Constant(self,node):
                if isinstance(node.value,str) and node.value==r'C:\AI-BS\ComfyUI\ComfyUI':return ast.copy_location(ast.Constant(value=store),node)
                return node
        function=StoreLocation().visit(function);scope={}
        exec(compile(ast.fix_missing_locations(ast.Module(body=[function],type_ignores=[])),'<actual-media-handler>','exec'),scope)
        app=FastAPI();app.get('/media')(scope['root_proxy_comfy_media']);self.client=TestClient(app)

    def test_images_audio_video_have_real_mime_and_private_response_headers(self):
        for ext,kind in [('png','image/'),('webm','video/'),('wav','audio/')]:
            response=self.client.get('/media',params={'filename':'test.'+ext})
            self.assertEqual(response.status_code,200);self.assertEqual(response.content,b'0123456789')
            self.assertTrue(response.headers['content-type'].startswith(kind));self.assertEqual(response.headers['cache-control'],'private, no-store')
            self.assertEqual(response.headers['x-content-type-options'],'nosniff')

    def test_video_supports_byte_ranges_and_missing_files_are_not_successes(self):
        response=self.client.get('/media',params={'filename':'test.webm'},headers={'Range':'bytes=2-5'})
        self.assertEqual(response.status_code,206);self.assertEqual(response.content,b'2345')
        self.assertEqual(self.client.get('/media',params={'filename':'missing.png'}).status_code,404)

    def test_traversal_and_non_media_files_are_refused(self):
        for query in [{'filename':'../secret.db'},{'filename':'test.png','subfolder':'../../private'},{'filename':'test.png','type':'private'},{'filename':'code.py'}]:
            self.assertEqual(self.client.get('/media',params=query).status_code,400)

if __name__=='__main__':unittest.main()
