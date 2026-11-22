"""Assess existing native aggregate reports; never launches or fabricates a run.

Targets: docs/game_engine/implementation_plan.md section 8. Aggregate native v1
reports do not record measured-interval route activity, GPU process residency,
DXGI budgets/pressure, or isolated game/physics timings. Those remain open even
when all available frame and CPU-memory targets pass.
"""
import math


def summarize_gpu_samples(gpu, *, expected_pid):
    """Summarize paired owned-process LOCAL samples, never adapter occupancy.

    Offset times belong to the observer, not the native measurement clock. No
    sample span, even 300 seconds, independently proves benchmark coverage.
    """
    cap = 8*1024**3
    base = dict(schema_version=1, expected_pid=expected_pid, pid=None,
                provenance_verified=False, status='unavailable', nodes=[],
                soft_cap_bytes=cap, any_observed_over_effective_cap=None,
                measurement_interval_coverage_verified=False, budget_pass=None,
                limitations=['Per-process LOCAL usage/budget per physical node; not adapter-wide occupancy',
                             'Sampled maxima are not unsampled peaks; node maxima are not additive',
                             'Observer offsets are not bound to the native measurement interval; five-minute coverage remains unknown'])
    if not isinstance(gpu, dict):
        return {**base, 'errors':['missing_or_invalid_gpu_sidecar']}
    base.update(pid=gpu.get('pid'), reported_status=gpu.get('status'),
                query_api=gpu.get('query_api'), process_handle_source=gpu.get('process_handle_source'),
                segment_group=gpu.get('segment_group'))
    valid = (type(expected_pid) is int and expected_pid > 0 and type(gpu.get('pid')) is int and
             gpu['pid'] == expected_pid and gpu.get('schema') == 'owned-process-wddm-local-v1' and
             gpu.get('query_api') == 'Gdi32!D3DKMTQueryVideoMemoryInfo' and
             gpu.get('process_handle_source') == 'existing_owned_Popen._handle' and gpu.get('segment_group') == 'LOCAL')
    if not valid:
        return {**base, 'status':'invalid_provenance', 'errors':['owned_process_local_provenance_mismatch']}
    base['provenance_verified'] = True
    samples = gpu.get('samples')
    if type(samples) is not list or len(samples) > 10000:
        return {**base, 'status':'invalid_samples', 'errors':['samples_missing_or_exceed_bound']}
    groups, invalid = {}, 0
    for s in samples:
        if not isinstance(s, dict) or type(s.get('luid')) is not str or not s['luid'] or type(s.get('physical_adapter_index')) is not int or s['physical_adapter_index'] < 0:
            invalid += 1
            continue
        key = s['luid'], s['physical_adapter_index']
        g = groups.setdefault(key, dict(luid=key[0], physical_adapter_index=key[1], successful_samples=0,
                                       failed_samples=0, invalid_samples=0, _good=[]))
        if s.get('success') is False:
            g['failed_samples'] += 1
            continue
        offset = s.get('offset_seconds')
        good = (s.get('success') is True and type(offset) in (int, float) and math.isfinite(offset) and offset >= 0 and
                all(type(s.get(k)) is int and s[k] >= 0 for k in ('current_usage_bytes', 'budget_bytes')))
        if not good:
            g['invalid_samples'] += 1
            invalid += 1
            continue
        g['successful_samples'] += 1
        g['_good'].append(dict(offset_seconds=offset, current_usage_bytes=s['current_usage_bytes'],
                               budget_bytes=s['budget_bytes'], effective_cap_bytes=min(cap, s['budget_bytes'])))
    nodes, any_over = [], None
    for g in groups.values():
        good = sorted(g.pop('_good'), key=lambda s:s['offset_seconds'])
        if good:
            peak = max(good, key=lambda s:s['current_usage_bytes'])
            over = [s for s in good if s['current_usage_bytes'] > s['effective_cap_bytes']]
            any_over = bool(over) or bool(any_over)
            gaps = [b['offset_seconds']-a['offset_seconds'] for a,b in zip(good, good[1:])]
            g.update(maximum_observed_usage_bytes=peak['current_usage_bytes'], paired_budget_at_maximum_usage_bytes=peak['budget_bytes'],
                     peak_usage_pair=peak, minimum_observed_budget_bytes=min(s['budget_bytes'] for s in good),
                     any_observed_over_effective_cap=bool(over), over_effective_cap_samples=len(over),
                     first_over_effective_cap_pair=over[0] if over else None,
                     first_success_offset_seconds=good[0]['offset_seconds'], last_success_offset_seconds=good[-1]['offset_seconds'],
                     observed_success_span_seconds=good[-1]['offset_seconds']-good[0]['offset_seconds'],
                     maximum_observed_success_gap_seconds=max(gaps) if gaps else None)
        else:
            g.update(maximum_observed_usage_bytes=None, paired_budget_at_maximum_usage_bytes=None,
                     any_observed_over_effective_cap=None, observed_success_span_seconds=None)
        nodes.append(g)
    return {**base, 'status':'observed_partial_coverage' if any_over is not None else 'unavailable',
            'nodes':nodes, 'invalid_samples':invalid,
            'any_observed_over_effective_cap':any_over,
            'observer_thread_joined':gpu.get('thread_joined'), 'observer_dropped_samples':gpu.get('dropped_samples'),
            'errors':['invalid_sample_rows'] if invalid else []}


def assess(report, *, expected_fingerprint, expected_world, expected_timeline):
    checks, errors = {}, []

    def check(name, condition):
        checks[name] = bool(condition)
        if not condition:
            errors.append(name)

    def number(value, minimum=0):
        return type(value) in (int, float) and math.isfinite(value) and value >= minimum

    def integer(value, minimum=0):
        return type(value) is int and value >= minimum

    if not isinstance(report, dict):
        report = {}
    r = report
    frame = r.get('frame_ms')
    frame = frame if isinstance(frame, dict) else {}
    count, wall = r.get('frame_count'), r.get('measured_wall_seconds')
    fps, mean = r.get('fps'), frame.get('mean')
    check('native_measured', type(r.get('version')) is int and r['version'] == 1 and
          r.get('status') == 'measured' and r.get('error') == '')
    check('ordinary_gameplay_profile', r.get('measurement_profile') == 'gameplay' and
          r.get('gameplay_includes_reading_inspection_and_saving') is True and
          r.get('controlled_input', False) is False)
    check('expected_scope', all(type(x) is str and bool(x) for x in
          (expected_fingerprint, expected_world, expected_timeline)) and
          r.get('content_fingerprint') == expected_fingerprint and
          r.get('scope') == dict(world_id=expected_world, timeline_id=expected_timeline))
    check('physical_1080p', all(type(r.get(k)) is int and r[k] == target for k, target in
          [('requested_width', 1920), ('requested_height', 1080),
           ('actual_client_width', 1920), ('actual_client_height', 1080)]))
    check('five_minute_request', number(r.get('requested_measure_seconds')) and r['requested_measure_seconds'] == 300)
    check('warmup', number(r.get('warmup_min_seconds'), 2) and r['warmup_min_seconds'] <= 30)
    check('full_measured_interval', number(wall, 300))
    # Timer close is the standard bounded diagnostic: it need not be a manual
    # player close. Both cases must drain through the saved close path.
    check('saved_close', type(r.get('normal_player_close')) is bool and r.get('saved_close_complete') is True)
    check('durable_outcomes', integer(r.get('visible_revision')) and
          integer(r.get('durable_revision')) and r['visible_revision'] == r['durable_revision'])
    check('present_accounting', integer(count, 1) and integer(r.get('actual_present_delta'), 1) and
          r['actual_present_delta'] == count)
    check('actual_time_statistics', number(wall, 0) and wall > 0 and integer(count, 1) and
          number(fps, 0) and fps > 0 and number(mean, 0) and mean > 0 and
          abs(fps-count/wall) < .01 and abs(mean-1000*wall/count) < .001)
    quantiles = [frame.get(k) for k in ('p50', 'p95', 'p99')]
    check('percentile_accounting', all(number(v, 0) and v > 0 for v in quantiles) and
          quantiles == sorted(quantiles) and number(wall) and quantiles[-1] <= wall*1000)
    check('p95_target', number(frame.get('p95')) and 0 < frame['p95'] <= 16.7)
    check('p99_target', number(frame.get('p99')) and 0 < frame['p99'] <= 33.3)
    long = r.get('long_frames')
    long = long if isinstance(long, dict) else {}
    counts = [long.get(k) for k in ('over50ms', 'over33_33ms', 'over16_67ms')]
    check('long_frame_accounting', all(integer(v) for v in counts) and integer(count, 1) and
          counts == sorted(counts) and counts[-1] <= count)
    check('present_mode_recorded', type(r.get('present_policy')) is str and bool(r['present_policy']))
    for key in ('engine_requested_inference', 'synthetic_chapter_ticks_used_for_fps', 'recording_enabled', 'gpu_debug_layer_observed'):
        check(key + '_disabled', r.get(key) is False)
    for key in ('gpu_debug_errors', 'gpu_debug_warnings'):
        check(key + '_zero', integer(r.get(key)) and r[key] == 0)
    setup = r.get('setup_readiness')
    setup = setup if isinstance(setup, dict) else {}
    check('foreground_setup', integer(setup.get('observations'), 1) and
          integer(setup.get('foreground_observations'), 1) and
          setup['foreground_observations'] <= setup['observations'] and
          setup.get('last_foreground') is True and setup.get('last_minimized') is False)
    # Native measured status means every sampled observation passed the runtime
    # active-context guard. This is a report assertion, not an OS input trace.
    check('zero_dropped_simulation', number(r.get('dropped_simulation_seconds')) and r['dropped_simulation_seconds'] == 0)
    for group in ('working_set_bytes', 'private_bytes', 'scene_content_gpu_bytes'):
        values = r.get(group)
        values = values if isinstance(values, dict) else {}
        check(group + '_accounting', all(integer(values.get(k)) for k in ('start', 'end', 'maximum_sampled')) and
              values['maximum_sampled'] >= max(values['start'], values['end']))
    working = r.get('working_set_bytes')
    working = working if isinstance(working, dict) else {}
    check('sampled_working_set_target', integer(working.get('maximum_sampled')) and working['maximum_sampled'] <= 4*1024**3)
    for key in ('measured_reading_frames', 'measured_inspection_frames', 'measured_saving_frames'):
        check(key + '_accounting', integer(r.get(key)) and integer(count, 1) and r[key] <= count)
    check('post_measurement_capture', r.get('capture_is_after_measurement') is True and integer(r.get('capture_nonbackground_pixels'), 1))
    outcome = r.get('opening_outcomes')
    outcome = outcome if isinstance(outcome, dict) else {}
    outcome_coherent = (outcome.get('first_route') in ('none', 'repair', 'bypass', 'alternative') and
                        type(outcome.get('shelter_secured')) is bool and type(outcome.get('pencil_visited')) is bool and
                        (not outcome['pencil_visited'] or outcome['shelter_secured']) and
                        outcome['shelter_secured'] == (outcome['first_route'] != 'none'))
    check('outcome_schema', outcome_coherent)
    scene = r.get('scene_content_gpu_bytes')
    scene = scene if isinstance(scene, dict) else {}
    scene_under_soft_cap = integer(scene.get('maximum_sampled')) and scene['maximum_sampled'] <= 8*1024**3
    # The reported scene allocation count excludes depth/swapchain/driver heaps.
    # It cannot be promoted to total process residency or current DXGI budget.
    missing = ['measured_interval_representative_route_activity',
               'process_gpu_residency_and_adapter_pressure', 'current_dxgi_budget',
               'separate_game_and_physics_timing', 'reload_and_transition_memory_trends']
    timing_pass = all(checks.values())
    return dict(schema_version=1, status='incomplete' if timing_pass else 'failed_available_checks',
                gate_pass=False, timing_pass=timing_pass, coverage_pass=False,
                checks=checks, failures=errors, missing_evidence=missing,
                metrics=dict(measured_wall_seconds=wall, frame_count=count, fps=fps,
                             frame_ms=frame, long_frames=long, working_set_bytes=working,
                             scene_content_gpu_bytes=scene),
                coverage=dict(final_opening_outcomes=outcome, final_outcomes_coherent=outcome_coherent,
                              representative_route_verified=False,
                              activity_interval='not_recorded_in_native_v1_aggregate',
                              foreground_evidence='native measured-status per-sample active guard plus setup report; no independent OS input trace'),
                gpu=dict(soft_cap_bytes=8*1024**3, scene_allocations_under_soft_cap=scene_under_soft_cap,
                         process_residency_verified=False, current_dxgi_budget_verified=False,
                         budget_pass=None),
                close=dict(normal_player_close=r.get('normal_player_close'),
                           saved_close_complete=r.get('saved_close_complete'),
                           timer_close_permitted=True),
                limitations=['Aggregate report assessment; no executable provenance or independent report authenticity verification',
                             'Zero dropped simulation is available evidence, not a separately recorded overload counter',
                             'Final route flags and start/end position cannot prove route activity during sampling',
                             'Scene GPU allocation bytes are not process residency; missing budget data holds the full gate'])
