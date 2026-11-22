"""Read-only WDDM local-memory sampling of an existing owned subprocess.Popen.

    with GpuMemorySampler(child, interval_seconds=0.1) as gpu:
        child.wait(timeout=60)
    evidence = gpu.report()

The caller retains ownership of the child and its process handle. No process is
opened by PID, no memory reservation is changed, and no foreground APIs are used.
Each usage/budget pair comes from one D3DKMTQueryVideoMemoryInfo call. Samples are
per adapter LUID/physical node; neither summed residency nor whole-run maxima are
inferred. Native scene-resource counters remain a separate measurement.

ABI: Windows SDK 10.0.26100.0/shared/d3dkmthk.h (x64). Reference:
https://learn.microsoft.com/en-us/windows-hardware/drivers/ddi/d3dkmthk/ns-d3dkmthk-_d3dkmt_queryvideomemoryinfo
"""
import copy
import ctypes as C
import os
import subprocess
import threading
import time

U32 = C.c_uint32
I32 = C.c_int32
U64 = C.c_uint64


class _Luid(C.Structure):
    _fields_ = [('low', U32), ('high', I32)]


class _Adapter(C.Structure):
    _fields_ = [('handle', U32), ('luid', _Luid), ('sources', U32), ('precise', I32)]


class _Enum(C.Structure):
    _fields_ = [('count', U32), ('adapters', C.POINTER(_Adapter))]


class _Query(C.Structure):
    _fields_ = [('process', C.c_void_p), ('adapter', U32), ('segment_group', I32),
                ('budget', U64), ('usage', U64), ('reservation', U64),
                ('available_reservation', U64), ('physical_index', U32)]


class _Info(C.Structure):
    _fields_ = [('adapter', U32), ('kind', I32), ('data', C.c_void_p), ('size', U32)]


class _Close(C.Structure):
    _fields_ = [('adapter', U32)]


class _DeviceIds(C.Structure):
    _fields_ = [(name, U32) for name in ('physical_index', 'vendor_id', 'device_id',
        'subvendor_id', 'subsystem_id', 'revision_id', 'bus_type')]


def _status(code):
    return '0x%08X' % (int(code) & 0xFFFFFFFF)


class GpuMemorySampler:
    """Context manager; report() returns JSON-safe evidence, never raises for unavailable WDDM.

    Must be entered immediately around the caller's still-open owned Popen child.
    Stop/join the sampler before exiting the Popen context (which closes _handle).
    max_samples bounds retained adapter-node observations, not sample rounds.
    """
    def __init__(self, child, interval_seconds=0.1, max_samples=10000):
        if not isinstance(child, subprocess.Popen):
            raise TypeError('An actual caller-owned subprocess.Popen is required')
        if not 0.02 <= interval_seconds <= 10:
            raise ValueError('interval_seconds must be 0.02..10')
        if not isinstance(max_samples, int) or not 1 <= max_samples <= 100000:
            raise ValueError('max_samples must be 1..100000')
        self.child = child
        self.interval = float(interval_seconds)
        self.limit = max_samples
        self._stop = threading.Event()
        self._lock = threading.Lock()
        self._thread = None
        self._started = None
        self._ended = None
        self._entries = []
        self._data = {'schema': 'owned-process-wddm-local-v1', 'status': 'not_started',
            'pid': child.pid, 'process_handle_source': 'existing_owned_Popen._handle',
            'query_api': 'Gdi32!D3DKMTQueryVideoMemoryInfo', 'segment_group': 'LOCAL',
            'interval_seconds_requested': self.interval, 'samples': [], 'adapters': [],
            'problems': [], 'attempts': 0, 'successful_queries': 0, 'failed_queries': 0,
            'dropped_samples': 0, 'aggregate_usage_verified': False,
            'baseline_measured': False, 'whole_process_lifetime_coverage_verified': False,
            'rendering_adapter_identified': False,
            'limitations': ['Discrete observations can miss peaks and allocations between samples.',
                'Local WDDM process usage is separate from native scene-only resource counters.',
                'LUID identifies the queried adapter; the renderer adapter is not inferred.',
                'Multiple adapters/nodes are reported separately without summation.']}

    def _problem(self, where, detail):
        with self._lock:
            # Deduplicate persistent query failures; counters retain their frequency.
            item = {'where': where, 'detail': detail}
            if item not in self._data['problems'] and len(self._data['problems']) < 64:
                self._data['problems'].append(item)

    def __enter__(self):
        if self._started is not None:
            raise RuntimeError('Sampler is single-use')
        self._started = time.perf_counter()
        if os.name != 'nt' or C.sizeof(C.c_void_p) != 8:
            self._problem('platform', 'Requires 64-bit Windows Python; no fallback measurement')
            self._ended = time.perf_counter()
            return self
        try:
            # Fail before using an ABI with unexpected packing.
            if (C.sizeof(_Adapter), C.sizeof(_Enum), C.sizeof(_Query), C.sizeof(_Info)) != (20, 16, 56, 24):
                raise RuntimeError('Unexpected Windows SDK structure layout')
            handle = int(self.child._handle)
            if not handle or handle == -1 or self.child.poll() is not None:
                raise RuntimeError('Owned child is already terminal or its handle unavailable')
            self._handle = handle  # Borrowed; never CloseHandle/OpenProcess.
            self._gdi = C.WinDLL('gdi32.dll')
            for name, structure in (('D3DKMTEnumAdapters2', _Enum),
                                    ('D3DKMTQueryVideoMemoryInfo', _Query),
                                    ('D3DKMTQueryAdapterInfo', _Info),
                                    ('D3DKMTCloseAdapter', _Close)):
                fn = getattr(self._gdi, name)
                fn.argtypes = [C.POINTER(structure)]
                fn.restype = I32
            self._enumerate()
            if self._entries:
                self._thread = threading.Thread(target=self._worker, name='owned-player-wddm-sampler', daemon=True)
                self._thread.start()
            else:
                self._ended = time.perf_counter()
        except Exception as exc:
            self._problem('setup', type(exc).__name__ + ': ' + str(exc))
            self._close_adapters()
            self._ended = time.perf_counter()
        return self

    def _enumerate(self):
        first = _Enum()
        status = self._gdi.D3DKMTEnumAdapters2(C.byref(first))
        if status < 0 or not 0 < first.count <= 64:
            raise RuntimeError('Adapter-count query failed: ' + _status(status) + ', count=' + str(first.count))
        array = (_Adapter * first.count)()
        request = _Enum(first.count, array)
        status = self._gdi.D3DKMTEnumAdapters2(C.byref(request))
        # Remember every returned valid handle before further validation so it is closed.
        self._adapters = [array[n] for n in range(min(request.count, len(array))) if array[n].handle]
        if status < 0 or request.count > len(array):
            raise RuntimeError('Adapter enumeration changed/failed: ' + _status(status))
        for adapter in self._adapters:
            luid = '%08X:%08X' % (adapter.luid.high & 0xFFFFFFFF, adapter.luid.low)
            count = U32()
            info = _Info(adapter.handle, 30, C.cast(C.pointer(count), C.c_void_p), C.sizeof(count))
            status = self._gdi.D3DKMTQueryAdapterInfo(C.byref(info))
            known_count = status >= 0 and 0 < count.value <= 32
            indices = range(count.value) if known_count else range(1)
            if not known_count:
                self._problem(luid + '/physical_count', _status(status) + '; index0 only, physical coverage unverified')
            description = {'luid': luid, 'display_source_count': adapter.sources,
                'physical_adapter_count': count.value if known_count else None,
                'physical_index_coverage_verified': known_count,
                'gpu_model_name': None, 'physical_device_ids': []}
            self._data['adapters'].append(description)
            for index in indices:
                ids = _DeviceIds()
                ids.physical_index = index
                request = _Info(adapter.handle, 31, C.cast(C.pointer(ids), C.c_void_p), C.sizeof(ids))
                identity_status = self._gdi.D3DKMTQueryAdapterInfo(C.byref(request))
                description['physical_device_ids'].append({'physical_adapter_index': index,
                    'ntstatus': _status(identity_status), 'verified': identity_status >= 0,
                    'ids': {field: getattr(ids, field) for field, _ in ids._fields_[1:]} if identity_status >= 0 else None})
                self._entries.append((adapter.handle, luid, index))

    def _close_adapters(self):
        for adapter in getattr(self, '_adapters', ()):
            try:
                result = self._gdi.D3DKMTCloseAdapter(C.byref(_Close(adapter.handle)))
                if result < 0:
                    self._problem('close_adapter', _status(result))
            except Exception as exc:
                self._problem('close_adapter', type(exc).__name__ + ': ' + str(exc))
        self._adapters = []

    def _worker(self):
        try:
            while not self._stop.is_set() and self.child.poll() is None:
                round_start = time.perf_counter()
                for adapter, luid, physical in self._entries:
                    if self._stop.is_set() or self.child.poll() is not None:
                        break
                    begin = time.perf_counter()
                    query = _Query()
                    query.process = self._handle
                    query.adapter = adapter
                    query.segment_group = 0  # D3DKMT_MEMORY_SEGMENT_GROUP_LOCAL
                    query.physical_index = physical
                    status = self._gdi.D3DKMTQueryVideoMemoryInfo(C.byref(query))
                    end = time.perf_counter()
                    sample = {'luid': luid, 'physical_adapter_index': physical,
                        'offset_seconds': begin - self._started, 'query_seconds': end - begin,
                        'ntstatus': _status(status), 'success': status >= 0}
                    if status >= 0:
                        sample.update(budget_bytes=query.budget, current_usage_bytes=query.usage,
                            current_reservation_bytes=query.reservation,
                            available_for_reservation_bytes=query.available_reservation,
                            usage_over_budget=(query.usage > query.budget))
                    with self._lock:
                        self._data['attempts'] += 1
                        self._data['successful_queries' if status >= 0 else 'failed_queries'] += 1
                        if len(self._data['samples']) < self.limit:
                            self._data['samples'].append(sample)
                        else:
                            self._data['dropped_samples'] += 1
                    if status < 0:
                        self._problem(luid + '/' + str(physical), 'QueryVideoMemoryInfo ' + _status(status))
                self._stop.wait(max(0, self.interval - (time.perf_counter() - round_start)))
        except Exception as exc:
            self._problem('worker', type(exc).__name__ + ': ' + str(exc))
        finally:
            self._close_adapters()
            self._ended = time.perf_counter()

    def __exit__(self, *_):
        self.stop()

    def stop(self):
        self._stop.set()
        if self._thread is not None:
            self._thread.join(timeout=5)
            if self._thread.is_alive():
                self._problem('stop', 'Sampler thread did not join within5seconds; native query may be stalled')
        if self._ended is None and (self._thread is None or not self._thread.is_alive()):
            self._ended = time.perf_counter()

    def report(self):
        with self._lock:
            result = copy.deepcopy(self._data)
        result['thread_joined'] = self._thread is None or not self._thread.is_alive()
        result['sampler_duration_seconds'] = ((self._ended or time.perf_counter()) - self._started) if self._started else None
        groups = {}
        for sample in result['samples']:
            key = sample['luid'] + '/' + str(sample['physical_adapter_index'])
            group = groups.setdefault(key, {'luid': sample['luid'], 'physical_adapter_index': sample['physical_adapter_index'],
                'successful_samples': 0, 'failed_samples': 0, 'sampled_peak_usage_pair': None,
                'first_success_offset_seconds': None, 'last_success_offset_seconds': None, 'maximum_observed_success_gap_seconds': None})
            if not sample['success']:
                group['failed_samples'] += 1
                continue
            previous = group['last_success_offset_seconds']
            if previous is not None:
                group['maximum_observed_success_gap_seconds'] = max(group['maximum_observed_success_gap_seconds'] or 0, sample['offset_seconds'] - previous)
            group['successful_samples'] += 1
            group['last_success_offset_seconds'] = sample['offset_seconds']
            if group['first_success_offset_seconds'] is None:
                group['first_success_offset_seconds'] = sample['offset_seconds']
            pair = group['sampled_peak_usage_pair']
            if pair is None or sample['current_usage_bytes'] > pair['current_usage_bytes']:
                group['sampled_peak_usage_pair'] = dict(sample)
        result['per_adapter_physical_node'] = list(groups.values())
        good = result['successful_queries'] > 0
        result['status'] = ('sampled' if good and not result['failed_queries'] and not result['problems']
                            and not result['dropped_samples'] and result['thread_joined'] else 'partial' if good else 'unavailable')
        result['observed_positive_usage_luids'] = sorted({s['luid'] for s in result['samples'] if s['success'] and s['current_usage_bytes'] > 0})
        return result
