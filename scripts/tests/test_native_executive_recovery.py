import json,os,tempfile,unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
from native_studio.chat_recovery import ChatRecoveryStore,ChatRecoveryError


def state(text):return {'transcript':text,'draft':'unsent '+text,'scratchpad':'','history':[],'model':'fixture-model'}


class ExecutiveRecoveryNamespaceTests(unittest.TestCase):
    def test_cockpit_cannot_replace_existing_bs_chat_recovery(self):
        with tempfile.TemporaryDirectory()as temp,patch.dict(os.environ,{'LOCALAPPDATA':temp}),patch('native_studio.local_connection._current_identity',return_value=SimpleNamespace(owner_sid='S-1-5-21-100')):
            chat=ChatRecoveryStore();chat.save(state('chat'))
            before={p.name:p.read_bytes()for p in chat.root.glob('*.json')}
            cockpit=ChatRecoveryStore(namespace='executive');cockpit.save(state('executive'))
            self.assertNotEqual(chat.root,cockpit.root)
            self.assertEqual(chat.load().state,state('chat'))
            self.assertEqual(cockpit.load().state,state('executive'))
            self.assertEqual(before,{p.name:p.read_bytes()for p in chat.root.glob('*.json')})

    def test_namespace_rejects_paths_and_unbounded_names(self):
        for bad in ['../chat',r'a\b','',None,'a'*25]:
            with self.subTest(namespace=bad),self.assertRaises(ChatRecoveryError):
                ChatRecoveryStore(root=Path(tempfile.gettempdir())/'not-created-executive',namespace=bad)


if __name__=='__main__':unittest.main()
