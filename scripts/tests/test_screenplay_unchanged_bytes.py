"""Actual writer functions against isolated synthetic manuscripts, never originals."""
import ast,hashlib,os,sys,threading
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import Mock
from fastapi import HTTPException

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'backend'))


class UnchangedWriterTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.directory=Path(self.temp.name)/'Fixture';self.directory.mkdir()
        self.path=self.directory/'screenplay.fountain'
        scope={'Path':Path,'HTTPException':HTTPException,'hashlib':hashlib,'os':os,'tempfile':tempfile,
               'Optional':__import__('typing').Optional,'WriteScreenplayPayload':object,
               '_PROJECT_STORE_LOCK':threading.RLock(),
               '_project_directory':lambda name:self.directory,'_require_idle_adaptation':lambda directory:None}
        tree=ast.parse((ROOT/'backend/routers/screenwriting_router.py').read_text(encoding='utf-8'))
        names={'_atomic_project_text','_screenplay_snapshot','_workflow_call','_require_screenplay_revision','_write_screenplay'}
        functions=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in names]
        exec(compile(ast.Module(body=functions,type_ignores=[]),'<actual-writer-functions>','exec'),scope)
        self.scope=scope

    def payload(self,content,*,explicit=False,revision=None):
        return SimpleNamespace(project_name='Fixture',content=content,
            expected_revision=revision or hashlib.sha256(self.path.read_bytes()).hexdigest(),
            preserve_unchanged_bytes=not explicit)

    def test_editor_newline_normalization_is_a_true_noop_preserving_bytes_revision_and_mtime(self):
        for raw in [b'TITLE\r\n\r\nINT. ROOM\r\nEnd\r\n',b'TITLE\nINT. ROOM\n',b'TITLE\rINT. ROOM\r',b'A\r\nB\nC\rEnd']:
            self.path.write_bytes(raw);mtime=self.path.stat().st_mtime_ns
            normalized=raw.decode().replace('\r\n','\n').replace('\r','\n')
            result=self.scope['_write_screenplay'](self.payload(normalized))
            self.assertEqual(self.path.read_bytes(),raw)
            self.assertEqual(self.path.stat().st_mtime_ns,mtime)
            self.assertEqual(result['revision'],hashlib.sha256(raw).hexdigest())
            self.assertTrue(result['unchanged'])

    def test_stale_revision_still_rejected_even_when_normalized_content_matches(self):
        self.path.write_bytes(b'A\r\nB\r\n')
        with self.assertRaises(HTTPException) as caught:self.scope['_write_screenplay'](self.payload('A\nB\n',revision='stale'))
        self.assertEqual(caught.exception.status_code,409)
        self.assertEqual(self.path.read_bytes(),b'A\r\nB\r\n')

    def test_real_text_edit_is_written_and_explicit_format_restore_is_exact(self):
        self.path.write_bytes(b'OLD\r\n')
        result=self.scope['_write_screenplay'](self.payload('NEW\n'))
        self.assertEqual(result['status'],'success');self.assertEqual(self.path.read_bytes(),b'NEW\n')
        result=self.scope['_write_screenplay'](self.payload('NEW\r\n',explicit=True))
        self.assertEqual(self.path.read_bytes(),b'NEW\r\n')
        self.assertEqual(result['revision'],hashlib.sha256(b'NEW\r\n').hexdigest())


if __name__=='__main__':unittest.main()
