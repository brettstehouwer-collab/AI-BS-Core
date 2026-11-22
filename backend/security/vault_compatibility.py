"""Pure raw-Fernet configuration compatibility; no filesystem or publication.

Explicit encoding and exact non-token bytes preserve the inspected legacy
root-then-backend reader semantics. Unknown token variants fail closed.
"""
from dataclasses import dataclass, field
import hashlib
import hmac
import re
from cryptography.fernet import Fernet
from security.vault_bundle import VaultGeneration


class VaultCompatibilityError(ValueError):
    pass


@dataclass(frozen=True)
class VaultCompatibilityReceipt:
    previous_generation: str
    candidate_generation: str
    encoding: str
    authenticated_occurrences: int
    previous_snapshot_sha256: str = field(repr=False)
    candidate_snapshot_sha256: str = field(repr=False)
    profile: str = 'legacy-env-raw-fernet-v1'


def _identity(snapshot):
    digest = hashlib.sha256()
    for raw in (snapshot.generation.encode('ascii'), snapshot.key, snapshot.root_config, snapshot.backend_config):
        digest.update(len(raw).to_bytes(8, 'big'))
        digest.update(raw)
    return digest.hexdigest()


def _snapshot(value):
    if not isinstance(value, VaultGeneration) or not isinstance(value.generation, str) or not re.fullmatch('[0-9a-f]{32}', value.generation):
        raise VaultCompatibilityError('Invalid private snapshot.')
    for raw, limit in [(value.key, 44), (value.root_config, 2*1024*1024), (value.backend_config, 2*1024*1024)]:
        if type(raw) is not bytes or len(raw) > limit:
            raise VaultCompatibilityError('Private snapshot exceeds the supported profile.')
    return Fernet(value.key)


def _lines(raw, encoding):
    text = raw.decode(encoding, errors='strict')
    if any(ch in text for ch in ('\v', '\f', '\x1c', '\x1d', '\x1e', '\x85', '\u2028', '\u2029')):
        raise VaultCompatibilityError('Unsupported configuration line separator.')
    return text.splitlines(keepends=True)


def _token_line(line):
    if '=' not in line or line.startswith('#'):
        return None
    body = line.rstrip('\r\n')
    ending = line[len(body):]
    prefix, value = body.split('=', 1)
    head = value.rstrip()
    trailing = value[len(head):]
    quoted = head.startswith('"gAAAAA') and head.endswith('"')
    if head.startswith('gAAAAA'):
        token, wrapper = head, ''
    elif quoted:
        token, wrapper = head[1:-1], '"'
    else:
        if head.lstrip(' \t\'"').startswith('gAAAAA'):
            raise VaultCompatibilityError('Unsupported quoted token variant.')
        return None
    if not re.fullmatch(r'gAAAAA[A-Za-z0-9_=-]+', token):
        raise VaultCompatibilityError('Unsupported token encoding.')
    return prefix+'=', wrapper, token, trailing, ending


def validate_candidate_compatibility(previous, candidate, *, encoding):
    """Authenticate each transformed occurrence; return no plaintext or authority.

    The receipt is private evidence, not operator approval or an execution grant.
    No effective-value dictionary is serialized or allowed to drop duplicates.
    """
    try:
        if encoding not in {'utf-8', 'cp1252'}:
            raise VaultCompatibilityError('An explicit supported encoding is required.')
        old_cipher, new_cipher = _snapshot(previous), _snapshot(candidate)
        if previous.generation == candidate.generation:
            raise VaultCompatibilityError('A distinct candidate generation is required.')
        authenticated = 0
        for old_raw, new_raw in [(previous.root_config, candidate.root_config),
                                 (previous.backend_config, candidate.backend_config)]:
            old_lines, new_lines = _lines(old_raw, encoding), _lines(new_raw, encoding)
            if len(old_lines) != len(new_lines):
                raise VaultCompatibilityError('Configuration occurrences changed.')
            for old_line, new_line in zip(old_lines, new_lines):
                old, new = _token_line(old_line), _token_line(new_line)
                if old is None:
                    if old_line != new_line or new is not None:
                        raise VaultCompatibilityError('Non-token configuration bytes changed.')
                    continue
                if new is None or (old[0], old[1], old[3], old[4]) != (new[0], new[1], new[3], new[4]):
                    raise VaultCompatibilityError('Token wrapper, source order or surrounding bytes changed.')
                old_token, new_token = old[2].encode('ascii'), new[2].encode('ascii')
                old_plain, new_plain = old_cipher.decrypt(old_token), new_cipher.decrypt(new_token)
                if not hmac.compare_digest(old_plain, new_plain):
                    raise VaultCompatibilityError('Authenticated configuration value changed.')
                del old_plain, new_plain
                if old_cipher.extract_timestamp(old_token) != new_cipher.extract_timestamp(new_token):
                    raise VaultCompatibilityError('Authenticated token timestamp changed.')
                authenticated += 1
                if authenticated > 20000:
                    raise VaultCompatibilityError('Too many token occurrences for this profile.')
        return VaultCompatibilityReceipt(previous.generation, candidate.generation, encoding,
            authenticated, _identity(previous), _identity(candidate))
    except VaultCompatibilityError:
        raise
    except Exception:
        raise VaultCompatibilityError('Private candidate compatibility could not be established.') from None
