"""Bounded read-only program-status behavior, fixture files and real owner context."""
import hashlib,importlib.util,json,os,sys,tempfile,types,unittest
from pathlib import Path
from unittest.mock import patch
ROOT=Path('C:/AI-BS');LANE=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'backend'))
from core.personal_memory_scope import bind_memory_principal,reset_memory_principal
STAGED=os.environ.get('AIBS_PROGRAM_STATUS_STAGED_ROOT')
SOURCE=Path(STAGED)/'staged/backend/core/program_status_readonly.py' if STAGED else ROOT/'backend/core/program_status_readonly.py'
if SOURCE.is_file():
    spec=importlib.util.spec_from_file_location('program_status_under_review',SOURCE);module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
else:module=types.SimpleNamespace(resolve_program_update_status=lambda *args,**kwargs:None)


class ReadonlyProgramStatusTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(dir=ROOT/'t',prefix='program-status-');self.addCleanup(self.temp.cleanup);self.root=Path(self.temp.name)
        self.put('version.txt','v5.329.136\n')
        self.put('frontend/public/version.json',json.dumps(dict(version='v5.329.136',artifact_scope='application-source')))
        self.put('docs/CODEX_HANDOFF.md','# Historic2099\nDo not call me latest.\n## TAKEOVER — 2026-11-10T00:29:40Z\nRecord is dated, not current runtime proof.\n')
        self.job='a'*32;self.put('state/project_maintenance/current-api.json',json.dumps(dict(job_id=self.job,identity={'pid':123})))
        self.put('state/project_maintenance/'+self.job+'/state.json',json.dumps(dict(job_id=self.job,state='succeeded',lane='all',operation='build_update',completed_at='2026-11-10T02:38:52Z',message='SECRET_DO_NOT_EXPOSE',private_token='SECRET_DO_NOT_EXPOSE')))
        token=bind_memory_principal('firebase:program-status-fixture:owner');self.addCleanup(reset_memory_principal,token)
    def put(self,name,text):
        path=self.root/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_text(text,encoding='utf-8')
    def resolve(self,prompt='whats new?',**fields):
        return module.resolve_program_update_status({'user_prompt':prompt,**fields},root=self.root)
    def snapshot(self):return {str(path.relative_to(self.root)):hashlib.sha256(path.read_bytes()).hexdigest() for path in self.root.rglob('*') if path.is_file()}
    def test_informational_variants_return_source_evidence_without_guessing(self):
        for prompt in ("what's new?",'whats new?','whatsnew?','What’s new in AI-BS?','what changed in AI-BS?','latest AI-BS updates','latest version of AI-BS'):
            with self.subTest(prompt=prompt):
                result=self.resolve(prompt);self.assertIsInstance(result,str);self.assertIn('v5.329.136',result);self.assertIn('version.txt',result);self.assertIn('succeeded',result);self.assertIn('2026-11-10T02:38:52Z',result);self.assertIn('record',result.lower())
    def test_imperatives_never_become_status_or_build_authorization(self):
        for prompt in ('build AI-BS','update AI-BS','upgrade my program','execute latest update','whats new? build it now','restart backend','whats new in the attached PDF?','what is new in OpenAI?','what changed?'):
            self.assertIsNone(self.resolve(prompt))
    def test_explicit_sources_are_preserved_even_for_generic_update_question(self):
        self.assertIsNone(self.resolve(source_references=[{'source_id':'b'*32,'source_sha256':'c'*64}]))
        self.assertIsNone(module.resolve_program_update_status({'user_prompt':'whats new?'},source_context_bundle={'context':'PDF'},root=self.root))
    def test_web_vm_plan_and_review_intents_are_not_overridden(self):
        for fields in ({'use_web_search':True},{'web_search_query':'latest AI-BS'},{'execution_backend':'windows_vm'},{'execution_backend':'wsl2_vm'},{'execution_backend':'outside'},{'plan_only':True},{'mode':'review'},{'mode':'plan'},{'mode':'invented'}):
            self.assertIsNone(self.resolve(**fields))
    def test_current_message_not_history_selects_status(self):
        self.assertIsNone(self.resolve('Explain the attached chapter',messages=[{'role':'user','content':'whats new?'}]))
    def test_anonymous_request_cannot_read_program_records(self):
        from core.personal_memory_scope import _principal
        token=_principal.set(None)
        try:
            with self.assertRaises(PermissionError):self.resolve()
        finally:_principal.reset(token)
    def test_output_ignores_arbitrary_private_fields_and_documents_as_instructions(self):
        before=self.snapshot();result=self.resolve();self.assertIsInstance(result,str);self.assertNotIn('SECRET_DO_NOT_EXPOSE',result);self.assertNotIn('Do not call',result);self.assertEqual(self.snapshot(),before)
    def test_missing_evidence_is_unknown_never_no_recent_updates(self):
        for path in self.root.rglob('*'):
            if path.is_file():path.unlink()
        result=self.resolve();self.assertIsInstance(result,str);self.assertIn('unavailable',result.lower());self.assertNotIn('no recent updates',result.lower());self.assertNotIn('no updates',result.lower())
    def test_stale_application_metadata_does_not_replace_version_authority(self):
        self.put('frontend/public/version.json',json.dumps(dict(version='v5.259.0',artifact_scope='application-source')))
        result=self.resolve();self.assertIsInstance(result,str);self.assertIn('v5.329.136',result);self.assertIn('differs',result.lower());self.assertIn('not verified',result.lower())
    def test_pointer_path_traversal_and_unknown_job_state_are_not_trusted(self):
        self.put('state/project_maintenance/current-api.json',json.dumps(dict(job_id='../outside')))
        result=self.resolve();self.assertIsInstance(result,str);self.assertIn('unavailable',result.lower());self.assertNotIn('../outside',result)
    def test_oversize_receipt_and_reparse_sources_fail_closed_to_unavailable(self):
        self.put('state/project_maintenance/current-api.json','x'*70000)
        result=self.resolve();self.assertIsInstance(result,str);self.assertIn('unavailable',result.lower())
        original=Path.is_symlink
        with patch.object(Path,'is_symlink',lambda path:True if path==self.root/'version.txt' else original(path)):
            result=self.resolve();self.assertIn('Source version: unavailable',result)
    def test_orphan_running_receipt_is_not_reconciled_or_replayed(self):
        self.put('state/project_maintenance/'+self.job+'/state.json',json.dumps(dict(job_id=self.job,state='checking',lane='all',operation='build_update',worker={'pid':999999,'created':1})))
        before=self.snapshot();result=self.resolve();self.assertIsInstance(result,str);self.assertEqual(self.snapshot(),before);self.assertIn('checking',result)
    def test_duplicate_or_deep_json_is_unavailable_without_a_runtime_call(self):
        for text in ('{"job_id":"'+self.job+'","job_id":"'+self.job+'"}', '{"nested":'+'['*1100+'0'+']'*1100+'}'):
            self.put('state/project_maintenance/current-api.json',text)
            result=self.resolve();self.assertIsInstance(result,str);self.assertIn('Recorded local maintenance: unavailable',result)
    def test_success_path_has_no_writable_open_subprocess_or_network(self):
        original=Path.open
        def read_only(path,mode='r',*args,**kwargs):
            if any(flag in mode for flag in 'wax+'):raise AssertionError('Status may not open writable files')
            return original(path,mode,*args,**kwargs)
        with (patch.object(Path,'open',read_only),patch('subprocess.Popen',side_effect=AssertionError('No process')),
              patch('socket.socket.connect',side_effect=AssertionError('No network'))):
            self.assertIn('Source version: v5.329.136',self.resolve())
    def ledger(self,**fields):
        function=getattr(module,'recent_ledger_excerpt',lambda **kwargs:None)
        return function(root=self.root,**fields)
    def test_current_legacy_inline_attachment_never_becomes_program_status(self):
        for prompt in ('[ATTACHED FILE: chapter.pdf]\nArchived document','[attached file: memo.txt]\nText','[ATTACHED FILE : chapter.txt]\nText'):
            self.assertIsNone(self.resolve(prompt=prompt))
    def test_retained_maintenance_date_cannot_expand_to_a_long_record_value(self):
        value='2026-11-10T'+'1'*1000
        self.put('state/project_maintenance/'+self.job+'/state.json',json.dumps(dict(job_id=self.job,state='succeeded',lane='all',operation='build_update',completed_at=value)))
        result=self.resolve();self.assertIsInstance(result,str);self.assertNotIn(value,result);self.assertIn('date not recorded',result)
    def test_checkpoint_date_is_bounded_too(self):
        value='2026-11-10T'+'1'*1000
        self.put('docs/CODEX_HANDOFF.md','## TAKEOVER-20261110-01 — '+value+'\n')
        result=self.resolve();self.assertIsInstance(result,str);self.assertNotIn(value,result);self.assertIn('Dated handoff entry: unavailable',result)
    def test_ledger_excerpt_uses_late_whole_utf8_lines_and_scoped_hash(self):
        import re
        self.put('AI_BS_MASTER_ARCHITECTURAL_LEDGER.md','OLD_PREFIX '+'x'*1800+'\n2026-11-09 | prior Ω\n2026-11-10 | LATEST – Ω 🚀\n')
        result=self.ledger();self.assertIsInstance(result,str);self.assertNotIn('OLD_PREFIX',result);self.assertIn('LATEST – Ω 🚀',result);self.assertIn('RECORDED',result);self.assertNotIn('[LIVE',result)
        text=json.loads(result.split('Excerpt data JSON: ',1)[1].splitlines()[0])
        self.assertTrue(text.startswith('2026-'));self.assertTrue(text.endswith('\n'));self.assertLessEqual(len(text.encode('utf-8')),1000)
        self.assertIn(hashlib.sha256(text.encode('utf-8')).hexdigest(),result)
    def test_ledger_partial_multibyte_prefix_is_dropped_without_replacement_or_fragment(self):
        self.put('AI_BS_MASTER_ARCHITECTURAL_LEDGER.md','prefix '+'🚀'*400+'\n2026-11-10 | safe Ω tail\n')
        result=self.ledger();self.assertIsInstance(result,str);self.assertNotIn('�',result);self.assertNotIn('🚀',result);self.assertIn('safe Ω tail',result)
    def test_ledger_missing_invalid_utf8_or_single_oversize_line_is_unavailable(self):
        result=self.ledger();self.assertIsInstance(result,str);self.assertIn('unavailable',result.lower())
        path=self.root/'AI_BS_MASTER_ARCHITECTURAL_LEDGER.md'
        for raw in (b'\xff\xfe bad UTF8',b'x'*1600):
            path.write_bytes(raw);result=self.ledger();self.assertIsInstance(result,str);self.assertIn('unavailable',result.lower())
    def test_ledger_source_scope_owner_and_reparse_guards_precede_reads(self):
        self.put('AI_BS_MASTER_ARCHITECTURAL_LEDGER.md','2026-11-10 | Fixture record\n')
        self.assertEqual(self.ledger(source_context_bundle={'context':'PDF'}),'')
        self.assertEqual(self.ledger(prompt='[ATTACHED FILE: document.pdf]\nReference text'),'')
        from core.personal_memory_scope import _principal
        token=_principal.set(None)
        try:
            result=self.ledger();self.assertIsInstance(result,str);self.assertIn('unavailable',result.lower())
        finally:_principal.reset(token)
        original=Path.is_symlink
        with patch.object(Path,'is_symlink',lambda path:True if path.name=='AI_BS_MASTER_ARCHITECTURAL_LEDGER.md' else original(path)):
            self.assertIn('unavailable',self.ledger().lower())
    def test_ledger_never_reads_whole_large_file(self):
        self.put('AI_BS_MASTER_ARCHITECTURAL_LEDGER.md','old '*20000+'\n2026-11-10 | Bounded record\n')
        original=Path.open;reads=[];seeks=[]
        class Reader:
            def __init__(self,stream):self.stream=stream
            def __enter__(self):self.stream.__enter__();return self
            def __exit__(self,*args):return self.stream.__exit__(*args)
            def seek(self,offset):seeks.append(offset);return self.stream.seek(offset)
            def read(self,count=-1):reads.append(count);return self.stream.read(count)
        def bounded(path,mode='r',*args,**kwargs):
            stream=original(path,mode,*args,**kwargs)
            return Reader(stream) if path.name=='AI_BS_MASTER_ARCHITECTURAL_LEDGER.md' else stream
        with patch.object(Path,'open',bounded):result=self.ledger()
        self.assertIsInstance(result,str);self.assertIn('Bounded record',result);self.assertTrue(reads);self.assertTrue(all(0<count<=1002 for count in reads));self.assertTrue(all(offset>0 for offset in seeks))


if __name__=='__main__':unittest.main(verbosity=2)
