"""Closed curated-opening asset manifest; stdlib only, no application imports.

Fast mode reads the bounded manifest/catalogs and checks paths, file shapes and
stat budgets. Full mode additionally verifies payload and native pack digests.
Typed decoding and decoded-residency checks remain the native factory's job.
"""
from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
import re
import uuid

OPENING_ROLES = ('capacitor', 'adam', 'nook', 'fault', 'bypass', 'shelter')
MANIFEST_LIMIT = 16 * 1024
PAYLOAD_LIMIT = 32 * 1024 * 1024
CLOSURE_LIMIT = 128 * 1024 * 1024
_SHA = re.compile(r'[0-9a-f]{64}\Z')


def plain_path(path, *, boundary=None, directory=False, file=False, fresh=False):
    """Reject redirection before resolving, including each existing ancestor."""
    path = Path(path).absolute()
    for ancestor in (path, *path.parents):
        if ancestor.is_symlink() or ancestor.is_junction():
            raise ValueError('Opening assets and outputs require plain local paths')
    resolved = path.resolve(strict=not fresh)
    if boundary is not None:
        try:
            resolved.relative_to(Path(boundary).resolve(strict=True))
        except ValueError as error:
            raise ValueError('Opening resource escaped its declared root') from error
    if directory and not resolved.is_dir():
        raise ValueError('Opening asset directory is missing')
    if file and not resolved.is_file():
        raise ValueError('Opening resource must be a regular file')
    if fresh and (path.exists() or not path.parent.is_dir() or not path.name):
        raise ValueError('Choose a new output child inside an existing directory')
    return resolved


def _pairs(items):
    result = {}
    for key, value in items:
        if key in result:
            raise ValueError('Duplicate curated-opening manifest key')
        result[key] = value
    return result


def bounded_json(raw, maximum=MANIFEST_LIMIT):
    if type(raw) is not bytes or not 1 <= len(raw) <= maximum:
        raise ValueError('Opening manifest exceeds its byte bound')
    def constant(value):
        raise ValueError('Nonfinite opening JSON value')
    return json.loads(raw.decode('utf-8', errors='strict'), object_pairs_hook=_pairs, parse_constant=constant)


def _read(path, maximum):
    with path.open('rb') as stream:
        raw = stream.read(maximum + 1)
    if not 1 <= len(raw) <= maximum:
        raise ValueError('Opening resource exceeds its bounded byte size')
    return raw


def _relative(value):
    if (type(value) is not str or not value or len(value.encode('utf-8', errors='strict')) > 512
            or '\\' in value or ':' in value or '\0' in value or value.startswith('/')
            or any(part in ('', '.', '..') for part in value.split('/'))):
        raise ValueError('Opening pack directory must be a bounded relative path without traversal')
    return value


def _reference(entry):
    identity, asset_sha, pack_sha = (entry.get(key) for key in ('asset_id', 'asset_sha256', 'pack_sha256'))
    try:
        valid = (type(identity) is str and str(uuid.UUID(identity)) == identity and uuid.UUID(identity).version == 4)
    except (ValueError, TypeError, AttributeError):
        valid = False
    if not valid or any(type(value) is not str or not _SHA.fullmatch(value) for value in (asset_sha, pack_sha)):
        raise ValueError('Opening pack requires a canonical v4 UUID and immutable lowercase SHA256 references')
    return identity, asset_sha, pack_sha


@dataclass(frozen=True)
class OpeningAsset:
    role: str
    relative_directory: str
    directory: Path
    payload: Path
    kind: str
    asset_id: str
    asset_sha256: str
    pack_sha256: str
    total_bytes: int

    @property
    def reference(self):
        return self.asset_id, self.asset_sha256, self.pack_sha256


@dataclass(frozen=True)
class OpeningAssetsBundle:
    root: Path
    manifest_path: Path
    manifest_bytes: bytes
    manifest_sha256: str
    roles: tuple[OpeningAsset, ...]
    total_bytes: int

    def role(self, name):
        return next(item for item in self.roles if item.role == name)


def _hash_bounded(path, size):
    digest = hashlib.sha256()
    total = 0
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(64 * 1024), b''):
            total += len(chunk)
            if total > size:
                raise ValueError('Opening pack changed during bounded hashing')
            digest.update(chunk)
    if total != size:
        raise ValueError('Opening pack changed during bounded hashing')
    return digest.hexdigest()


def read_opening_assets(root, *, verify_pack_contents=False):
    if type(verify_pack_contents) is not bool:
        raise ValueError('Opening content verification mode must be a typed boolean')
    root = plain_path(root, directory=True)
    manifest = plain_path(root / 'opening-assets.json', boundary=root, file=True)
    raw = _read(manifest, MANIFEST_LIMIT)
    value = bounded_json(raw)
    if (type(value) is not dict or set(value) != {'version', 'roles'}
            or type(value['version']) is not int or value['version'] != 1
            or type(value['roles']) is not dict or set(value['roles']) != set(OPENING_ROLES)):
        raise ValueError('Opening manifest requires version1 and exactly capacitor/adam/nook/fault/bypass/shelter')
    roles = []
    closure = 0
    for role in OPENING_ROLES:
        entry = value['roles'][role]
        if type(entry) is not dict or set(entry) != {'directory', 'asset_id', 'asset_sha256', 'pack_sha256'}:
            raise ValueError('Opening role requires exactly directory and its three immutable reference fields')
        identity, asset_sha, pack_sha = _reference(entry)
        relative = _relative(entry['directory'])
        directory = plain_path(root / relative, boundary=root, directory=True)
        members = []
        for child in directory.iterdir():
            if len(members) == 4:
                raise ValueError('Opening pack requires exactly four native files')
            members.append(plain_path(child, boundary=root, file=True))
        names = {path.name for path in members}
        suffixes = ('.aibchar',) if role == 'adam' else ('.aibmesh', '.aibsurf')
        payloads = [directory / (asset_sha + suffix) for suffix in suffixes if asset_sha + suffix in names]
        if len(payloads) != 1 or names != {'catalog.aibcat', 'LICENSE.txt', 'provenance.json', payloads[0].name}:
            raise ValueError('Opening role has an unexpected file, payload identity or asset type')
        payload = payloads[0]
        kind = {'.aibmesh': 'mesh', '.aibsurf': 'surface', '.aibchar': 'character'}[payload.suffix]
        sizes = {}
        for path in members:
            size = path.stat().st_size
            maximum = PAYLOAD_LIMIT if path == payload else 1024 * 1024 if path.name == 'catalog.aibcat' else 65536
            if not 1 <= size <= maximum:
                raise ValueError('Opening pack file exceeds its content-specific byte budget')
            sizes[path.name] = size
        total = sum(sizes.values())
        closure += total
        if total > 33 * 1024 * 1024 or closure > CLOSURE_LIMIT:
            raise ValueError('Opening pack or combined dependency closure exceeds its byte budget')
        header = b'AIBCAT 1\n' if kind == 'mesh' else ('AIBCAT 2\n' + kind + ' ').encode('ascii')
        expected = header + (identity + ' ' + asset_sha + ' ' + payload.name + '\n').encode('ascii')
        if _read(directory / 'catalog.aibcat', 1024 * 1024) != expected:
            raise ValueError('Opening catalog differs from its typed manifest reference')
        if verify_pack_contents:
            hashes = {path.name: _hash_bounded(path, sizes[path.name]) for path in members}
            if hashes[payload.name] != asset_sha:
                raise ValueError('Opening payload SHA256 differs from the curated manifest')
            native = 'AIBPACK 1\n' if kind == 'mesh' else 'AIBPACK 2\n'
            native += ''.join(name + ' ' + str(sizes[name]) + ' ' + hashes[name] + '\n' for name in sorted(names))
            if hashlib.sha256(native.encode('ascii')).hexdigest() != pack_sha:
                raise ValueError('Opening native pack digest differs from the curated manifest')
        roles.append(OpeningAsset(role, relative, directory, payload, kind, identity, asset_sha, pack_sha, total))
    return OpeningAssetsBundle(root, manifest, raw, hashlib.sha256(raw).hexdigest(), tuple(roles), closure)
