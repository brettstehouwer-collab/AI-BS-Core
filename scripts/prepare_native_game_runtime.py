"""Build matching Release runtime tools into a new package-only runtime prefix.

Never installs an SDK, replaces a frozen candidate, runs a game or packages Studio.
"""
import os
from pathlib import Path
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'engine/tools'))
from qualify_rtx_creator import read, write, pin, plain, load, write_json
from qualify_rtx_hud_fit import validate_candidate

BUILD = ROOT/'t/hudfit_build01'
OUT = ROOT/'backups/studio139_runtime_20261111_v01'
TARGETS = ('aibs_player', 'aibs_creator_host', 'aibs_content_host',
           'aibs_creator_viewport', 'aibs_assetc', 'aibs_warm_opening_project')


def need(value, message):
    if not value:
        raise RuntimeError(message)


def prepare():
    player, candidate = validate_candidate()
    original = load(ROOT/'t/hudfit_build01/frozen-candidate-v01.json')
    need(pin(BUILD/'Release/aibs_motherboard.exe') == pin(player), 'Release motherboard differs from frozen4324')
    need(not OUT.exists(), 'Preserve existing runtime attempts')
    plain(OUT); plain(BUILD)
    source = read(ROOT/'engine/CMakeLists.txt').decode('utf8')
    for target in TARGETS:
        need('add_executable('+target+' ' in source, 'Expected runtime target absent: '+target)
        need((BUILD/(target+'.vcxproj')).is_file(), 'Expected generated target absent: '+target)
    cache = read(BUILD/'CMakeCache.txt').decode('utf8')
    for expected in ('CMAKE_HOME_DIRECTORY:INTERNAL=C:/AI-BS/engine',
        'FETCHCONTENT_FULLY_DISCONNECTED:BOOL=ON',
        'FETCHCONTENT_SOURCE_DIR_JOLTSOURCE:PATH=C:/AI-BS/t/r139d01/jolt',
        'FETCHCONTENT_SOURCE_DIR_SQLITESOURCE:PATH=C:/AI-BS/t/r139d01/sqlite'):
        need(expected in cache, 'Reviewed offline build configuration differs')
    OUT.mkdir()
    record = {'status': 'INCOMPLETE', 'purpose': 'runtime-prefix-for-package',
        'full_static_developer_sdk_qualified': False, 'games_or_gpu_tests_executed': False,
        'install_or_launcher_changed': False, 'candidate_before': candidate,
        'canonical_source_pins': original['source_pins'], 'frozen_artifact_pins': original['artifact_pins'],
        'build_cache_before': pin(BUILD/'CMakeCache.txt'), 'targets': TARGETS}
    try:
        # Read the existing builder's closed runtime contract; no application
        # imports, stage/build actions or private content are executed here.
        import build_native_game_release as builder
        destinations = {Path(original_name).relative_to('engine/install/release').as_posix()
                        for original_name, _ in builder.NATIVE_PLAYER_ASSETS}
        destinations.update('bin/'+name for name in builder._asset_contract.WARM_PLAYER_FILES
                            if name != 'cgltf-LICENSE.txt')
        destinations.update(('bin/aibs_warm_opening_project.exe', 'share/licenses/AIBS/cgltf/LICENSE.txt'))
        need(len(destinations) == 18, 'Unexpected runtime closure; review before building')
        command = [str(Path('C:/Program Files/CMake/bin/cmake.exe')), '--build', str(BUILD),
            '--config', 'Release', '--target', *TARGETS, '--parallel', '4']
        write_json(OUT/'preflight.json', {**record, 'expected_runtime_members': sorted(destinations), 'command': command})
        with (OUT/'build.stdout.log').open('xb') as stdout, (OUT/'build.stderr.log').open('xb') as stderr:
            child = subprocess.Popen(command, cwd=ROOT, stdin=subprocess.DEVNULL, stdout=stdout,
                stderr=stderr, creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
            write_json(OUT/'build.started.json', {'pid': child.pid, 'command': command,
                'exact_popen_handle_retained': True})
            began, retained = time.monotonic(), False
            while child.poll() is None:
                if not retained and time.monotonic()-began > 600:
                    retained = True
                    write_json(OUT/'build.retained.json', {'pid': child.pid,
                        'status': 'RETAINED_NO_KILL_OR_RESTART', 'exact_popen_handle_retained': True})
                time.sleep(.2)
            record['build'] = {'pid': child.pid, 'terminal': True, 'exit_code': child.returncode,
                'wall_seconds': time.monotonic()-began, 'deadline_exceeded': retained}
            write_json(OUT/'build.process.json', record['build'])
            need(child.returncode == 0 and not retained, 'Runtime target build failed; preserve diagnostics')
        need(validate_candidate()[1] == candidate and pin(BUILD/'Release/aibs_motherboard.exe') == pin(player),
             'Frozen/current motherboard or canonical sources changed')
        prefix = OUT/'runtime-prefix'
        prefix.mkdir()
        rows = {}
        for relative in sorted(destinations):
            rel = Path(relative)
            if rel.parts[0] == 'bin':
                origin = BUILD/'Release'/Path(*rel.parts[1:])
            elif relative == 'share/licenses/AIBS/cgltf/LICENSE.txt':
                origin = ROOT/'engine/third_party/cgltf/LICENSE.txt'
            else:
                origin = ROOT/'engine/third_party'/rel.name
            plain(origin)
            need(origin.is_file(), 'Required runtime source missing: '+str(origin))
            expected = pin(origin)
            target = prefix/rel
            plain(target)
            target.parent.mkdir(parents=True, exist_ok=True)
            write(target, read(origin))
            need(pin(target) == expected and pin(origin) == expected, 'Runtime copy/source changed')
            rows[relative] = {'source': str(origin), **expected}
        need(len(rows) == 18 and {p.relative_to(prefix).as_posix() for p in prefix.rglob('*') if p.is_file()} == set(rows),
             'Runtime member set differs')
        caps = load(prefix/'bin/aibs_capabilities.json')
        builder._asset_contract.require_saved_play_capabilities(caps)
        builder._asset_contract.require_opening_capabilities(caps)
        need(pin(prefix/'bin/aibs_motherboard.exe') == pin(player), 'Composed runtime player differs')
        record.update(status='PREPARED_RELEASE_RUNTIME_PREFIX_NOT_INSTALLED', runtime_prefix=str(prefix),
            members=rows, canonical_and_frozen_unchanged=validate_candidate()[1] == candidate,
            source_notices_preserved_exactly=True)
        write_json(OUT/'runtime-files.json', rows)
        print(str(prefix), flush=True)
    except BaseException as error:
        record.update(status='FAILED_OR_RETAINED', error=str(error))
        raise
    finally:
        record['candidate_after'] = validate_candidate()[1]
        write_json(OUT/'preparation.json', record)
        print(record['status'], flush=True)


if __name__ == '__main__':
    prepare()
