"""Replay one retained diagnostic capture; never credit failed native admission.

The source capture's native debug guard failed and remains failed. This tool
establishes only whether its already captured frame can be replayed/inspected.
"""
import argparse
from datetime import datetime, timezone
from pathlib import Path
import os
import csv
import math

from qualify_rtx_creator import ROOT, VARIANTS, load, long, need, plain, write_json
from qualify_rtx_hud_fit import validate_candidate
from qualify_rtx_nsight import TOOLS, artifact, environment, run_owned, verify_tools

SOURCE = VARIANTS/'Nsight_LH_20261111_v01'
CAPTURE = SOURCE/'capture/lh-frame.ngfx-bincap'
EXPECTED_CAPTURE = {'bytes': 9789336, 'sha256': '6667cf36d1f5072283cf7f4cd9188741a91d5e943de489f2623b0045e5d6d702'}


def inspect_reports(directory):
    captures=list(directory.glob('*/capture.png'))
    images=list(directory.glob('*/replay_0.png'))
    timing=list(directory.glob('*/iteration_times.csv'))
    need(len(captures)==len(images)==len(timing)==1, 'Expected one original/replay image and one iteration report')
    need(artifact(captures[0])==artifact(images[0]), 'Replayed image differs from captured image')
    with timing[0].open(newline='',encoding='utf8') as stream:
        rows=list(csv.DictReader(stream,skipinitialspace=True))
    need(len(rows)==1 and int(rows[0]['numFrames'])==1 and float(rows[0]['mae'])==0,
         'Replay image comparison or frame count failed')
    need(math.isfinite(float(rows[0]['msFrameTime'])), 'Invalid replay timing')
    return {'capture_image':artifact(captures[0]),'replayed_image':artifact(images[0]),
            'capture_and_replay_png_bytes_equal':True,'comparison_mean_absolute_error':0,
            'frames':1,'ordinary_gameplay_fps_qualification':False}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    output = args.output.absolute()
    plain(output)
    need(output.parent == VARIANTS and output.name.startswith('Nsight_LH_Replay_')
         and not long(output).exists(), 'Use a new reviewed replay-only fixture')
    player, candidate = validate_candidate()
    tools = verify_tools()
    source = load(SOURCE/'capture.process.json')
    need(source['terminal'] and source['exit_code'] == 4294967295 and len(source['player_processes']) == 1
         and source['player_processes'][0]['terminal'] and source['player_processes'][0]['exit_code'] == 1,
         'Expected retained failed native capture, with all owners terminal')
    need(artifact(CAPTURE) == EXPECTED_CAPTURE, 'Retained capture bytes changed')
    long(output).mkdir()
    record = {'utc': datetime.now(timezone.utc).isoformat(), 'status': 'INCOMPLETE',
              'scope': 'Retained frame replay diagnostic only; original native debug admission remains FAILED',
              'native_capture_acceptance_passed': False, 'ordinary_performance_measured': False,
              'capture': str(CAPTURE), 'capture_pin': EXPECTED_CAPTURE, 'tools': tools,
              'candidate': candidate}
    try:
        env = environment(output, player)
        for name in ('replay-temp','replay-performance'):
            long(output/name).mkdir()
        command = [str(TOOLS/'ngfx-replay.exe'), '--loop-count','1', '--max-worker-threads','4',
                   '--temp-resource-dir',str(output/'replay-temp'), '--perf-report-dir',str(output/'replay-performance'),
                   '--no-crash-reporting', str(CAPTURE)]
        record['process'] = run_owned(command, TOOLS, env, output, 'replay')
        rows = {}
        for here, directories, files in os.walk(long(output/'replay-performance'),followlinks=False):
            for name in directories:
                plain(Path(here)/name)
            for name in files:
                path=Path(here)/name
                need(len(rows)<128,'Replay report member bound exceeded')
                rows[path.relative_to(long(output/'replay-performance')).as_posix()]=artifact(path,64*1024**2)
        record['replay_raw_reports']=rows
        record['replay_visual_check']=inspect_reports(output/'replay-performance')
        need(artifact(CAPTURE)==EXPECTED_CAPTURE and validate_candidate()[1]==candidate
             and verify_tools()==tools, 'Read-only inputs changed during replay')
        record['status']='REPLAY_EXIT0_NATIVE_CAPTURE_ACCEPTANCE_STILL_FAILED'
    except Exception as error:
        record.update(status='FAILED_OR_RETAINED',error=str(error))
        raise
    finally:
        write_json(output/'qualification.json',record)
        print(record['status'],flush=True)


if __name__ == '__main__':
    main()
