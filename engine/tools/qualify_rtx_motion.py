"""Finite controlled-motion measurement; CUA foreground assistance is separate.

Never takes focus or sends desktop input. Copies only the qualified chapter into
a new reviewed fixture. The owned player drains and exits itself; timeouts retain
the exact process, rather than killing or restarting it.
"""
import argparse
from datetime import datetime, timezone
import os
from pathlib import Path
import subprocess
import time
import uuid

import psutil
from qualify_rtx_creator import ROOT, VARIANTS, copy_tree, load, long, need, plain, pin, tree, write_json
from qualify_rtx_current_player import CREATOR
from qualify_rtx_hud_fit import validate_candidate


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    output = args.output.absolute()
    plain(output)
    need(output.parent == VARIANTS and not long(output).exists(), 'Use a new direct RTX child')
    player, manifest = validate_candidate()
    source = CREATOR/'project'
    before = tree(source)
    need(pin(source/'opening.aibd') == load(CREATOR/'author.json')['opening'], 'Current export changed')
    long(output).mkdir()
    copy_tree(source, output/'project')
    session = str(uuid.uuid4())
    command = [str(player), '--durable-world', '--content-definition', str(output/'project/opening.aibd'),
               '--asset-root', str(output/'project/assets/packs'), '--database', str(output/'world.sqlite'),
               '--project', 'prop01-native-acceptance', '--branch', 'independent-prop01-v1',
               '--play-session', session, '--stop-file', str(output/('stop.'+session+'.request')),
               '--width', '1920', '--height', '1080', '--performance-controlled-motion',
               '--performance-seconds', '180', '--performance-warmup', '2',
               '--performance-report', str(output/'performance.json'), '--capture', str(output/'final.bmp')]
    env = {key: os.environ[key] for key in ('SystemRoot','WINDIR','TEMP','TMP') if key in os.environ}
    env['PATH'] = str(player.parent)+';C:\\Windows\\System32'
    result = {'utc': datetime.now(timezone.utc).isoformat(), 'status': 'INCOMPLETE',
              'scope': 'Controlled internally commanded motion with separately recorded CUA-assisted activation; not ordinary input or human play',
              'command': command, 'candidate_manifest': manifest}
    write_json(output/'preflight.json', {'source': str(source), 'source_tree': before, 'candidate': manifest})
    try:
        with (output/'stdout.log').open('xb') as stdout, (output/'stderr.log').open('xb') as stderr:
            child = subprocess.Popen(command, cwd=player.parent, env=env, stdout=stdout, stderr=stderr,
                                     creationflags=subprocess.CREATE_NO_WINDOW)
            identity = {'pid': child.pid, 'created': psutil.Process(child.pid).create_time(),
                        'executable': str(player), 'retained_exact_handle': True}
            write_json(output/'owned-player.json', identity)
            result['process'] = identity
            print('OWNED_PLAYER_READY_FOR_CUA '+str(child.pid), flush=True)
            deadline = time.monotonic()+240
            while child.poll() is None and time.monotonic()<deadline:
                time.sleep(.25)
            identity.update(terminal=child.poll() is not None, exit_code=child.poll())
            need(identity['terminal'], 'Owned player still live; retain process and inspect, no restart')
            need(child.returncode == 0, 'Native measurement failed; retain report and diagnostics')
        native = load(output/'performance.json')
        result['native'] = native
        need(native['status'] == 'measured' and native['error'] == '', 'Measurement did not qualify')
        need(native['measurement_profile'] == 'controlled-motion' and native['controlled_input']
             and not native['os_focus_input_verified'] and not native['human_pacing_measured'], 'Wrong qualification scope')
        need(native['saved_close_complete'] and native['visible_revision'] == native['durable_revision'] == 0,
             'Measurement changed chapter outcomes or failed saved close')
        need(native['gpu_debug_errors'] == native['gpu_debug_warnings'] == 0, 'GPU diagnostic failure')
        need(native['actual_client_width'] == 1920 and native['actual_client_height'] == 1080
             and native['measured_wall_seconds'] >= 180 and native['frame_count'] > 0,
             'Incomplete duration, size or actual frame observations')
        need(tree(output/'project') == before, 'Owned immutable inputs changed')
        need(validate_candidate()[1] == manifest, 'Candidate/source changed')
        result['status'] = 'MEASURED_CONTROLLED_MOTION'
    except Exception as error:
        result.update(status='FAILED_OR_RETAINED', error=str(error))
        raise
    finally:
        result['original_source_unchanged'] = tree(source) == before
        write_json(output/'qualification.json', result)
        print(result['status'], flush=True)


if __name__ == '__main__':
    main()
