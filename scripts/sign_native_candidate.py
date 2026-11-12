"""Sign an explicitly pinned *new copy*. Never import keys or overwrite a release.

Certificate trust on this computer is a prerequisite, not recipient acceptance.
The backend is injectable for synthetic transaction tests; the CLI uses Windows.
"""
import argparse
from contextlib import contextmanager
import hashlib
import ipaddress
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
from urllib.parse import urlsplit


class SigningError(Exception):
    """Sanitized, bounded error code, never raw provider output."""


def _hash(stream):
    stream.seek(0)
    value = hashlib.sha256()
    for chunk in iter(lambda: stream.read(1024 * 1024), b''):
        value.update(chunk)
    stream.seek(0)
    return value.hexdigest()


def _plain_path(path):
    # Refuse junctions/symlinks rather than resolving through them silently.
    for part in (path, *path.parents):
        if os.path.lexists(part):
            info = part.lstat()
            if part.is_symlink() or getattr(info, 'st_file_attributes', 0) & 0x400:
                raise SigningError('REPARSE_PATH_REJECTED')


@contextmanager
def _read_locked(path):
    if os.name != 'nt':
        with path.open('rb') as stream:
            yield stream
        return
    # Deny concurrent writes/deletion while hashing/copying the pinned original.
    import ctypes
    from ctypes import wintypes
    import msvcrt
    kernel = ctypes.WinDLL('kernel32', use_last_error=True)
    kernel.CreateFileW.argtypes = [wintypes.LPCWSTR, wintypes.DWORD, wintypes.DWORD,
        wintypes.LPVOID, wintypes.DWORD, wintypes.DWORD, wintypes.HANDLE]
    kernel.CreateFileW.restype = wintypes.HANDLE
    handle = kernel.CreateFileW(str(path), 0x80000000, 1, None, 3, 0x00200000, None)
    if handle == ctypes.c_void_p(-1).value:
        raise SigningError('SOURCE_LOCK_UNAVAILABLE')
    try:
        fd = msvcrt.open_osfhandle(handle, os.O_RDONLY | os.O_BINARY)
    except Exception:
        kernel.CloseHandle.argtypes = [wintypes.HANDLE]
        kernel.CloseHandle(handle)
        raise SigningError('SOURCE_LOCK_UNAVAILABLE') from None
    with os.fdopen(fd, 'rb') as stream:
        yield stream


def windows_backend(mode, path, thumbprint, timestamp):
    if os.name != 'nt':
        raise SigningError('WINDOWS_REQUIRED')
    shell = Path(os.environ.get('SystemRoot', r'C:\Windows')) / 'System32/WindowsPowerShell/v1.0/powershell.exe'
    command = [str(shell), '-NoLogo', '-NoProfile', '-NonInteractive', '-File',
        str(Path(__file__).with_name('native_authenticode.ps1')), '-Mode', mode,
        '-TargetPath', str(path), '-Thumbprint', thumbprint, '-TimestampUrl', timestamp,
        '-ReceiptPath', str(path) + '.signing.json']
    try:
        result = subprocess.run(command, capture_output=True, timeout=180, check=False)
        if result.returncode:
            raise SigningError('WINDOWS_PROVIDER_FAILED')
        value = json.loads(result.stdout.decode('utf-8-sig'))
        if not isinstance(value, dict):
            raise ValueError()
        return value
    except SigningError:
        raise
    except Exception:
        raise SigningError('WINDOWS_PROVIDER_UNAVAILABLE') from None


def _timestamp(url):
    try:
        parts = urlsplit(url)
        host = (parts.hostname or '').lower()
        if (parts.scheme != 'https' or not host or parts.username is not None
                or parts.password is not None or parts.fragment or parts.port not in (None, 443)
                or host == 'localhost' or host.endswith(('.localhost', '.local'))
                or not re.fullmatch(r'[a-z0-9][a-z0-9.-]*[a-z0-9]', host)
                or '.' not in host or any(ord(c) < 33 for c in url)):
            raise ValueError()
        try:
            ipaddress.ip_address(host)
        except ValueError:
            pass
        else:
            raise ValueError()
    except (ValueError, TypeError):
        raise SigningError('INVALID_TIMESTAMP_URL') from None


def _write_receipt(stream, receipt):
    stream.seek(0)
    json.dump(receipt, stream, indent=2, sort_keys=True)
    stream.write('\n')
    stream.truncate()
    stream.flush()
    os.fsync(stream.fileno())


def sign_candidate(source, destination, expected_sha256, thumbprint, timestamp_url,
                   backend=windows_backend):
    source = Path(os.path.abspath(source))
    destination = Path(os.path.abspath(destination))
    receipt_path = Path(str(destination) + '.signing.json')
    if not isinstance(expected_sha256, str) or not re.fullmatch('[0-9a-fA-F]{64}', expected_sha256):
        raise SigningError('INVALID_SOURCE_HASH')
    if not isinstance(thumbprint, str) or not re.fullmatch('[0-9a-fA-F]{40}', thumbprint):
        raise SigningError('INVALID_CERTIFICATE_THUMBPRINT')
    thumbprint = thumbprint.upper()
    _timestamp(timestamp_url)
    for path in (source, destination, receipt_path):
        _plain_path(path)
    if (source == destination or source.suffix.lower() != '.exe'
            or destination.suffix.lower() != '.exe'
            or not destination.parent.is_dir()):
        raise SigningError('INVALID_RELEASE_PATH')
    if os.path.lexists(destination) or os.path.lexists(receipt_path):
        raise SigningError('DESTINATION_ALREADY_EXISTS')
    try:
        with _read_locked(source) as original:
            if original.read(2) != b'MZ' or _hash(original) != expected_sha256.lower():
                raise SigningError('SOURCE_HASH_OR_FORMAT_MISMATCH')
            cert = backend('inspect', source, thumbprint, timestamp_url)
            if (not isinstance(cert, dict) or cert.get('thumbprint') != thumbprint
                    or cert.get('selfIssued') is not False
                    or any(cert.get(key) is not True for key in (
                        'hasPrivateKey', 'codeSigningEku', 'chainValid', 'currentlyValid'))):
                raise SigningError('CERTIFICATE_NOT_RELEASE_READY')
            receipt = dict(schema=1, status='IN_PROGRESS', source=str(source),
                destination=str(destination), sourceSha256=expected_sha256.lower(),
                certificateThumbprint=thumbprint, timestampUrl=timestamp_url,
                signatureVerified=False, recipientWorkflowAccepted=False,
                certificateRevocationChecked=False)
            # Exclusive creation: an old receipt/candidate is never overwritten.
            with receipt_path.open('x', encoding='utf-8') as journal:
                _write_receipt(journal, receipt)
                try:
                    with destination.open('xb') as staged:
                        shutil.copyfileobj(original, staged, 1024 * 1024)
                        staged.flush()
                        os.fsync(staged.fileno())
                    backend('sign', destination, thumbprint, timestamp_url)
                    with _read_locked(destination) as signed:
                        verified = backend('verify', destination, thumbprint, timestamp_url)
                        if (not isinstance(verified, dict) or verified.get('status') != 'Valid'
                                or verified.get('signerThumbprint') != thumbprint
                                or verified.get('timestampPresent') is not True):
                            raise SigningError('SIGNATURE_OR_TIMESTAMP_REJECTED')
                        receipt['signedSha256'] = _hash(signed)
                    if _hash(original) != expected_sha256.lower():
                        raise SigningError('ORIGINAL_CHANGED')
                    receipt.update(status='SIGNED_VERIFIED', signatureVerified=True)
                    _write_receipt(journal, receipt)
                    return receipt
                except Exception:
                    receipt.update(status='FAILED_RETAINED', signatureVerified=False,
                                   failureCode='SIGNING_TRANSACTION_FAILED')
                    _write_receipt(journal, receipt)
                    raise SigningError('SIGNING_TRANSACTION_FAILED; COPY_AND_RECEIPT_RETAINED') from None
    except SigningError:
        raise
    except Exception:
        raise SigningError('SIGNING_PREFLIGHT_FAILED') from None


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('source', 'destination', 'expected-sha256', 'thumbprint', 'timestamp-url'):
        parser.add_argument('--' + name, required=True)
    args = parser.parse_args(argv)
    try:
        result = sign_candidate(**vars(args))
    except SigningError as error:
        print(json.dumps({'status': 'REJECTED', 'code': str(error)}))
        return 1
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
