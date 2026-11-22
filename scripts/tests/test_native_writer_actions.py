"""Actual native doctor handler must use the loaded saved project, never canned success."""
import ast
import os
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import patch
from native_studio.screenplay_client import ScreenplayError
ROOT=Path(__file__).resolve().parents[2]

class NativeWriterActionTests(unittest.TestCase):
    def handler(self):
        tree=ast.parse((ROOT/'native_studio/screenwriting_view.py').read_text(encoding='utf-8'))
        cls=next(n for n in tree.body if isinstance(n,ast.ClassDef) and n.name=='ScreenwritingNativeView')
        method=next(n for n in cls.body if getattr(n,'name','')=='_run_script_doctor')
        scope={'ScreenplayError':ScreenplayError,'os':os}
        exec(compile(ast.Module(body=[method],type_ignores=[]),'<actual-doctor>','exec'),scope)
        return scope['_run_script_doctor']
    def state(self,response):
        calls=[];errors=[];statuses=[]
        def request(method,path,**kwargs):calls.append((method,path,kwargs));return response
        state=SimpleNamespace(_writer_busy=False,_draft=SimpleNamespace(project='Correct Loaded',dirty=False),
            _writer_client=SimpleNamespace(_json=request),_writer_error=errors.append,_writer_status=statuses.append)
        def run(work,success,failure):
            try:result=work()
            except Exception as error:failure(str(error))
            else:success(result)
        state._native_io=run
        return state,calls,errors,statuses
    def test_doctor_uses_auth_client_and_confirmed_current_project(self):
        state,calls,errors,statuses=self.state({'status':'success','project_name':'Correct Loaded','response':'Actual answer',
            'generation_verified':True,'receipt':{'complete':True},'sources':[{'source_revision':'r1'}]})
        with patch.dict(os.environ,{'PYTEST_CURRENT_TEST':'offline'}):self.handler()(state)
        self.assertEqual(calls[0][1],'/api/screenwriting/project-assistant/chat')
        self.assertEqual(calls[0][2]['json']['project_name'],'Correct Loaded')
        self.assertFalse(errors);self.assertTrue(statuses)
    def test_missing_or_dirty_project_never_dispatches_or_uses_a_default_story(self):
        for project,dirty in ((None,False),('Correct Loaded',True)):
            state,calls,errors,_=self.state({});state._draft.project=project;state._draft.dirty=dirty
            self.handler()(state);self.assertFalse(calls);self.assertTrue(errors)
    def test_no_index_or_false_model_success_is_a_visible_failure(self):
        for response in ({'status':'not_indexed','response':'No index'}, {'status':'success','response':'Canned','generation_verified':False}):
            state,calls,errors,statuses=self.state(response)
            with patch.dict(os.environ,{'PYTEST_CURRENT_TEST':'offline'}):self.handler()(state)
            self.assertTrue(errors);self.assertFalse(statuses)

if __name__=='__main__':unittest.main()
