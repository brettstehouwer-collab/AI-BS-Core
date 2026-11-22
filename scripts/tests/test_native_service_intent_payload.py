"""Transport intent boundaries, with an explicit inert HTTP fixture only."""
import json
import unittest
import httpx
from native_studio.chat_service import NativeChatService


class NativeIntentPayloadTests(unittest.TestCase):
    def test_status_question_does_not_inherit_media_intent_from_history(self):
        requests = []
        def transport(request):
            requests.append(request)
            return httpx.Response(200, text='ComfyUI availability was not checked in this fixture.')
        service = NativeChatService(headers_provider=lambda: {'Authorization': 'Bearer fixture-only'},
                                    transport=httpx.MockTransport(transport))
        service.stream('is comfy UI running?', history=[('Generate a picture', 'Prior fixture reply')])
        self.assertEqual(len(requests), 1)
        self.assertEqual(requests[0].url.path, '/api/v1/hybrid-chat/stream')
        payload = json.loads(requests[0].content)
        self.assertEqual(payload.get('user_prompt'), 'is comfy UI running?')
        self.assertEqual(payload['prompt'], 'is comfy UI running?')
        self.assertEqual(payload['messages'][0]['content'], 'Generate a picture')

    def test_explicit_generation_remains_the_current_request(self):
        requests = []
        service = NativeChatService(headers_provider=lambda: {'Authorization': 'Bearer fixture-only'},
            transport=httpx.MockTransport(lambda request: (requests.append(request) or httpx.Response(200, text='Fixture accepted'))))
        service.stream('/image a fixture landscape')
        payload = json.loads(requests[0].content)
        self.assertEqual(payload.get('user_prompt'), '/image a fixture landscape')
        self.assertEqual(payload['prompt'], '/image a fixture landscape')


if __name__ == '__main__':
    unittest.main()
