"""Retained synthetic verification runs and the actual viewport health state machine.

No engine build, GPU process, SDK publication, or real project save is executed.
The fake CMake executable only exercises the real PowerShell orchestration.
"""
import ctypes
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import unittest
import uuid


SOURCE = Path(__file__).resolve().parents[1]


class VerificationTakeoverTests(unittest.TestCase):
    def setUp(self):
        retained = os.environ.get('AIBS_ENGINE_TAKEOVER_TEST_ROOT', str(SOURCE / 'out/takeover-test-evidence'))
        self.root = Path(retained) / uuid.uuid4().hex
        self.root.mkdir(parents=True)

    def fixture(self):
        root = self.root / 'engine'
        (root / 'scripts').mkdir(parents=True)
        (root / 'out/windows-msvc').mkdir(parents=True)
        shutil.copyfile(SOURCE / 'scripts/verify.ps1', root / 'scripts/verify.ps1')
        (root / 'CMakeLists.txt').write_text('project(AIBSEngine VERSION 0.17.4 LANGUAGES C CXX)\n')
        # Real native fixtures need a short base. Every run itself remains a
        # freshly allocated private directory, including when CMake is synthetic.
        evidence = SOURCE / 'out'
        evidence.mkdir(exist_ok=True)
        (root / 'out/windows-msvc/CMakeCache.txt').write_text(
            'AIBS_EVIDENCE_ROOT:PATH=' + evidence.as_posix() + '\n')
        (root / 'out/verification.log').write_text('RETAINED_PREVIOUS_LOG\n')
        previous = root / 'out/validation-Debug'
        previous.mkdir()
        (previous / 'previous.txt').write_text('RETAINED_VALIDATION')
        fake = self.root / 'fake python'
        fake.mkdir()
        runner = fake / 'fake_python.py'
        runner.write_text('''import json,os,sys
from pathlib import Path
with Path(os.environ['FAKE_COMMAND_LOG']).open('a',encoding='utf-8') as out:
 out.write(json.dumps(sys.argv[1:])+'\\n')
with Path(os.environ['FAKE_COMMAND_LOG']+'.temp').open('a',encoding='utf-8') as out:
 out.write(json.dumps({'TEMP':os.environ.get('TEMP'),'TMP':os.environ.get('TMP')})+'\\n')
print('FAKE_STDOUT '+repr(sys.argv[1:]))
if os.environ.get('FAKE_CMAKE_FAIL') and '-m' in sys.argv:
 print('RETAINED_CMAKE_DIAGNOSTIC',file=sys.stderr)
 sys.exit(9)
''')
        (fake / 'python.cmd').write_text('@"' + sys.executable + '" "' + str(runner) + '" %*\n')
        env = os.environ.copy()
        env.pop('AIBS_EVIDENCE_ROOT', None)
        env['PATH'] = str(fake) + os.pathsep + env['PATH']
        env['FAKE_COMMAND_LOG'] = str(self.root / 'commands.jsonl')
        return root, evidence, previous, env

    def invoke(self, root, env):
        return subprocess.run(['powershell.exe', '-NoProfile', '-ExecutionPolicy', 'Bypass',
            '-File', str(root / 'scripts/verify.ps1'), '-Configuration', 'Debug',
            '-TempRoot', str(SOURCE.parent / 't')],
            env=env, capture_output=True, text=True, timeout=45)

    def test_repeated_runs_preserve_previous_evidence_and_configured_base(self):
        root, evidence, previous, env = self.fixture()
        for _ in range(2):
            result = self.invoke(root, env)
            self.assertEqual(0, result.returncode, result.stdout + result.stderr)
        self.assertEqual('RETAINED_VALIDATION', (previous / 'previous.txt').read_text())
        self.assertTrue((root / 'out/verification.log').read_text(encoding='utf-8-sig').startswith('RETAINED_PREVIOUS_LOG'))
        commands = [json.loads(line) for line in Path(env['FAKE_COMMAND_LOG']).read_text().splitlines()]
        overrides = [arg.split('=', 1)[1] for cmd in commands for arg in cmd
                     if arg.startswith('-DAIBS_VERIFICATION_EVIDENCE_ROOT=')]
        self.assertEqual(2, len(overrides))
        self.assertNotEqual(overrides[0], overrides[1])
        for directory in overrides:
            self.assertTrue(Path(directory).resolve().is_relative_to(evidence.resolve()))
            run = Path(directory).parent
            self.assertTrue((run / 'verification.log').is_file())
            self.assertEqual('passed', json.loads((run / 'verification.json').read_text(encoding='utf-8-sig'))['status'])
        installs = [cmd[cmd.index('--prefix') + 1] for cmd in commands if '--install' in cmd]
        consumers = [cmd[cmd.index('-B') + 1] for cmd in commands if '-S' in cmd]
        self.assertEqual(2, len(installs))
        for directory, sdk, consumer in zip(overrides, installs, consumers):
            run = Path(directory).parent.resolve()
            self.assertTrue(Path(sdk).resolve().is_relative_to(run), 'Verification must not overwrite an existing installed SDK')
            self.assertTrue(Path(consumer).resolve().is_relative_to(run), 'SDK consumer build must be unique to this run')
        self.assertEqual('AIBS_EVIDENCE_ROOT:PATH=' + evidence.as_posix() + '\n',
                         (root / 'out/windows-msvc/CMakeCache.txt').read_text())

    def test_failure_retains_native_stderr_and_failed_receipt(self):
        root, evidence, previous, env = self.fixture()
        env['FAKE_CMAKE_FAIL'] = '1'
        result = self.invoke(root, env)
        self.assertNotEqual(0, result.returncode)
        commands = [json.loads(line) for line in Path(env['FAKE_COMMAND_LOG']).read_text().splitlines()]
        roots = [arg.split('=', 1)[1] for cmd in commands for arg in cmd if arg.startswith('-DAIBS_VERIFICATION_EVIDENCE_ROOT=')]
        logs = [Path(directory).parent / 'verification.log' for directory in roots]
        self.assertEqual(1, len(logs))
        self.assertIn('RETAINED_CMAKE_DIAGNOSTIC', logs[0].read_text(encoding='utf-8-sig'))
        receipt = json.loads((logs[0].parent / 'verification.json').read_text(encoding='utf-8-sig'))
        self.assertEqual('failed', receipt['status'])
        self.assertEqual(9, receipt['last_cmake_exit_code'])
        self.assertTrue((previous / 'previous.txt').exists())

    def test_native_temporary_paths_are_fresh_short_and_retained(self):
        root, evidence, previous, env = self.fixture()
        temporary_paths = []
        for _ in range(2):
            result = subprocess.run(['powershell.exe','-NoProfile','-ExecutionPolicy','Bypass',
                '-File',str(root/'scripts/verify.ps1'),'-Configuration','Debug',
                '-TempRoot',str(SOURCE.parent/'t')],env=env,capture_output=True,text=True,timeout=45)
            self.assertEqual(0,result.returncode,result.stdout+result.stderr)
            commands = [json.loads(line) for line in Path(env['FAKE_COMMAND_LOG']).read_text().splitlines()]
            directory = next(arg.split('=',1)[1] for command in reversed(commands) for arg in command
                             if arg.startswith('-DAIBS_VERIFICATION_EVIDENCE_ROOT='))
            receipt = json.loads((Path(directory).parent/'verification.json').read_text(encoding='utf-8-sig'))
            temporary = Path(receipt['temporary_root'])
            self.assertTrue(temporary.is_dir())
            self.assertTrue(temporary.resolve().is_relative_to((SOURCE.parent/'t').resolve()))
            self.assertLessEqual(len(str(temporary)),36)
            temporary_paths.append(temporary)
            (temporary/'retained.txt').write_text('retain native fixture evidence')
        self.assertNotEqual(*temporary_paths)
        observations = [json.loads(line) for line in Path(env['FAKE_COMMAND_LOG']+'.temp').read_text().splitlines()]
        for temporary in temporary_paths:
            self.assertEqual('retain native fixture evidence',(temporary/'retained.txt').read_text())
            self.assertTrue(any(item['TEMP']==str(temporary) and item['TMP']==str(temporary) for item in observations))

    def test_long_native_evidence_path_is_rejected_before_cmake(self):
        root, evidence, previous, env = self.fixture()
        long_root = self.root / 'deliberately-long-configured-native-evidence-root'
        (root / 'out/windows-msvc/CMakeCache.txt').write_text('AIBS_EVIDENCE_ROOT:PATH=' + long_root.as_posix() + '\n')
        result = self.invoke(root, env)
        self.assertNotEqual(0, result.returncode)
        self.assertIn('evidence path is too long', result.stdout + result.stderr)
        commands = [json.loads(line) for line in Path(env['FAKE_COMMAND_LOG']).read_text().splitlines()]
        self.assertFalse(any('-m' in cmd for cmd in commands))
        receipts = list(long_root.glob('v/*/verification.json'))
        self.assertEqual(1, len(receipts))
        self.assertEqual('failed', json.loads(receipts[0].read_text(encoding='utf-8-sig'))['status'])
        self.assertEqual('RETAINED_VALIDATION', (previous / 'previous.txt').read_text())

    def test_native_lock_still_refuses_overlap(self):
        root, evidence, previous, env = self.fixture()
        kernel = ctypes.WinDLL('kernel32', use_last_error=True)
        kernel.CreateFileW.argtypes = [ctypes.c_wchar_p, ctypes.c_ulong, ctypes.c_ulong,
                                      ctypes.c_void_p, ctypes.c_ulong, ctypes.c_ulong, ctypes.c_void_p]
        kernel.CreateFileW.restype = ctypes.c_void_p
        kernel.CloseHandle.argtypes = [ctypes.c_void_p]
        handle = kernel.CreateFileW(str(root / 'out/verification.lock'), 0xC0000000, 0, None, 4, 0x80, None)
        self.assertNotEqual(ctypes.c_void_p(-1).value, handle)
        try:
            result = self.invoke(root, env)
            self.assertNotEqual(0, result.returncode)
            self.assertFalse(Path(env['FAKE_COMMAND_LOG']).exists())
        finally:
            kernel.CloseHandle(handle)

    def test_sdk_consumer_requests_current_supported_minor(self):
        version = re.search(r'project\(AIBSEngine VERSION ([\d.]+)',
                            (SOURCE / 'CMakeLists.txt').read_text()).group(1)
        consumer = (SOURCE / 'examples/sdk_consumer/CMakeLists.txt').read_text()
        self.assertRegex(consumer, r'find_package\(AIBS\s+' + re.escape(version) + r'\s+CONFIG REQUIRED\)')

    def test_actual_cmake_version_selection_accepts_current_and_rejects_other_minor(self):
        source = (SOURCE / 'CMakeLists.txt').read_text()
        version = re.search(r'project\(AIBSEngine VERSION ([\d.]+)', source).group(1)
        policy = re.search(r'VERSION \$\{PROJECT_VERSION\} COMPATIBILITY (\w+)', source).group(1)
        package = self.root / 'synthetic-sdk'
        package.mkdir()
        (package / 'AIBSConfig.cmake').write_text('set(AIBS_VERSION "' + version + '")\n')
        generator = self.root / 'generate.cmake'
        generator.write_text('include(CMakePackageConfigHelpers)\nwrite_basic_package_version_file("' +
            (package / 'AIBSConfigVersion.cmake').as_posix() + '" VERSION ' + version + ' COMPATIBILITY ' + policy + ')\n')
        result = subprocess.run([sys.executable, '-m', 'cmake', '-P', str(generator)], capture_output=True, text=True, timeout=30)
        self.assertEqual(0, result.returncode, result.stdout + result.stderr)
        for requested, compatible in [(version, True), ('0.16.4', False)]:
            consumer = self.root / ('request-' + requested)
            consumer.mkdir()
            (consumer / 'CMakeLists.txt').write_text('cmake_minimum_required(VERSION 3.25)\nproject(VersionContract NONE)\nfind_package(AIBS ' +
                requested + ' CONFIG REQUIRED PATHS "' + package.as_posix() + '" NO_DEFAULT_PATH)\n')
            result = subprocess.run([sys.executable, '-m', 'cmake', '-S', str(consumer), '-B', str(consumer / 'build')],
                                    capture_output=True, text=True, timeout=30)
            (consumer / 'configure.log').write_text(result.stdout + result.stderr)
            self.assertEqual(compatible, result.returncode == 0, result.stdout + result.stderr)

    def test_viewport_health_reports_persistent_failure_and_recovers(self):
        source = (SOURCE / 'apps/creator_viewport.cpp').read_text()
        start, end = '// BEGIN SNAPSHOT WATCH HEALTH', '// END SNAPSHOT WATCH HEALTH'
        self.assertIn(start, source, 'Viewport must distinguish transient and persistent unavailability')
        implementation = source.split(start, 1)[1].split(end, 1)[0]
        cpp = self.root / 'health.cpp'
        cpp.write_text('#include <chrono>\n#include <optional>\n#include <string>\n#include <cassert>\n' +
            implementation + '''
int main(){
 SnapshotHealth health;using namespace std::chrono;
 const auto start=SnapshotHealth::Clock::time_point{};
 assert(!health.pending());
 assert(!health.failure(start,"open32",true));assert(health.pending());
 assert(!health.failure(start+milliseconds(1999),"open32",true));
 assert(health.failure(start+seconds(2),"open32",true));
 assert(!health.failure(start+seconds(3),"open32",true));
 assert(health.recover());assert(!health.pending());assert(!health.recover());
 assert(health.failure(start+seconds(4),"invalid snapshot",false));
 assert(!health.failure(start+seconds(5),"invalid snapshot",false));
 assert(health.recover());
 assert(!health.failure(start+seconds(6),"metadata",true));
 assert(!health.recover());assert(!health.pending());
}
''')
        vcvars = Path(os.environ.get('ProgramFiles(x86)', r'C:/Program Files (x86)')) / 'Microsoft Visual Studio/2022/BuildTools/VC/Auxiliary/Build/vcvars64.bat'
        self.assertTrue(vcvars.exists(), 'Installed MSVC toolchain required for real state-machine test')
        batch = self.root / 'compile_health.cmd'
        batch.write_text('@echo off\ncall "' + str(vcvars) + '" >nul\nif errorlevel 1 exit /b 1\ncl /nologo /EHsc /std:c++20 /W4 /WX "' + str(cpp) + '" /Fe:"' + str(self.root / 'health.exe') + '" /Fo:"' + str(self.root / 'health.obj') + '"\n')
        result = subprocess.run(['cmd.exe', '/d', '/c', str(batch)], capture_output=True, text=True, timeout=45)
        self.assertEqual(0, result.returncode, result.stdout + result.stderr)
        result = subprocess.run([str(self.root / 'health.exe')], capture_output=True, timeout=10)
        self.assertEqual(0, result.returncode, result.stdout + result.stderr)


if __name__ == '__main__':
    unittest.main()
