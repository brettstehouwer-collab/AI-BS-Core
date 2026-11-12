"""Execute actual router preflight definitions against an isolated source project."""
import ast
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import threading
import unittest
from fastapi import HTTPException
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'backend'))
from security.firebase_auth import VerifiedFirebaseContext
from security.native_creative_handoff import CreativeHandoffs, HandoffDenied
from core.personal_memory_scope import current_memory_principal
from scripts.tests import test_chat_pdf_workflow as pdf


class ProjectPreflight(unittest.TestCase):
    def setUp(self):
        self.fixture=pdf.PdfWorkflowFixture()
        self.fixture._setupAsyncioRunner()
        self.addCleanup(self.fixture._tearDownAsyncioRunner)
        self.addCleanup(self.fixture.doCleanups)
        self.fixture._callSetUp()
        self.root=self.fixture.projects
        self.owner=pdf.OWNER
        source=self.fixture.stage()
        self.fixture.import_source(source,name='original')
        self.source=source['source_sha256']
        self.project=self.root/'original'
        self.body=(self.project/'screenplay.fountain').read_bytes()
        self.revision = hashlib.sha256(self.body).hexdigest()
        source = (Path(__file__).resolve().parents[2] / 'backend/routers/screenwriting_router.py').read_text(encoding='utf-8')
        names = {'_project_directory','_existing_project_directory','_screenplay_snapshot','_issue_native_creative_grant'}
        tree = ast.parse(source)
        definitions = [node for node in tree.body if isinstance(node,ast.FunctionDef) and node.name in names]
        self.assertEqual(len(definitions), 4)
        namespace = dict(Path=Path, HTTPException=HTTPException, hashlib=hashlib,
                         SCREENPLAY_ROOT=self.root, _PROJECT_STORE_LOCK=threading.RLock())
        exec(compile(ast.Module(body=definitions,type_ignores=[]), '<actual router preflight>', 'exec'), namespace)
        self.issue = namespace['_issue_native_creative_grant']
        self.context = VerifiedFirebaseContext(self.owner, 900)
        self.store = CreativeHandoffs(clock=lambda:500)
        self.invocation = object()
        self.before = {p.relative_to(self.project).as_posix():p.read_bytes() for p in self.project.rglob('*') if p.is_file()}

    def tearDown(self):
        self.assertEqual({p.relative_to(self.project).as_posix():p.read_bytes() for p in self.project.rglob('*') if p.is_file()}, self.before)
        self.assertIsNone(current_memory_principal())

    def call(self, **changes):
        options = dict(project_name='original', expected_revision=self.revision,
                       expected_source_sha256=self.source, grants=self.store)
        options.update(changes)
        return self.issue(self.context, self.invocation, 'b'*64, **options)

    def test_real_owner_fence_revision_and_scope_succeed_without_write(self):
        lease = self.store.redeem(self.call(), self.invocation)
        scope = self.store.authorize(lease, self.invocation, project='original', operation='read')
        self.assertEqual((scope.owner,scope.opening_revision,scope.source_sha256), (self.owner,self.revision,self.source))

    def test_foreign_owner_is_denied_by_existing_store_fence(self):
        self.context = VerifiedFirebaseContext('firebase:test:owner-b',900)
        with self.assertRaises(HTTPException) as error: self.call()
        self.assertEqual(error.exception.status_code,403)

    def test_stale_revision_and_wrong_source_never_issue(self):
        with self.assertRaises(HTTPException) as error: self.call(expected_revision='stale')
        self.assertEqual(error.exception.status_code,409)
        with self.assertRaises(HandoffDenied): self.call(expected_source_sha256='c'*64)
        self.assertEqual(self.store._grants,{})

    def test_path_escape_and_unverified_context_are_rejected(self):
        with self.assertRaises(HTTPException): self.call(project_name='../original')
        self.context = None
        with self.assertRaises(HandoffDenied): self.call()


if __name__ == '__main__': unittest.main()
