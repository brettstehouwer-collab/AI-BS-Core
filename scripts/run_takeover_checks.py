"""Run reviewed synthetic takeover checks with retained output and fresh fixtures.

This runner does not discover arbitrary tests, import the application, seed the
real registry or contact a provider. The broad backend fixture modules each get
their own process and retained synthetic roots.
"""
import argparse
import datetime
import json
import logging
import os
from pathlib import Path
import subprocess
import sys
import unittest
import uuid

ROOT = Path(__file__).resolve().parents[1]
CORE = [
    'scripts.tests.test_specialist_takeover', 'scripts.tests.test_takeover_models',
    'scripts.tests.test_immutable_publishing_takeover',
    'scripts.tests.test_program_builder_takeover',
    'scripts.tests.test_bs_chat_openai', 'scripts.tests.test_ai_provider_environment',
    'scripts.tests.test_native_shared_chat', 'scripts.tests.test_contained_file_access',
    'scripts.tests.test_historical_reference_context', 'scripts.tests.test_owned_rag_sources',
    'scripts.tests.test_host_document_lookup', 'scripts.tests.test_tool_call_contract',
    'scripts.tests.test_project_maintenance', 'scripts.tests.test_viewport_publication_takeover',
    # The supplied private PDF has a separate explicitly selected qualification;
    # ordinary in-app builds use synthetic preservation cases only.
    'scripts.tests.test_screenplay_pdf.SyntheticScreenplayPdfTests',
    'scripts.tests.test_pdf_text_source',
    'scripts.tests.test_chat_pdf_workflow',
    'scripts.tests.test_native_screenplay_workflow',
    'scripts.tests.test_screenplay_professional.ProfessionalScreenplayTests',
    'scripts.tests.test_attached_source_context',
    'scripts.tests.test_novelizer_takeover.NovelizerTakeoverTests',
    'scripts.tests.test_novelizer_context_budget',
    'scripts.tests.test_project_rag_takeover.ProjectRagTakeoverTests',
    'scripts.tests.test_project_rag_callers.ProjectRagCallerTests',
    'scripts.tests.test_project_rag_callers.AudioTranscriptCallerTests',
    'scripts.tests.test_screenwriting_audio_owner_handoff.AudioOwnerHandoffTests',
    'scripts.tests.test_fdx_source_documents',
    'scripts.tests.test_fdx_source_workflow',
    'scripts.tests.test_native_rich_writer',
    'scripts.tests.test_native_rich_routes.NativeRichRouteTests',
    'scripts.tests.test_native_rich_qt_ranges',
    'scripts.tests.test_native_pdf_handoff',
    'scripts.tests.test_native_creative_handoff',
    'scripts.tests.test_native_writer_actions',
    'scripts.tests.test_native_novelizer_assistant.NativeNovelizerAssistantTests',
    'scripts.tests.test_local_chat_inference',
    'scripts.tests.test_local_pipeline',
    'scripts.tests.test_hybrid_route_registration',
    'scripts.tests.test_batch_runtime',
    'scripts.tests.test_inline_document_scope',
    'scripts.tests.test_project_rag_runtime',
    'scripts.tests.test_project_rag_failure_evidence',
    'scripts.tests.test_quoted_rag_relevance',
    'scripts.tests.test_program_status_readonly',
    'scripts.tests.test_program_status_integration',
]
RETAINED = ['test_http_fallback', 'test_owned_vault',
            'test_personal_memory_authority', 'test_repository_snapshot']


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--group', choices=['core', 'retained-backend'], default='core')
    parser.add_argument('--output-root', type=Path, default=ROOT / 'backups/antigravity_takeover_20261109T190150Z/checks')
    args = parser.parse_args()
    name = datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%SZ') + '-' + uuid.uuid4().hex[:8]
    output = args.output_root.resolve() / name
    output.mkdir(parents=True)
    summary = dict(group=args.group, output=str(output), provider_requests='mocked-only', runs=[])
    if args.group == 'core':
        if any(os.environ.get(name) for name in ('AIBS_LOCAL_CHAT_STAGE_ROOT', 'AIBS_HYBRID_ROUTE_TEST_STAGED_ROOT',
                                                'AIBS_PROJECT_RAG_STAGE_ROOT', 'AIBS_PROGRAM_STATUS_STAGED_ROOT', 'AIBS_QUOTED_RAG_STAGE_ROOT')):
            raise RuntimeError('Fixed current-source checks cannot use a checkpoint source override.')
        sys.path.insert(0, str(ROOT))
        logging.disable(logging.INFO)
        suite = unittest.defaultTestLoader.loadTestsFromNames(CORE)
        with (output / 'unittest.log').open('w', encoding='utf-8') as log:
            result = unittest.TextTestRunner(stream=log, verbosity=2).run(suite)
        summary['runs'].append(dict(modules=CORE, tests=result.testsRun,
                                    failures=len(result.failures), errors=len(result.errors),
                                    skipped=len(result.skipped), passed=result.wasSuccessful()))
    else:
        for module in RETAINED:
            fixture = ROOT / 'scratch/takeover-fixtures' / name / module
            fixture.mkdir(parents=True)
            retained_log = output / module
            retained_log.mkdir()
            env = os.environ.copy()
            env['PYTHONPATH'] = os.pathsep.join([str(ROOT / 'backend'), str(ROOT / 'backend/tests')])
            for key, directory in [('AIBS_FALLBACK_TEST_OUTPUT','fallback'), ('AIBS_OWNED_TEST_OUTPUT','owned'),
                                   ('AIBS_PERSONAL_TEST_OUTPUT','personal'), ('AIBS_SNAPSHOT_TEST_ROOT','snapshot')]:
                # Snapshot setUpClass creates its root; keep this leaf absent.
                env[key] = str(fixture / directory)
            command = [sys.executable, '-B', '-m', 'unittest', module, '-v']
            try:
                result = subprocess.run(command, cwd=ROOT, env=env, capture_output=True,
                                        text=True, encoding='utf-8', errors='replace', timeout=120)
                text = result.stdout + result.stderr
                code = result.returncode
            except subprocess.TimeoutExpired as error:
                def decoded(value): return value.decode('utf-8', 'replace') if isinstance(value, bytes) else value or ''
                text, code = decoded(error.stdout) + decoded(error.stderr) + '\nFixture runner timed out.', -1
            (retained_log / 'unittest.log').write_text(text, encoding='utf-8')
            summary['runs'].append(dict(module=module, fixture_root=str(fixture), exit_code=code, passed=code == 0))
    summary['passed'] = all(row['passed'] for row in summary['runs'])
    (output / 'results.json').write_text(json.dumps(summary, indent=2), encoding='utf-8')
    print(json.dumps(summary, indent=2))
    return 0 if summary['passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
