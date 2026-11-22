"""Synthetic Windows/Git source capture, never generated-code execution."""
import copy
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import unittest
from unittest.mock import patch
import uuid

try:
    from core import coding_repository_snapshot as snapshot
except ImportError:
    snapshot = None


class RepositorySnapshotTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root = Path(os.environ['AIBS_SNAPSHOT_TEST_ROOT'])
        cls.root.mkdir()
        cls.template = cls.root / 'template'
        cls.template.mkdir()
        (cls.template / 'src').mkdir()
        (cls.template / 'tests').mkdir()
        (cls.template / 'src/app.py').write_bytes(b'value = 1\n')
        (cls.template / 'tests/test_app.py').write_bytes(b'# selected immutable test fixture; never executed\n')
        (cls.template / 'package.json').write_bytes(b'{"scripts":{"test":"do-not-execute"}}')
        (cls.template / 'package-lock.json').write_bytes(b'{"lockfileVersion":3}')
        cls.git(cls.template,'init','--template=')
        cls.git(cls.template,'add','--','src/app.py','tests/test_app.py','package.json','package-lock.json')
        cls.git(cls.template,'commit','-m','Synthetic source fixture')

    @staticmethod
    def git(repo,*argv):
        result = subprocess.run(['git','--no-optional-locks','-c','core.hooksPath=NUL','-c','core.fsmonitor=false',
            '-c','user.name=AI-BS Test','-c','user.email=fixture@example.invalid','-C',str(repo),*argv],capture_output=True,timeout=10)
        if result.returncode:
            raise AssertionError('Synthetic Git fixture operation failed')
        return result.stdout.decode('ascii').strip()

    def setUp(self):
        self.assertTrue(callable(getattr(snapshot,'capture_repository_snapshot',None)), 'Source capture module is not implemented')
        self.case = self.root / uuid.uuid4().hex
        self.repo = self.case / 'repo'
        shutil.copytree(self.template,self.repo)
        self.selected = [{'relative_path':'src/app.py','role':'editable'}, {'relative_path':'tests/test_app.py','role':'verification'}]

    def capture(self,selected=None,allowed=None,repo=None):
        return snapshot.capture_repository_snapshot(repo or self.repo, self.selected if selected is None else selected,
            allowed_roots=[self.case] if allowed is None else allowed)

    def test_exact_current_dirty_and_untracked_bytes_not_head(self):
        original_head = self.git(self.repo,'rev-parse','HEAD')
        current = b'from pathlib import Path\nPath("EXECUTED").write_text("unexpected")\nvalue = 2\n'
        (self.repo / 'src/app.py').write_bytes(current)
        (self.repo / 'src/new.js').write_bytes(b'export const value = 2;\n')
        self.selected.append({'relative_path':'src/new.js','role':'editable'})
        record,contents = self.capture()
        self.assertEqual(contents['src/app.py'],current)
        self.assertIn('src/new.js',contents)
        self.assertEqual(record['commit'],original_head)
        self.assertEqual(record['state'],'SNAPSHOT_ONLY')
        self.assertIs(record['authorized'],False)
        self.assertIs(record['executed'],False)
        self.assertFalse((self.repo / 'EXECUTED').exists())
        self.assertEqual(self.git(self.repo,'show','HEAD:src/app.py'),'value = 1')

    def test_only_selected_files_and_all_originals_preserved(self):
        (self.repo / '.env').write_bytes(b'UNSELECTED_PRIVATE_CANARY')
        (self.repo / 'screenplay.txt').write_bytes(b'UNSELECTED_DOCUMENT_CANARY')
        before = {p.relative_to(self.repo).as_posix():p.read_bytes() for p in self.repo.rglob('*') if p.is_file() and '.git' not in p.parts}
        record,contents = self.capture()
        self.assertEqual(set(contents),{'src/app.py','tests/test_app.py'})
        self.assertEqual(record['byte_count'],sum(map(len,contents.values())))
        self.assertEqual(before,{p.relative_to(self.repo).as_posix():p.read_bytes() for p in self.repo.rglob('*') if p.is_file() and '.git' not in p.parts})

    def test_utf8_bom_crlf_and_roles_hash_exact(self):
        value = '\ufeff# original café\r\nvalue = "雪"\r\n'.encode('utf-8')
        (self.repo / 'src/app.py').write_bytes(value)
        record,contents = self.capture()
        self.assertEqual(contents['src/app.py'],value)
        entry = next(r for r in record['files'] if r['relative_path'] == 'src/app.py')
        self.assertEqual(entry,dict(relative_path='src/app.py',role='editable',length=len(value),sha256=hashlib.sha256(value).hexdigest()))
        proof = dict(record)
        digest = proof.pop('snapshot_sha256')
        self.assertEqual(digest,hashlib.sha256(json.dumps(proof,sort_keys=True,separators=(',',':'),allow_nan=False).encode('utf-8')).hexdigest())

    def test_foreign_or_missing_trusted_scope_rejected_before_git(self):
        for roots in [[],[self.case / 'other'],[Path('relative')]]:
            with self.subTest(roots=str(roots)),patch.object(snapshot,'_git_head') as git:
                with self.assertRaises(ValueError): self.capture(allowed=roots)
                git.assert_not_called()

    def test_traversal_alias_and_credential_paths_rejected(self):
        for name in ['../outside.py','C:/outside.py','src\\app.py','src/./app.py','src/con.py','src/app.py:stream','.git/HEAD','.env','.env.local','.ssh/id','private.key','.npmrc','node_modules/x.js','src/app.py.','src/a\x00.py']:
            with self.subTest(name=name),patch.object(snapshot,'_git_head') as git:
                with self.assertRaises(ValueError): self.capture([{'relative_path':name,'role':'editable'}])
                git.assert_not_called()

    def test_collision_and_prefix_paths_rejected(self):
        for entries in [[{'relative_path':'src/app.py','role':'editable'},{'relative_path':'SRC/APP.PY','role':'dependency'}],
                        [{'relative_path':'src','role':'dependency'},{'relative_path':'src/app.py','role':'editable'}]]:
            with self.subTest(entries=entries),patch.object(snapshot,'_git_head') as git:
                with self.assertRaises(ValueError): self.capture(entries)
                git.assert_not_called()

    def test_count_roles_and_record_fields_are_strict(self):
        for entries in [[],self.selected*11,[{'relative_path':'src/app.py','role':'unknown'}],
                        [{'relative_path':'src/app.py','role':'editable','owner':'forged'}]]:
            with self.subTest(entries=len(entries)),patch.object(snapshot,'_git_head') as git:
                with self.assertRaises(ValueError): self.capture(entries)
                git.assert_not_called()

    def test_missing_file_and_directory_are_not_partial_success(self):
        for name in ['src/absent.py','src']:
            with self.subTest(name=name):
                with self.assertRaises((ValueError,OSError)): self.capture([{'relative_path':name,'role':'editable'}])

    def test_file_budget_rejects_before_reading_source(self):
        (self.repo / 'src/app.py').write_bytes(b'x'*2097153)
        with patch.object(snapshot,'_read_bytes') as read:
            with self.assertRaises(ValueError): self.capture()
            read.assert_not_called()

    def test_total_budget_rejects_before_reading_sources(self):
        entries = []
        for index in range(9):
            name = f'src/large{index}.py'
            (self.repo / name).write_bytes(b'x'*2097152)
            entries.append({'relative_path':name,'role':'editable'})
        with patch.object(snapshot,'_read_bytes') as read:
            with self.assertRaises(ValueError): self.capture(entries)
            read.assert_not_called()

    def test_recognized_credential_text_rejects_without_redaction(self):
        value = ('value = "' + 'sk-' + 'x'*32 + '"\n').encode('utf-8')
        (self.repo / 'src/app.py').write_bytes(value)
        with self.assertRaises(ValueError): self.capture()
        self.assertEqual((self.repo / 'src/app.py').read_bytes(),value)

    def test_current_environment_credential_values_are_excluded(self):
        value = 'synthetic-fixture-marker-008833'
        (self.repo / 'src/app.py').write_text('value = "' + value + '"',encoding='utf-8')
        with patch.dict(os.environ,{'AIBS_FIXTURE_TOKEN':value}):
            with self.assertRaises(ValueError): self.capture()

    def test_binary_or_invalid_utf8_rejected_unchanged(self):
        for value in [b'x\x00y',b'\xff\xfe\xfa']:
            (self.repo / 'src/app.py').write_bytes(value)
            with self.assertRaises(ValueError): self.capture()
            self.assertEqual((self.repo / 'src/app.py').read_bytes(),value)

    def test_hardlinked_source_rejected(self):
        original = self.case / 'outside.py'
        original.write_bytes(b'external = True\n')
        os.link(original,self.repo / 'src/linked.py')
        with self.assertRaises(ValueError): self.capture([{'relative_path':'src/linked.py','role':'editable'}])
        self.assertEqual(original.read_bytes(),b'external = True\n')

    def test_directory_junction_rejected(self):
        outside = self.case / 'outside'
        outside.mkdir()
        (outside / 'other.py').write_bytes(b'outside = True\n')
        result = subprocess.run(['cmd.exe','/d','/c','mklink','/J',str(self.repo / 'linked'),str(outside)],capture_output=True,timeout=5)
        self.assertEqual(result.returncode,0,'Synthetic junction fixture creation failed')
        with self.assertRaises(ValueError): self.capture([{'relative_path':'linked/other.py','role':'editable'}])

    def test_all_selected_sources_and_directories_locked_during_reads(self):
        original = snapshot._read_bytes
        observations = []
        def inspect(handle,length):
            with self.assertRaises(PermissionError):
                with (self.repo / 'tests/test_app.py').open('wb') as stream: stream.write(b'changed')
            with self.assertRaises(PermissionError): (self.repo / 'src').rename(self.repo / 'renamed')
            observations.append(True)
            return original(handle,length)
        with patch.object(snapshot,'_read_bytes',side_effect=inspect): self.capture()
        self.assertEqual(len(observations),2)
        # All handles are released afterward; ordinary subsequent user edits work.
        (self.repo / 'src/app.py').write_bytes(b'value = 9\n')

    def test_head_change_rejects_completed_bytes(self):
        actual = self.git(self.repo,'rev-parse','HEAD')
        with patch.object(snapshot,'_git_head',side_effect=[actual,'b'*40]):
            with self.assertRaises(ValueError): self.capture()

    def test_git_failure_diagnostics_are_not_exported(self):
        result = subprocess.CompletedProcess([],1,b'',b'private-diagnostic-marker')
        with patch.object(snapshot.subprocess,'run',return_value=result):
            with self.assertRaises(ValueError) as error: self.capture()
        self.assertNotIn('private-diagnostic-marker',str(error.exception))

    def test_non_repository_and_linked_metadata_not_followed(self):
        plain = self.case / 'plain'
        plain.mkdir()
        for metadata in [False,True]:
            if metadata: (plain / '.git').write_text('gitdir: ../repo/.git',encoding='utf-8')
            with self.assertRaises((OSError,ValueError)): self.capture(repo=plain)

    def test_selection_detached_and_existing_schema2_staging_accepts_bytes(self):
        self.selected.extend([{'relative_path':'package.json','role':'dependency'},{'relative_path':'package-lock.json','role':'dependency'}])
        record,contents = self.capture()
        self.selected[0]['role'] = 'dependency'
        self.assertEqual(record['files'][0]['role'],'editable')
        from core.coding_vm_inputs import validate_vm_inputs
        from core.coding_vm_staging import stage_vm_inputs
        manifest = dict(schema_version=2,task_id='1'*32,request_id='2'*32,attempt_id='3'*32,repository_id='4'*32,
            authorization_ref='5'*32,commit=record['commit'],base_image_sha256='6'*64,files=record['files'],
            checks=[{'check_id':'python','argv':['python','-m','unittest','tests.test_app']}],
            limits={'check_seconds':30,'total_seconds':180,'output_bytes':262144})
        self.assertEqual(validate_vm_inputs(manifest,contents,copy.deepcopy(manifest)),manifest)
        transfer = self.case / 'transfer'
        transfer.mkdir()
        staged = stage_vm_inputs(transfer,manifest,contents,copy.deepcopy(manifest))
        self.assertEqual(staged['state'],'STAGED')
        for name,value in contents.items(): self.assertEqual((Path(staged['directory']) / 'payload' / name).read_bytes(),value)

    def test_git_child_ignores_inherited_overrides_and_credentials(self):
        run = snapshot.subprocess.run
        commands = []
        marker = self.case / 'git_trace.txt'
        def inspect(argv,**kwargs):
            self.assertEqual(argv[0],r'C:\Program Files\Git\cmd\git.exe')
            self.assertIn('rev-parse',argv)
            self.assertIn('core.fsmonitor=false',argv)
            self.assertIn('core.hooksPath=NUL',argv)
            self.assertNotIn('GIT_DIR',kwargs['env'])
            self.assertNotIn('GIT_TRACE',kwargs['env'])
            self.assertNotIn('AI_BS_FIXTURE_KEY',kwargs['env'])
            self.assertNotIn('shell',kwargs)
            commands.append(True)
            return run(argv,**kwargs)
        with patch.dict(os.environ,{'GIT_DIR':str(self.case / 'wrong_git'),'GIT_TRACE':str(marker),'AI_BS_FIXTURE_KEY':'synthetic-credential-marker'}),patch.object(snapshot.subprocess,'run',side_effect=inspect):
            self.capture()
        self.assertEqual(len(commands),2)
        self.assertFalse(marker.exists())

    def test_preexisting_writer_blocks_capture_without_partial_reads(self):
        before = (self.repo / 'src/app.py').read_bytes()
        with (self.repo / 'src/app.py').open('r+b'),patch.object(snapshot,'_read_bytes') as read:
            with self.assertRaises(PermissionError): self.capture()
            read.assert_not_called()
        self.assertEqual((self.repo / 'src/app.py').read_bytes(),before)

    def test_malformed_root_and_unhashable_roles_are_validation_errors(self):
        for role in [[],{},None,True]:
            with self.subTest(role=repr(role)):
                with self.assertRaises(ValueError): self.capture([{'relative_path':'src/app.py','role':role}])
        for repo in [None,42,False]:
            with self.subTest(repo=repr(repo)):
                with self.assertRaises(ValueError): snapshot.capture_repository_snapshot(repo,self.selected,allowed_roots=[self.case])

