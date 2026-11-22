"""Private-record fixtures and offline signer validation; no user keys/cloud RPCs."""
import ast
import ctypes
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import traceback
import types
import unittest
from unittest.mock import Mock, patch

from backend.security import firebase_admin_runtime as runtime

ROOT = Path(__file__).resolve().parents[2]
RAW_READER = runtime._read_credential_blob


def fixture_info(**changes):
    info = {"type": "service_account", "project_id": runtime.PROJECT_ID,
            "token_uri": "https://oauth2.googleapis.com/token",
            "client_email": "fixture@fixture.iam.gserviceaccount.com",
            "private_key": "synthetic-not-a-key"}
    info.update(changes)
    return info


def blob(info):
    return json.dumps(info, ensure_ascii=False).encode("utf-8")


class FirebaseAdminRuntimeTests(unittest.TestCase):
    def setUp(self):
        self.previous_app = runtime._app
        runtime._app = None
        self.addCleanup(setattr, runtime, "_app", self.previous_app)
        self.environment = patch.dict(os.environ, {
            runtime.CREDENTIAL_TARGET_ENV: runtime.CREDENTIAL_TARGET,
            "FIREBASE_PROJECT_ID": runtime.PROJECT_ID,
        })
        self.environment.start()
        self.addCleanup(self.environment.stop)
        self.reader = patch.object(runtime, "_read_credential_blob", return_value=blob(fixture_info()))
        self.read = self.reader.start()
        self.addCleanup(self.reader.stop)
        self.certificate = Mock(return_value=types.SimpleNamespace(project_id=runtime.PROJECT_ID))
        self.sdk = types.ModuleType("firebase_admin")
        self.sdk.credentials = types.SimpleNamespace(Certificate=self.certificate)
        self.sdk.initialize_app = Mock(return_value=object())

    def fake_sdk(self):
        return patch.dict(sys.modules, {"firebase_admin": self.sdk})

    def test_import_is_inert(self):
        module = types.ModuleType("_inert_firebase_runtime_fixture")
        with patch.object(ctypes, "WinDLL", side_effect=AssertionError("vault touched")), self.fake_sdk():
            exec(compile(Path(runtime.__file__).read_text(), runtime.__file__, "exec"), module.__dict__)
        self.sdk.initialize_app.assert_not_called()
        self.certificate.assert_not_called()

    def test_named_app_explicit_credentials_options_and_cache(self):
        with self.fake_sdk():
            first = runtime.get_firebase_admin_app()
            self.assertIs(first, runtime.get_firebase_admin_app())
            status = runtime.firebase_admin_local_status()
        self.read.assert_called_once_with()
        self.certificate.assert_called_once_with(fixture_info())
        self.sdk.initialize_app.assert_called_once_with(
            self.certificate.return_value, {"projectId": runtime.PROJECT_ID}, name="aibs-admin-runtime")
        self.assertEqual(status, {"initialized": True, "app_name": "aibs-admin-runtime",
            "project_id": runtime.PROJECT_ID, "local_validation": "passed", "cloud_access_verified": False})
        self.assertNotIn("fixture@", json.dumps(status))
        self.assertNotIn("private_key", json.dumps(status))

    def test_invalid_environment_rejected_before_private_read_or_cache(self):
        for key, value, code in [
            (runtime.CREDENTIAL_TARGET_ENV, "", "not_configured"),
            (runtime.CREDENTIAL_TARGET_ENV, "unrelated-vault-target", "invalid_target"),
            ("FIREBASE_PROJECT_ID", "other-project", "project_mismatch"),
        ]:
            with self.subTest(key=key, code=code), patch.dict(os.environ, {key: value}):
                runtime._app = object()
                with self.assertRaises(runtime.FirebaseAdminRuntimeError) as error:
                    runtime.get_firebase_admin_app()
                self.assertEqual(error.exception.code, code)
        self.read.assert_not_called()

    def test_bad_private_records_fail_before_signer_or_app(self):
        bad = [b"", b"x" * 2560, "not bytes", b"\xff", b"{bad-json", b"[]", b"null",
            blob(fixture_info(type="authorized_user")), blob(fixture_info(project_id="other-project")),
            blob(fixture_info(token_uri="https://fixture.invalid/token")),
            blob(fixture_info(universe_domain="fixture.invalid"))]
        with self.fake_sdk():
            for value in bad:
                with self.subTest(kind=type(value).__name__, size=len(value)):
                    self.read.return_value = value
                    with self.assertRaises(runtime.FirebaseAdminRuntimeError):
                        runtime.get_firebase_admin_app()
        self.certificate.assert_not_called()
        self.sdk.initialize_app.assert_not_called()

    def test_vault_errors_are_redacted(self):
        self.read.side_effect = RuntimeError("synthetic-secret-value")
        with self.assertRaises(runtime.FirebaseAdminRuntimeError) as error:
            runtime.get_firebase_admin_app()
        self.assertEqual(error.exception.code, "credential_unavailable")
        self.assertNotIn("synthetic-secret-value", "".join(traceback.format_exception(error.exception)))

    def test_signer_and_app_errors_are_redacted_and_no_external_app_adopted(self):
        for failure in ["certificate", "existing_named_app"]:
            with self.subTest(failure=failure), self.fake_sdk():
                self.certificate.side_effect = ValueError("synthetic-secret-value") if failure == "certificate" else None
                self.sdk.initialize_app.side_effect = ValueError("synthetic-secret-value")
                with self.assertRaises(runtime.FirebaseAdminRuntimeError) as error:
                    runtime.get_firebase_admin_app()
                self.assertEqual(error.exception.code, "certificate_or_app_invalid")
                self.assertNotIn("synthetic-secret-value", "".join(traceback.format_exception(error.exception)))
                self.assertIsNone(runtime._app)

    def test_signer_project_mismatch_fails_before_initialization(self):
        self.certificate.return_value.project_id = "other-project"
        with self.fake_sdk(), self.assertRaises(runtime.FirebaseAdminRuntimeError) as error:
            runtime.get_firebase_admin_app()
        self.assertEqual(error.exception.code, "project_mismatch")
        self.sdk.initialize_app.assert_not_called()

    def fake_native_api(self, content=b"raw\x00utf8\xc3\xa9", size=None, null=False, success=True):
        buffer = (ctypes.c_ubyte * len(content)).from_buffer_copy(content)
        record = runtime._CredentialW()
        record.CredentialBlobSize = len(content) if size is None else size
        if not null:
            record.CredentialBlob = ctypes.cast(buffer, ctypes.POINTER(ctypes.c_ubyte))
        pointer = ctypes.pointer(record)
        def read(target, kind, flags, result):
            self.assertEqual((target, kind, flags), (runtime.CREDENTIAL_TARGET, 1, 0))
            if success:
                ctypes.cast(result, ctypes.POINTER(ctypes.POINTER(runtime._CredentialW)))[0] = pointer
            return success
        api = types.SimpleNamespace(CredReadW=Mock(side_effect=read), CredFree=Mock())
        # Closure captures the buffer/record for the lifetime of this fake API.
        api.keepalive = (buffer, record)
        return api

    def test_native_blob_read_preserves_exact_bytes_and_frees(self):
        content = b"raw\x00utf8\xc3\xa9"
        api = self.fake_native_api(content)
        with patch.object(ctypes, "WinDLL", return_value=api):
            self.assertEqual(RAW_READER(), content)
        api.CredReadW.assert_called_once()
        api.CredFree.assert_called_once()

    def test_native_bad_size_or_null_pointer_still_frees(self):
        for size, null in [(0, False), (2560, False), (10, True)]:
            with self.subTest(size=size, null=null):
                api = self.fake_native_api(size=size, null=null)
                with patch.object(ctypes, "WinDLL", return_value=api), self.assertRaises(runtime.FirebaseAdminRuntimeError):
                    RAW_READER()
                api.CredFree.assert_called_once()

    def test_native_failed_read_does_not_dereference_or_free(self):
        api = self.fake_native_api(success=False)
        with patch.object(ctypes, "WinDLL", return_value=api), self.assertRaises(runtime.FirebaseAdminRuntimeError):
            RAW_READER()
        api.CredFree.assert_not_called()

    def test_installed_sdk_parses_generated_signer_offline_without_adc(self):
        import firebase_admin
        from firebase_admin import credentials
        from cryptography.hazmat.primitives.asymmetric import rsa
        from cryptography.hazmat.primitives.serialization import Encoding, PrivateFormat, NoEncryption
        key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        info = fixture_info(private_key=key.private_bytes(Encoding.PEM, PrivateFormat.PKCS8, NoEncryption()).decode())
        self.assertLess(len(blob(info)), 2560)
        self.read.return_value = blob(info)
        with patch("requests.sessions.Session.request", side_effect=AssertionError("network forbidden")), \
             patch("google.auth.default", side_effect=AssertionError("ADC forbidden")), \
             patch.object(credentials, "ApplicationDefault", side_effect=AssertionError("ADC forbidden")):
            app = runtime.get_firebase_admin_app()
            try:
                self.assertEqual(app.name, runtime.APP_NAME)
                self.assertEqual(app.project_id, runtime.PROJECT_ID)
                self.assertIsNone(app.credential.get_credential().token)
                self.assertFalse(runtime.firebase_admin_local_status()["cloud_access_verified"])
            finally:
                firebase_admin.delete_app(app)


class RecoveryLauncherBoundaryTests(unittest.TestCase):
    def test_backend_only_reference_no_adc_or_frontend_secrets(self):
        launcher = ROOT / "runtime/recovery-tools-20261110/start_core.py"
        tree = ast.parse(launcher.read_text())
        prefix = []
        for node in tree.body:
            if isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id == "port" for t in node.targets):
                break
            prefix.append(node)
        code = compile(ast.Module(body=prefix, type_ignores=[]), str(launcher), "exec")
        fake_dotenv = types.ModuleType("dotenv")
        fake_dotenv.dotenv_values = lambda _: {"GOOGLE_APPLICATION_CREDENTIALS": "fixture-adc-path",
            runtime.CREDENTIAL_TARGET_ENV: "fixture-unrelated-target", "FIXTURE_PRIVATE_SECRET": "synthetic-secret"}
        fake_allowlist = types.ModuleType("firebase_runtime_config")
        fake_allowlist.apply_firebase_config = lambda env: 1
        for name in ["backend", "gateway", "frontend", "ollama"]:
            with self.subTest(service=name), patch.dict(os.environ, {"AI_BS_ADMIN_KEY": "synthetic-key"}, clear=True), \
                 patch.object(sys, "argv", [str(launcher), name]), \
                 patch.dict(sys.modules, {"dotenv": fake_dotenv, "firebase_runtime_config": fake_allowlist}), \
                 patch.object(subprocess, "Popen", side_effect=AssertionError("launch forbidden")):
                namespace = {"__name__": "_launcher_prefix_fixture"}
                exec(code, namespace)
                env = namespace["env"]
                self.assertNotIn("GOOGLE_APPLICATION_CREDENTIALS", env)
                if name == "backend":
                    self.assertEqual(env[runtime.CREDENTIAL_TARGET_ENV], runtime.CREDENTIAL_TARGET)
                else:
                    self.assertNotIn(runtime.CREDENTIAL_TARGET_ENV, env)
                if name in {"frontend", "ollama"}:
                    self.assertNotIn("AI_BS_ADMIN_KEY", env)
                    self.assertNotIn("FIXTURE_PRIVATE_SECRET", env)
                for key in ["AI_BS_BACKEND_MANAGE_DAEMONS", "AI_BS_BACKEND_BACKGROUND_ENABLED", "AI_BS_ALLOW_DESTRUCTIVE_ACTIONS"]:
                    self.assertEqual(env[key], "false")


if __name__ == "__main__":
    unittest.main()
