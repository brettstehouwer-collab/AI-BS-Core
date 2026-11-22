"""Protected media references and exact bounded native downloads, with fixture bytes."""
import hashlib,os,tempfile,unittest
from pathlib import Path
import httpx

class NativeMediaTests(unittest.TestCase):
    def test_references_accept_only_owned_routes_and_no_error_objects(self):
        from native_studio.media_client import media_references,media_route
        good='/api/comfy/media?filename=fixture.mp4&type=output&subfolder=video'
        self.assertEqual(media_route('https://api.brettstehouwer.live'+good),good)
        self.assertEqual(media_references(f'[Download]({good})\n<video src="{good}"></video>'),[good])
        for bad in ['https://untrusted.invalid'+good,'http://127.0.0.1:8189/view?filename=a.mp4','file:///C:/private.mp4',good+'&token=private','/api/comfy/media?filename=..%2Fsecret.mp4','/api/comfy/media?filename=a.svg','/api/comfy/media?filename=a.mp4&type=input']:
            self.assertIsNone(media_route(bad),bad)
        self.assertEqual(media_references('{"status":"error","message":"'+good+'"}'),[])
    def test_download_is_exact_private_cached_once_and_rejects_fake_media(self):
        from native_studio.media_client import NativeMediaClient,NativeMediaError
        body=b'\x00\x00\x00\x18ftypisom'+b'fixture-video-payload'
        with tempfile.TemporaryDirectory()as temp:
            seen=[]
            def handler(req):seen.append(req);return httpx.Response(200,content=body,headers={'content-type':'video/mp4'})
            client=NativeMediaClient(root=Path(temp)/'media',headers_provider=lambda:{'Authorization':'Bearer fixture-only'},transport=httpx.MockTransport(handler),prepare_directory=lambda p:p.mkdir(parents=True,exist_ok=True))
            route='/api/comfy/media?filename=fixture.mp4&type=output'
            first=client.fetch(route);second=client.fetch(route)
            self.assertEqual(len(seen),1);self.assertEqual(first.path,second.path);self.assertEqual(first.path.read_bytes(),body)
            self.assertEqual(first.sha256,hashlib.sha256(body).hexdigest());self.assertEqual(first.kind,'video')
            self.assertEqual(str(seen[0].url),'http://127.0.0.1:8080'+route)
            for mime,content in [('video/mp4',b'{"status":"error"}'),('text/html',b'private server detail')]:
                client.transport=httpx.MockTransport(lambda req:httpx.Response(200,content=content,headers={'content-type':mime}))
                with self.assertRaises(NativeMediaError):client.fetch(route.replace('fixture','other'+str(len(content))))
    def test_redirect_auth_and_size_limit_do_not_publish_successful_file(self):
        from native_studio.media_client import NativeMediaClient,NativeMediaError
        with tempfile.TemporaryDirectory()as temp:
            for status in [302,401,403,500]:
                root=Path(temp)/str(status);seen=[]
                def handler(req):seen.append(req);return httpx.Response(status,headers={'location':'https://untrusted.invalid/'})
                client=NativeMediaClient(root=root,headers_provider=lambda:{'Authorization':'Bearer fixture'},transport=httpx.MockTransport(handler),prepare_directory=lambda p:p.mkdir(parents=True,exist_ok=True))
                with self.assertRaises(NativeMediaError):client.fetch('/api/comfy/media?filename=fixture.png')
                self.assertEqual(len(seen),1);self.assertEqual(list(root.glob('*.png')),[])
            client.transport=httpx.MockTransport(lambda req:httpx.Response(200,content=b'\x89PNG\r\n\x1a\n' + b'x'*100,headers={'content-type':'image/png'}));client.max_bytes=32
            with self.assertRaises(NativeMediaError):client.fetch('/api/comfy/media?filename=huge.png')

if __name__=='__main__':unittest.main()
