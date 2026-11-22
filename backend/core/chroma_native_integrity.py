"""Bounded, read-only validation of persisted Chroma HNSW files.

Only the observed 100-byte, 64-bit persistence-v1 layout is understood.
No SQLite, Chroma, native library, model or pickle is opened or executed.
Passing these checks never establishes native query health or complete recovery.

Format reference: chroma-core/hnswlib, hnswlib/hnswalg.h
(HEADER_FIELDS, loadLinkLists, isMarkedDeleted and normalization storage).
"""
from array import array
from contextlib import ExitStack, contextmanager
from pathlib import Path
import os
import stat
import struct


HEADER = struct.Struct("<iQQQQQQiIQQQdQ")
REQUIRED_FILES = ("header.bin", "data_level0.bin", "length.bin", "link_lists.bin")
REPARSE_POINT = getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400)
LIMITS = (
    "Known 64-bit HNSW persistence-v1 format checks only. Passing does not "
    "establish native query health, collection ownership, authoritative vector "
    "completeness, or permission to start a service."
)


class _Issue(Exception):
    def __init__(self, code, status="CORRUPT", **details):
        super().__init__(code)
        self.code, self.status, self.details = code, status, details


def _result():
    return {
        "format": "HNSW_PERSISTENCE_V1_64BIT",
        "status": "UNVERIFIED",
        "known_format_checks_pass": False,
        "errors": [],
        "native_runtime_tested": False,
        "data_recovery_complete": False,
        "limits": LIMITS,
    }


def _stat_path(path):
    return Path(path).stat(follow_symlinks=False)


def _reparse(info):
    return stat.S_ISLNK(info.st_mode) or bool(getattr(info, "st_file_attributes", 0) & REPARSE_POINT)


def _identity(info):
    return info.st_dev, info.st_ino, stat.S_IFMT(info.st_mode)


def _stamp(info):
    return _identity(info) + (info.st_size, info.st_mtime_ns, info.st_ctime_ns)


def _cross_api_stamp(info):
    # Windows Python 3.12 path-stat and fd-stat expose different ctime
    # semantics. Compare ctime only within the same API before/after; identity,
    # byte count and last-write time remain comparable across both APIs.
    return _identity(info) + (info.st_size, info.st_mtime_ns)


def _ancestors(directory):
    root = Path(os.path.abspath(os.fspath(directory)))
    snapshots = {}
    for path in (root, *root.parents):
        info = _stat_path(path)
        if _reparse(info):
            raise _Issue("LINK_NOT_ALLOWED", "UNSUPPORTED")
        if not stat.S_ISDIR(info.st_mode):
            raise _Issue("DIRECTORY_REQUIRED", "UNVERIFIED")
        snapshots[path] = _identity(info)
    return root, snapshots


def _unchanged_directories(snapshots):
    for path, previous in snapshots.items():
        now = _stat_path(path)
        if _reparse(now) or _identity(now) != previous:
            return False
    return True


def _read_exact(stream, count):
    value = stream.read(count)
    if len(value) != count:
        raise EOFError("SHORT_READ")
    return value


def _checked_read(stream, count):
    value = _read_exact(stream, count)
    if len(value) != count:
        raise EOFError("SHORT_READ")
    return value


def _error(result, code, **details):
    result["errors"].append({"code": code, **details})


def _budget(value, maximum, name):
    if value > maximum:
        raise _Issue("INSPECTION_LIMIT", "UNVERIFIED", budget=name, required=value, maximum=maximum)


def _valid_limit(value):
    return isinstance(value, int) and not isinstance(value, bool) and value > 0


@contextmanager
def _open_sources(directory, max_file_bytes, max_total_bytes):
    root, ancestors = _ancestors(directory)
    before = {}
    for name in REQUIRED_FILES:
        try:
            info = _stat_path(root / name)
        except FileNotFoundError:
            raise _Issue("REQUIRED_FILE_MISSING", file=name) from None
        if _reparse(info):
            raise _Issue("LINK_NOT_ALLOWED", "UNSUPPORTED", file=name)
        if not stat.S_ISREG(info.st_mode):
            raise _Issue("REGULAR_FILE_REQUIRED", "UNSUPPORTED", file=name)
        _budget(info.st_size, max_file_bytes, "max_file_bytes")
        before[name] = info
    _budget(sum(info.st_size for info in before.values()), max_total_bytes, "max_total_bytes")
    with ExitStack() as cleanup:
        streams = {}
        opened_stamps = {}
        flags = os.O_RDONLY | getattr(os, "O_BINARY", 0) | getattr(os, "O_NOFOLLOW", 0)
        for name in REQUIRED_FILES:
            descriptor = os.open(root / name, flags)
            try:
                stream = os.fdopen(descriptor, "rb")
            except BaseException:
                os.close(descriptor)
                raise
            cleanup.enter_context(stream)
            opened = os.fstat(stream.fileno())
            if _cross_api_stamp(opened) != _cross_api_stamp(before[name]):
                raise _Issue("INSPECTION_CHANGED", "UNVERIFIED")
            opened_stamps[name] = _stamp(opened)
            streams[name] = stream
        try:
            yield streams, before
        finally:
            changed = False
            try:
                for name, stream in streams.items():
                    now = _stat_path(root / name)
                    if (_reparse(now) or _stamp(now) != _stamp(before[name])
                            or _stamp(os.fstat(stream.fileno())) != opened_stamps[name]):
                        changed = True
                changed = changed or not _unchanged_directories(ancestors)
            except OSError:
                changed = True
            if changed:
                raise _Issue("INSPECTION_CHANGED", "UNVERIFIED")


def _scan_open_files(result, streams, sizes, expected_dimension, budgets):
    if sizes["header.bin"].st_size != HEADER.size:
        raise _Issue("UNSUPPORTED_HEADER_SIZE", "UNSUPPORTED", bytes=sizes["header.bin"].st_size)
    (version, level0, capacity, count, size, label_offset, vector_offset,
     max_level, entry, max_m, max_m0, _m, _mult, _ef) = HEADER.unpack(_checked_read(streams["header.bin"], HEADER.size))
    result.update(records=count, capacity=capacity, record_bytes=size, max_level=max_level)
    if version != 1:
        raise _Issue("UNSUPPORTED_PERSISTENCE_VERSION", "UNSUPPORTED", version=version)
    if count > capacity or max_m < 1 or max_m0 < 1 or size < 1 or (count and max_level < 0):
        raise _Issue("HEADER_BOUND")
    _budget(capacity, budgets["max_records"], "max_records")
    _budget(size, budgets["max_record_bytes"], "max_record_bytes")
    _budget(max_m, 4096, "maximum_upper_neighbors")
    _budget(max_m0, 8192, "maximum_level0_neighbors")
    _budget(max(0, max_level), budgets["max_upper_levels"], "max_upper_levels")
    if not (level0 + 4 + max_m0 * 4 <= vector_offset <= label_offset
            and label_offset + 8 <= size and (label_offset - vector_offset) % 4 == 0):
        raise _Issue("RECORD_LAYOUT")
    dimension = (label_offset - vector_offset) // 4
    result["dimension"] = dimension
    if expected_dimension is not None and dimension != expected_dimension:
        _error(result, "DIMENSION_MISMATCH", expected=expected_dimension, actual=dimension)
    normalization_bytes = sizes["length.bin"].st_size
    if not (count * 4 <= normalization_bytes <= capacity * 4) or normalization_bytes % 4:
        _error(result, "NORMALIZATION_STORAGE_SIZE")
    # length.bin contains float normalization storage. Its arbitrary unused L2
    # values are not interpreted as unsigned counts or link-list byte lengths.
    data_bytes = sizes["data_level0.bin"].st_size
    if not (count * size <= data_bytes <= capacity * size) or data_bytes % size:
        _error(result, "LEVEL0_STORAGE_SIZE")
        return

    labels = {}
    duplicate_records = duplicate_labels = deleted = bad_counts = bad_neighbors = 0
    for _ in range(count):
        record = _checked_read(streams["data_level0.bin"], size)
        links = struct.unpack_from("<H", record, level0)[0]
        is_deleted = bool(record[level0 + 2] & 1)
        label = struct.unpack_from("<Q", record, label_offset)[0]
        if label not in labels:
            _budget(len(labels) + 1, budgets["max_label_entries"], "max_label_entries")
            labels[label] = 0
        if is_deleted:
            deleted += 1
        else:
            if labels[label] >= 1:
                duplicate_records += 1
                duplicate_labels += labels[label] == 1
            labels[label] += 1
        if links > max_m0:
            bad_counts += 1
            continue
        for (neighbor,) in struct.iter_unpack("<I", memoryview(record)[level0 + 4:level0 + 4 + links * 4]):
            bad_neighbors += neighbor >= count
    result.update(active_duplicate_records=duplicate_records, active_duplicate_labels=duplicate_labels,
                  unique_labels=len(labels), deleted_records=deleted)
    if duplicate_records:
        _error(result, "DUPLICATE_ACTIVE_LABELS", records=duplicate_records)
    if bad_counts:
        _error(result, "LEVEL0_LINK_COUNT", records=bad_counts)
    if bad_neighbors:
        _error(result, "LEVEL0_NEIGHBOR_BOUND", edges=bad_neighbors)

    # First pass stores only bounded node levels, never an edge list. A second
    # sequential pass validates target levels once every node's level is known.
    upper = streams["link_lists.bin"]
    total = sizes["link_lists.bin"].st_size
    per_level = 4 + max_m * 4
    levels = array("H")
    bad_counts = bad_neighbors = 0
    for index in range(count):
        offset = upper.tell()
        if total - offset < 4:
            _error(result, "UPPER_LINK_PREFIX_TRUNCATED", internal_id=index)
            break
        length = struct.unpack("<I", _checked_read(upper, 4))[0]
        if length % per_level or length > max(0, max_level) * per_level or length > total - upper.tell():
            _error(result, "UPPER_LINK_LENGTH", internal_id=index, offset=offset,
                   declared_bytes=length, per_level_bytes=per_level)
            break
        _budget(length, budgets["max_upper_bytes_per_node"], "max_upper_bytes_per_node")
        level = length // per_level
        levels.append(level)
        payload = _checked_read(upper, length)
        for current in range(level):
            offset_in_node = current * per_level
            n = struct.unpack_from("<H", payload, offset_in_node)[0]
            if n > max_m:
                bad_counts += 1
                continue
            for (neighbor,) in struct.iter_unpack("<I", memoryview(payload)[offset_in_node + 4:offset_in_node + 4 + n * 4]):
                bad_neighbors += neighbor >= count
    result["upper_records_parsed"] = len(levels)
    if bad_counts:
        _error(result, "UPPER_LINK_COUNT", records=bad_counts)
    if bad_neighbors:
        _error(result, "UPPER_NEIGHBOR_BOUND", edges=bad_neighbors)
    if len(levels) != count:
        return
    if upper.tell() != total:
        _error(result, "UPPER_LINK_TRAILING_BYTES")
    if count and (entry >= count or levels[entry] != max_level):
        _error(result, "ENTRYPOINT_LEVEL")
    upper.seek(0)
    missing_levels = 0
    for _ in range(count):
        length = struct.unpack("<I", _checked_read(upper, 4))[0]
        _budget(length, budgets["max_upper_bytes_per_node"], "max_upper_bytes_per_node")
        if length % per_level or length > max(0, max_level) * per_level:
            raise _Issue("INSPECTION_CHANGED", "UNVERIFIED")
        payload = _checked_read(upper, length)
        for current in range(length // per_level):
            offset = current * per_level
            n = struct.unpack_from("<H", payload, offset)[0]
            if n > max_m:
                continue
            for (neighbor,) in struct.iter_unpack("<I", memoryview(payload)[offset + 4:offset + 4 + n * 4]):
                if neighbor < count and levels[neighbor] < current + 1:
                    missing_levels += 1
    if missing_levels:
        _error(result, "UPPER_NEIGHBOR_LEVEL", edges=missing_levels)


def inspect_hnsw_segment(directory, expected_dimension=None, *, max_records=2_000_000,
                         max_file_bytes=1 << 30, max_total_bytes=2 << 30,
                         max_record_bytes=1 << 20, max_upper_bytes_per_node=1 << 16,
                         max_upper_levels=128, max_label_entries=250_000):
    """Inspect bounded binary invariants; never open a native client or mutate."""
    result = _result()
    budgets = dict(max_records=max_records, max_record_bytes=max_record_bytes,
                   max_upper_bytes_per_node=max_upper_bytes_per_node,
                   max_upper_levels=max_upper_levels, max_label_entries=max_label_entries)
    try:
        if not all(_valid_limit(x) for x in (*budgets.values(), max_file_bytes, max_total_bytes)):
            raise _Issue("INSPECTION_LIMIT", "UNVERIFIED", budget="invalid_configuration")
        with _open_sources(directory, max_file_bytes, max_total_bytes) as (streams, sizes):
            _scan_open_files(result, streams, sizes, expected_dimension, budgets)
        result["status"] = "CORRUPT" if result["errors"] else "STATIC_CHECKS_PASS"
    except _Issue as issue:
        _error(result, issue.code, **issue.details)
        result["status"] = issue.status
    except (EOFError, struct.error):
        _error(result, "SHORT_OR_CHANGED_READ")
        result["status"] = "UNVERIFIED"
    except OSError as issue:
        _error(result, "IO_ERROR", error_type=type(issue).__name__)
        result["status"] = "UNVERIFIED"
    result["known_format_checks_pass"] = result["status"] == "STATIC_CHECKS_PASS"
    return result


def _store_inventory(root, max_segments, max_directory_entries, max_store_bytes):
    """Bounded membership/identity snapshot, including unmaterialized dirs.

    Required-file presence is recorded for every immediate directory. An empty
    directory gaining a persisted index must not escape the post-scan check.
    """
    candidates = []
    entries_by_name = {}
    snapshots = {}
    byte_count = 0
    with os.scandir(root) as entries:
        for count, entry in enumerate(entries, 1):
            _budget(count, max_directory_entries, "max_directory_entries")
            path = root / entry.name
            info = _stat_path(path)
            if _reparse(info):
                raise _Issue("LINK_NOT_ALLOWED", "UNSUPPORTED")
            entries_by_name[entry.name] = _identity(info)
            if not stat.S_ISDIR(info.st_mode):
                continue
            files = {}
            for name in REQUIRED_FILES:
                try:
                    item = _stat_path(path / name)
                except FileNotFoundError:
                    continue
                if _reparse(item):
                    raise _Issue("LINK_NOT_ALLOWED", "UNSUPPORTED", file=name)
                files[path / name] = _stamp(item)
                byte_count += item.st_size
            if files:
                _budget(len(candidates) + 1, max_segments, "max_segments")
                _budget(byte_count, max_store_bytes, "max_store_bytes")
                candidates.append(path)
                snapshots.update(files)
    return candidates, entries_by_name, snapshots


def inspect_chroma_store(directory, *, max_segments=10_000, max_directory_entries=20_000,
                         max_store_bytes=4 << 30, **segment_budgets):
    """Inspect immediate persisted-index directories without opening SQLite."""
    result = _result()
    result.update(segments=[], sqlite_opened=False, persisted_segments=0)
    result["limits"] = (LIMITS + " No SQL-to-segment ownership is inferred; "
                        "unmaterialized directories require separate metadata review.")
    try:
        if not all(_valid_limit(v) for v in (max_segments, max_directory_entries, max_store_bytes)):
            raise _Issue("INSPECTION_LIMIT", "UNVERIFIED", budget="invalid_store_configuration")
        root, ancestors = _ancestors(directory)
        database = _stat_path(root / "chroma.sqlite3")
        if _reparse(database):
            raise _Issue("LINK_NOT_ALLOWED", "UNSUPPORTED", file="chroma.sqlite3")
        if not stat.S_ISREG(database.st_mode):
            raise _Issue("CHROMA_DATABASE_FILE_ABSENT", "UNVERIFIED")
        candidates, entries_by_name, snapshots = _store_inventory(
            root, max_segments, max_directory_entries, max_store_bytes)
        for path in sorted(candidates):
            result["segments"].append({"directory": path.name, **inspect_hnsw_segment(path, **segment_budgets)})
        try:
            _, current_entries, current_files = _store_inventory(
                root, max_segments, max_directory_entries, max_store_bytes)
        except (OSError, _Issue):
            raise _Issue("INSPECTION_CHANGED", "UNVERIFIED") from None
        if entries_by_name != current_entries or snapshots != current_files:
            raise _Issue("INSPECTION_CHANGED", "UNVERIFIED")
        if not _unchanged_directories(ancestors):
            raise _Issue("INSPECTION_CHANGED", "UNVERIFIED")
        if not candidates:
            raise _Issue("NO_PERSISTED_SEGMENTS", "UNVERIFIED")
        statuses = {item["status"] for item in result["segments"]}
        result["status"] = ("CORRUPT" if "CORRUPT" in statuses else "UNVERIFIED"
                            if statuses & {"UNVERIFIED", "UNSUPPORTED"} else "STATIC_CHECKS_PASS")
    except _Issue as issue:
        _error(result, issue.code, **issue.details)
        result["status"] = issue.status
    except OSError as issue:
        _error(result, "IO_ERROR", error_type=type(issue).__name__)
        result["status"] = "UNVERIFIED"
    result["persisted_segments"] = len(result["segments"])
    result["known_format_checks_pass"] = result["status"] == "STATIC_CHECKS_PASS"
    return result
