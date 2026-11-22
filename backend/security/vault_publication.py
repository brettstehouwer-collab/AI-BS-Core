"""Explicit cooperative publication of already-staged private generations.

No root discovery, bootstrap, key generation, credential conversion or consumer
activation. Trusted host configuration must supply the protected root.
"""
from contextlib import ExitStack
from dataclasses import dataclass
from pathlib import Path
from security.vault_bundle import (VaultBundleError, _GENERATION, _HASH,
    _generation_snapshot, _private_directory, _read_member, load_private_generation)
from security.vault_compatibility import validate_candidate_compatibility


class VaultPublicationError(ValueError):
    def __init__(self, *, outcome='not_published'):
        super().__init__('Private selection was not confirmed; inspect retained state before another operation.')
        self.outcome = outcome


@dataclass(frozen=True)
class VaultPublicationReceipt:
    previous_generation: str
    generation: str
    status: str = 'published_and_read_back'
    compatibility_profile: str = 'legacy-env-raw-fernet-v1'
    encoding: str = ''
    authenticated_occurrences: int = 0


def publish_private_generation(root, generation, *, expected_generation, manifest_sha256, encoding=None):
    """Publish under the existing cooperative writer lock, with no automatic retry.

    Requires an existing valid selection. Does not bootstrap or grant permission
    to switch a live store. Explicit supported decoding and authenticated
    occurrence compatibility are mandatory. Hostile same-account writers are
    not sandboxed.
    """
    attempted = False
    try:
        if encoding not in {'utf-8', 'cp1252'}:
            raise VaultBundleError('Explicit supported configuration encoding is required.')
        for value in (generation, expected_generation):
            if not isinstance(value, str) or not _GENERATION.fullmatch(value):
                raise VaultBundleError('Invalid publication generation.')
        if generation == expected_generation or not isinstance(manifest_sha256, str) or not _HASH.fullmatch(manifest_sha256):
            raise VaultBundleError('An exact distinct candidate is required.')
        path = Path(root)
        if not path.is_absolute() or '..' in path.parts or str(path).startswith(('\\\\', '//')):
            raise VaultBundleError('An explicit local private root is required.')
        from security.contained_file_access import _pinned_directory
        from core.coding_locks import record_lock
        from core.coding_journal import write_json_record
        with ExitStack() as stack:
            directory = stack.enter_context(_pinned_directory(path))
            _private_directory(directory)
            lock = directory/'publication.lock'
            # Callers own this private cooperative namespace. Reject an existing
            # redirected/hardlinked/nonprivate lock before using the frozen lock.
            if lock.exists() or lock.is_symlink():
                with _read_member(directory, lock.name, 1): pass
            stack.enter_context(record_lock(lock))
            previous = load_private_generation(directory, expected_generation=expected_generation)
            pinned_previous, _ = _generation_snapshot(stack, directory, expected_generation)
            if pinned_previous != previous:
                raise VaultBundleError('Previous generation changed during admission.')
            candidate, digest = _generation_snapshot(stack, directory, generation)
            if digest != manifest_sha256:
                raise VaultBundleError('Candidate manifest changed.')
            compatibility = validate_candidate_compatibility(pinned_previous, candidate, encoding=encoding)
            # Revalidate the expected selection inside the writer lock. Candidate
            # member handles remain held across the atomic selector replacement.
            if load_private_generation(directory, expected_generation=expected_generation) != pinned_previous:
                raise VaultBundleError('Previous selection changed during admission.')
            attempted = True
            write_json_record(directory/'current.json', {'schema': 1, 'generation': generation}, retry_seconds=0)
            confirmed = load_private_generation(directory, expected_generation=generation)
            if confirmed != candidate:
                raise VaultBundleError('Publication readback changed.')
            return VaultPublicationReceipt(expected_generation, generation,
                compatibility_profile=compatibility.profile, encoding=encoding,
                authenticated_occurrences=compatibility.authenticated_occurrences)
    except Exception:
        raise VaultPublicationError(outcome='unknown' if attempted else 'not_published') from None
