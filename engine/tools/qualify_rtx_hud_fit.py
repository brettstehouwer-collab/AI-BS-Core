"""Owned copied-chapter integration of the explicit HUD-fit candidate only."""
import argparse
from datetime import datetime, timezone
from pathlib import Path
import uuid

from qualify_rtx_creator import ROOT, VARIANTS, copy_tree, load, long, need, pin, plain, tree, write_json
from qualify_rtx_current_player import CREATOR, run_stage

CANDIDATE = ROOT/'t/hudfit_build01/frozen-candidate-v01.json'
PLAYER_SHA = '4324fca383f876db588997f6353cde2915a5613f8e31c3fe3571f95a807c55ce'


def validate_candidate():
    manifest = load(CANDIDATE)
    player = Path(manifest['player'])
    need(player == ROOT/'t/hudfit_build01/frozen_v01/aibs_motherboard.exe', 'Wrong candidate location')
    need(pin(player)['sha256'] == manifest['player_sha256'] == PLAYER_SHA, 'HUD-fit player changed')
    need(len(manifest['artifact_pins']) == 9 and len(manifest['source_pins']) == 158, 'Incomplete candidate provenance')
    for name, expected in manifest['artifact_pins'].items():
        need(pin(Path(name)) == expected, 'Candidate artifact changed: '+name)
    for name, expected in manifest['source_pins'].items():
        need(pin(Path(name))['sha256'] == expected, 'Compiled source changed: '+name)
    for name, expected in manifest['validation_source_pins'].items():
        need(pin(Path(name)) == expected, 'Validation source changed: '+name)
    return player, pin(CANDIDATE)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    output = args.output.absolute()
    plain(output)
    need(output.parent == VARIANTS and not long(output).exists(), 'Use a new reviewed RTX child')
    player, manifest_pin = validate_candidate()
    before = tree(CREATOR/'project')
    need(pin(CREATOR/'project/opening.aibd') == load(CREATOR/'author.json')['opening'], 'Original current export differs')
    long(output).mkdir()
    result = {'utc': datetime.now(timezone.utc).isoformat(), 'status': 'INCOMPLETE',
              'player': str(player), 'player_sha256': PLAYER_SHA, 'manifest': manifest_pin,
              'scope': 'Controlled hidden native copied chapter and temporary databases; not human play or installed release',
              'viewports': []}
    write_json(output/'preflight.json', {'source': str(CREATOR/'project'), 'source_tree': before,
                                       'candidate': manifest_pin})
    try:
        for dimensions in ((640,480), (800,600), (960,640), (1440,900)):
            case = output/('%dx%d' % dimensions)
            long(case).mkdir()
            copy_tree(CREATOR/'project', case/'project')
            session = str(uuid.uuid4())
            stages = {stage: run_stage(player, case, session, stage, dimensions) for stage in ('seed','reload')}
            for key in ('scope','content','chapter_ids','components','events','visible_revision','durable_revision','durable_sequence'):
                need(stages['seed']['report'][key] == stages['reload']['report'][key], 'Reload durability differs: '+key)
            need(tree(case/'project') == before, 'Owned immutable input changed')
            result['viewports'].append({'dimensions': dimensions, 'stages': stages})
        need(validate_candidate()[1] == manifest_pin, 'Candidate changed during run')
        result['status'] = 'PASS_CONTROLLED_HUD_FIT_FOUR_VIEWPORTS'
    except Exception as exc:
        result.update(status='FAILED', error=str(exc))
        raise
    finally:
        result['original_project_unchanged'] = tree(CREATOR/'project') == before
        if not result['original_project_unchanged']:
            result['status'] = 'FAILED_SOURCE_PRESERVATION'
        write_json(output/'qualification.json', result)
        print(result['status'], flush=True)
    need(result['original_project_unchanged'], 'Original source changed')


if __name__ == '__main__':
    main()
