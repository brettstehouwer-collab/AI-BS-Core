import json
from pathlib import Path
import tempfile
import unittest
from core.chat_film_store import FilmStore
from core.chat_film import command

class FilmSmoke(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.store=FilmStore(Path(self.temp.name))
        self.owner='firebase:test:alice'
        self.calls=[]
    def call(self,text,owner=None):
        return command(text,owner or self.owner,self.store,lambda *args:self.calls.append(args))
    def plan(self):
        self.call('film plan 45: Stage performance with plants')
        return self.store.get(self.owner)
    def test_01_plan_duration(self):
        p=self.plan();self.assertEqual(sum(s['seconds'] for s in p['shots']),45)
    def test_02_no_inference_when_planning(self):
        self.plan();self.assertEqual(self.calls,[])
    def test_03_raw_script_preserved(self):
        script='INT. STAGE\nADAM: Hello!'
        self.call('film plan 12: '+script);self.assertEqual(self.store.get(self.owner)['script'],script)
    def test_04_owner_isolation(self):
        p=self.plan()
        with self.assertRaises(ValueError):self.store.get('firebase:test:bob',p['id'])
    def test_05_identity_required(self):
        with self.assertRaises(PermissionError):command('film plan 5: test',None,self.store)
    def test_06_duration_limit(self):
        with self.assertRaises(ValueError):self.call('film plan 601: test')
    def test_07_edit_retains_script(self):
        p=self.plan();self.call('film shot 3: Close-up of plants')
        q=self.store.get(self.owner);self.assertEqual(q['script'],p['script']);self.assertEqual(q['shots'][2]['prompt'],'Close-up of plants')
    def test_08_cas(self):
        p=self.plan();q=dict(p);self.store.save(self.owner,p)
        with self.assertRaises(ValueError):self.store.save(self.owner,q)
    def test_09_restart_read(self):
        p=self.plan();self.assertEqual(FilmStore(self.store.root).get(self.owner),p)
    def test_10_render_authority(self):
        self.plan();self.call('film render');self.assertEqual(len(self.calls),1);self.assertTrue(self.store.get(self.owner)['run_requested'])
    def test_11_pause(self):
        self.plan();self.call('film render');self.call('film pause');self.assertFalse(self.store.get(self.owner)['run_requested'])
    def test_12_unknown_submission_no_replay(self):
        p=self.plan();p['shots'][0]['state']='submitting';self.store.save(self.owner,p)
        with self.assertRaises(ValueError):self.call('film resume')
        self.assertEqual(self.calls,[])
    def test_13_informational_not_action(self):
        self.assertIsNone(self.call('How do I create a 45 second video?'));self.assertFalse((self.store.root/'films.sqlite3').exists())
    def test_14_natural_request(self):
        self.call('Create a 45 second cinematic Wan2.1 video of a theatrical performance on a stage with plants')
        self.assertEqual(self.store.get(self.owner)['seconds'],45);self.assertEqual(self.calls,[])

if __name__=='__main__':unittest.main()
