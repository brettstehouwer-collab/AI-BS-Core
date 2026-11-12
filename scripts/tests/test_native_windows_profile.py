"""Windows profile metadata/API contracts; no profile contents, GUI or services."""
from contextlib import contextmanager
import ctypes
from ctypes import wintypes
import hashlib
import os
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from native_studio.windows_profile import current_user_profile_directory, WindowsProfileError

HOME_KEYS = ('USERPROFILE', 'HOMEDRIVE', 'HOMEPATH', 'HOME')


@contextmanager
def home_environment(values):
    # Touch only these profile metadata variables in this test process, and
    # restore their previous presence/values. Never copy other auth variables.
    previous = {name: os.environ.get(name) for name in HOME_KEYS}
    try:
        for name in HOME_KEYS:
            if name in values:
                os.environ[name] = values[name]
            else:
                os.environ.pop(name, None)
        yield
    finally:
        for name, value in previous.items():
            if value is None:
                os.environ.pop(name, None)
            else:
                os.environ[name] = value


class FakeAPI:
    def __init__(self, text=r'C:\Users\Synthetic Profile', *, required=None, reported=None,
                 open_ok=True, token=88, first_ok=False, first_error=122,
                 second_ok=True, close_ok=True, raises=None):
        self.text = text
        self.required = self.units(text) if required is None else required
        self.reported = self.units(text) if reported is None else reported
        self.open_ok, self.token = open_ok, token
        self.first_ok, self.first_error = first_ok, first_error
        self.second_ok, self.close_ok, self.raises = second_ok, close_ok, raises
        self.calls = []; self.closed = []; self.error = 0

    @staticmethod
    def units(value): return len(value.encode('utf-16-le')) // 2 + 1

    def current_process(self):
        return ctypes.c_void_p(-1).value

    def open_process_token(self, process, access, output):
        self.calls.append(('open', process, access))
        if self.open_ok:
            ctypes.cast(output, ctypes.POINTER(wintypes.HANDLE)).contents.value = self.token
        return self.open_ok

    def clear_error(self): self.error = 0
    def last_error(self): return self.error

    def profile_directory(self, token, buffer, count):
        size = ctypes.cast(count, ctypes.POINTER(wintypes.DWORD)).contents
        self.calls.append(('size' if buffer is None else 'fill', token.value, size.value))
        if self.raises is not None:
            raise self.raises
        if buffer is None:
            self.error = self.first_error
            size.value = self.required
            return self.first_ok
        if self.second_ok:
            buffer.value = self.text
            size.value = self.reported
        return self.second_ok

    def close_handle(self, token):
        self.closed.append(token.value)
        return self.close_ok


@unittest.skipUnless(os.name == 'nt', 'Windows profile token metadata')
class RealProfileTests(unittest.TestCase):
    def test_current_process_profile_is_local_absolute_without_content_access(self):
        with patch.object(Path, 'home', side_effect=AssertionError('No home fallback')), \
             patch.object(Path, 'resolve', side_effect=AssertionError('No filesystem resolution')), \
             patch.object(Path, 'open', side_effect=AssertionError('No profile file IO')):
            profile = current_user_profile_directory()
        self.assertTrue(profile.is_absolute())
        self.assertTrue(len(profile.drive) == 2 and profile.drive[1] == ':')
        self.assertFalse(str(profile).startswith('\\\\'))

    def test_current_metadata_partition_matches_existing_home_when_available(self):
        try:
            previous = Path.home()
        except RuntimeError:
            self.skipTest('Legacy home metadata is unavailable in this runtime')
        fingerprint = lambda p: hashlib.sha256(str(p).casefold().encode('utf-8')).hexdigest()[:16]
        self.assertTrue(fingerprint(current_user_profile_directory()) == fingerprint(previous),
            'Profile partition differs; retain existing directories, do not auto-migrate')

    def test_missing_and_hostile_home_environment_do_not_change_current_token_profile(self):
        expected = current_user_profile_directory()
        for values in ({}, dict(USERPROFILE=r'Z:\Synthetic Hostile', HOMEDRIVE='Z:',
                               HOMEPATH=r'\Wrong Profile', HOME=r'Z:\Other')):
            with self.subTest(environment='missing' if not values else 'hostile'):
                with home_environment(values):
                    actual = current_user_profile_directory()
                self.assertTrue(str(actual) == str(expected), 'Environment changed token-owned metadata')

    def test_real_queries_leave_current_process_handle_count_unchanged(self):
        # Warm DLL bindings before the count and query only our own process.
        current_user_profile_directory()
        kernel = ctypes.WinDLL('kernel32.dll', use_last_error=True, winmode=0x800)
        kernel.GetCurrentProcess.argtypes = []; kernel.GetCurrentProcess.restype = wintypes.HANDLE
        kernel.GetProcessHandleCount.argtypes = [wintypes.HANDLE, ctypes.POINTER(wintypes.DWORD)]
        kernel.GetProcessHandleCount.restype = wintypes.BOOL
        def count():
            value = wintypes.DWORD()
            self.assertTrue(kernel.GetProcessHandleCount(kernel.GetCurrentProcess(), ctypes.byref(value)))
            return value.value
        before = count()
        for _ in range(3): current_user_profile_directory()
        self.assertEqual(count(), before)


@unittest.skipUnless(os.name == 'nt', 'Windows WCHAR/handle contract fixtures')
class ProfileContractTests(unittest.TestCase):
    def query(self, api):
        with patch('native_studio.windows_profile._WindowsAPI', return_value=api):
            return current_user_profile_directory()

    def refused(self, api, *, expected_closes=(88,)):
        with self.assertRaises(WindowsProfileError) as error:
            self.query(api)
        self.assertEqual(str(error.exception), 'The current Windows profile directory could not be confirmed.')
        self.assertEqual(api.closed, list(expected_closes))

    def test_own_process_query_only_then_exact_token_close(self):
        api = FakeAPI()
        self.assertEqual(str(self.query(api)), api.text)
        self.assertEqual(api.calls, [('open', ctypes.c_void_p(-1).value, 0x8),
            ('size', 88, 0), ('fill', 88, api.required)])
        self.assertEqual(api.closed, [88])
        self.assertNotIn(ctypes.c_void_p(-1).value, api.closed)

    def test_unicode_size_counts_utf16_code_units(self):
        api = FakeAPI('C:\\Users\\Synthetic \U0001f4bb')
        self.assertGreater(api.required, len(api.text)+1)
        self.assertTrue(str(self.query(api)) == api.text)
        self.assertEqual(api.closed, [88])

    def test_sizing_rejects_unbounded_or_nonprofile_lengths_before_allocation(self):
        for size in (0, 1, 32769, 0xffffffff):
            with self.subTest(size=size):
                api = FakeAPI(required=size)
                with patch('native_studio.windows_profile.ctypes.create_unicode_buffer',
                           side_effect=AssertionError('Invalid size must not allocate')):
                    self.refused(api)
                self.assertFalse(any(call[0] == 'fill' for call in api.calls))

    def test_wrong_sizing_error_or_unexpected_success_is_refused(self):
        for api in (FakeAPI(first_error=5), FakeAPI(first_ok=True)):
            self.refused(api)
            self.assertFalse(any(call[0] == 'fill' for call in api.calls))

    def test_fill_failure_and_inconsistent_reported_lengths_close_owned_token(self):
        for api in (FakeAPI(second_ok=False), FakeAPI(reported=0), FakeAPI(reported=1),
                    FakeAPI(reported=32768), FakeAPI(reported=3)):
            self.refused(api)

    def test_relative_unc_device_stream_control_and_dot_paths_are_refused(self):
        for text in ('relative', r'C:relative', r'\rooted', r'\\server\profile',
                     r'\\?\C:\Users\Synthetic', r'C:\Users\Bad:stream',
                     'C:\\Users\\Bad\nName', r'C:\Users\..\Other', r'C:\.\Users', '',
                     'C:\\Users\\Early\x00ignored'):
            with self.subTest(case='malformed metadata'):
                self.refused(FakeAPI(text=text))

    def test_open_failure_or_invalid_token_never_closes_process_pseudo_handle(self):
        for api in (FakeAPI(open_ok=False), FakeAPI(token=None),
                    FakeAPI(token=ctypes.c_void_p(-1).value)):
            self.refused(api, expected_closes=())
            self.assertEqual(len(api.calls), 1)

    def test_api_exception_after_open_is_sanitized_and_token_closed(self):
        api = FakeAPI(raises=OSError('synthetic-private-profile-marker'))
        self.refused(api)

    def test_binding_failure_is_sanitized_without_fallback(self):
        with patch('native_studio.windows_profile._WindowsAPI',
                   side_effect=OSError('synthetic-private-loader-marker')), \
             patch.object(Path, 'home', side_effect=AssertionError('No fallback')):
            with self.assertRaises(WindowsProfileError) as error:
                current_user_profile_directory()
        self.assertNotIn('private-loader', str(error.exception))

    def test_close_failure_is_not_reported_as_a_successful_profile_query(self):
        self.refused(FakeAPI(close_ok=False))

    def test_system_dll_bindings_are_secure_typed_and_query_only(self):
        from unittest.mock import MagicMock
        dlls = [MagicMock(), MagicMock(), MagicMock()]
        with patch('native_studio.windows_profile.ctypes.WinDLL', side_effect=dlls) as load:
            from native_studio.windows_profile import _WindowsAPI
            api = _WindowsAPI()
        self.assertEqual([call.args[0] for call in load.call_args_list],
            ['kernel32.dll', 'advapi32.dll', 'userenv.dll'])
        self.assertTrue(all(call.kwargs == dict(use_last_error=True, winmode=0x800)
            for call in load.call_args_list))
        self.assertEqual(api.open_process_token.argtypes,
            [wintypes.HANDLE, wintypes.DWORD, ctypes.POINTER(wintypes.HANDLE)])
        self.assertEqual(api.profile_directory.argtypes,
            [wintypes.HANDLE, wintypes.LPWSTR, ctypes.POINTER(wintypes.DWORD)])
        self.assertIs(api.profile_directory.restype, wintypes.BOOL)


if __name__ == '__main__': unittest.main()
