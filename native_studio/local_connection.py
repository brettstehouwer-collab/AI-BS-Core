"""Automatic current-user Windows connection to the owned loopback backend.

No credential enumeration, network discovery, server startup or bundled secret.
The service publishes only after its own process owns the exact loopback port.
Clients revalidate the listener identity for every use; remote origins get none
of this local authentication material.
"""
from __future__ import annotations

import asyncio
from dataclasses import asdict, dataclass
import json
import math
import ntpath
import os
import re
import socket
import threading
import time

ORIGIN = 'http://127.0.0.1:8080'
TARGET = 'AI-BS/Native/LocalBackend/v1/127.0.0.1:8080'
MAX_BLOB = 2400
_probe_activity = threading.local()


def _probe_counts():
    return (getattr(_probe_activity, 'attempts', 0),
            getattr(_probe_activity, 'connected', 0))


class LocalConnectionError(RuntimeError):
    pass


def _unavailable():
    return LocalConnectionError('The private local connection is not ready. Start the local AI-BS service and try again; no API key entry is required.')


@dataclass(frozen=True)
class ServiceIdentity:
    pid: int
    created: float
    exe: str
    owner_sid: str


def _validate_identity(value):
    if (not isinstance(value, ServiceIdentity) or isinstance(value.pid, bool)
            or not isinstance(value.pid, int) or value.pid <= 0
            or isinstance(value.created, bool) or not isinstance(value.created, (int, float))
            or not math.isfinite(value.created) or value.created <= 0
            or not isinstance(value.exe, str) or not ntpath.isabs(value.exe)
            or not isinstance(value.owner_sid, str)
            or not re.fullmatch(r'S-\d+(?:-\d+)+', value.owner_sid)):
        raise _unavailable()
    return value


def _same_service(left, right):
    _validate_identity(left); _validate_identity(right)
    return (left.pid == right.pid and left.created == right.created
            and ntpath.normcase(ntpath.normpath(left.exe)) == ntpath.normcase(ntpath.normpath(right.exe))
            and left.owner_sid == right.owner_sid)


def _process_identity(pid):
    if os.name != 'nt':
        raise _unavailable()
    import psutil
    import win32api
    import win32con
    import win32security
    handle = win32api.OpenProcess(win32con.PROCESS_QUERY_INFORMATION, False, pid)
    try:
        token = win32security.OpenProcessToken(handle, win32con.TOKEN_QUERY)
        try:
            sid = win32security.ConvertSidToStringSid(win32security.GetTokenInformation(token, win32security.TokenUser)[0])
        finally:
            token.Close()
        process = psutil.Process(pid)
        return _validate_identity(ServiceIdentity(pid, process.create_time(), process.exe(), sid))
    finally:
        handle.Close()


def _current_identity():
    return _process_identity(os.getpid())


def _listener_identity():
    import psutil
    entries = psutil.net_connections(kind='tcp')
    listeners = [entry for entry in entries
                 if entry.status == psutil.CONN_LISTEN and entry.laddr.port == 8080]
    # Credentials target literal IPv4 loopback. A separate ::1 listener (for
    # example WSL forwarding) is never selected or given these credentials.
    if not listeners:
        # Some current Windows hosts report their bound listener row as raw
        # state0/NONE while accepted connections retain ESTABLISHED correctly.
        # NONE alone never proves listening. It only admits an exact, byte-free
        # peer ownership probe when the candidate row is unique and loopback.
        candidates = [entry for entry in entries
                      if entry.status == psutil.CONN_NONE and entry.laddr.port == 8080
                      and not getattr(entry, 'raddr', ())]
        if not candidates:
            return None
        if any(entry.laddr.ip not in {'127.0.0.1', '::1'} for entry in candidates):
            raise _unavailable()
        ipv4 = [entry for entry in candidates if entry.laddr.ip == '127.0.0.1']
        if not ipv4:
            return None
        if len(ipv4) != 1 or type(ipv4[0].pid) is not int or ipv4[0].pid <= 0:
            raise _unavailable()
        return _established_peer_identity(ipv4[0].pid)
    if any(entry.laddr.ip not in {'127.0.0.1', '::1'} for entry in listeners):
        raise _unavailable()
    ipv4 = [entry for entry in listeners if entry.laddr.ip == '127.0.0.1']
    if not ipv4:
        return None
    if len(ipv4) != 1 or not ipv4[0].pid:
        raise _unavailable()
    return _process_identity(ipv4[0].pid)


def _established_peer_identity(candidate_pid):
    """Prove an anomalous row using its exact accepted connection's kernel PID.

    No HTTP, authentication or application bytes are sent. Keep the probe open
    while querying the complete reverse tuple; PID reuse is fenced by process
    identity both before and after observation. Existing owner/vault checks are
    still applied by LocalConnection to the returned identity.
    """
    import psutil
    try:
        before = _validate_identity(_process_identity(candidate_pid))
        if before.pid != candidate_pid:
            raise _unavailable()
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
            probe.settimeout(1.0)
            _probe_activity.attempts = _probe_counts()[0] + 1
            probe.connect(('127.0.0.1', 8080))
            _probe_activity.connected = _probe_counts()[1] + 1
            local_ip, local_port = probe.getsockname()
            if (probe.getpeername() != ('127.0.0.1', 8080) or local_ip != '127.0.0.1'
                    or type(local_port) is not int or not 0 < local_port <= 65535):
                raise _unavailable()
            deadline = time.monotonic() + 1.0
            while True:
                peers = [entry for entry in psutil.net_connections(kind='tcp')
                         if entry.laddr.ip == '127.0.0.1' and entry.laddr.port == 8080
                         and getattr(entry, 'raddr', ())
                         and entry.raddr.ip == local_ip and entry.raddr.port == local_port]
                if peers:
                    if (len(peers) != 1 or type(peers[0].pid) is not int
                            or peers[0].pid != candidate_pid):
                        raise _unavailable()
                    if peers[0].status == psutil.CONN_ESTABLISHED:
                        after = _process_identity(candidate_pid)
                        if not _same_service(before, after):
                            raise _unavailable()
                        return after
                    # A known handshake state may settle within the existing
                    # deadline, but is never itself proof. NONE, closing states,
                    # different PIDs and ambiguity still reject immediately.
                    if peers[0].status not in (psutil.CONN_SYN_SENT, psutil.CONN_SYN_RECV):
                        raise _unavailable()
                if time.monotonic() >= deadline:
                    raise _unavailable()
                time.sleep(.025)
    except LocalConnectionError:
        raise
    except Exception:
        raise _unavailable() from None


class WindowsCredentialVault:
    """One exact Generic Credential in this Windows user's local-machine vault."""
    def read(self):
        if os.name != 'nt':
            raise _unavailable()
        import win32cred
        import pywintypes
        try:
            raw = win32cred.CredRead(TARGET, win32cred.CRED_TYPE_GENERIC)['CredentialBlob']
            if not isinstance(raw, bytes) or len(raw) > MAX_BLOB:
                raise _unavailable()
            # CredWrite accepts Unicode and CredRead returns its UTF-16LE bytes.
            return raw.decode('utf-16-le').encode('utf-8')
        except pywintypes.error as error:
            if error.winerror == 1168:  # Credential not found, not access denied.
                return None
            raise _unavailable() from None

    def write(self, blob, owner_sid):
        if os.name != 'nt' or not isinstance(blob, bytes) or len(blob) > MAX_BLOB:
            raise _unavailable()
        import win32cred
        text = blob.decode('utf-8')
        if len(text.encode('utf-16-le')) > MAX_BLOB:
            raise _unavailable()
        win32cred.CredWrite({'Type': win32cred.CRED_TYPE_GENERIC,
                             'TargetName': TARGET,
                             'UserName': owner_sid,
                             'CredentialBlob': text,
                             'Persist': win32cred.CRED_PERSIST_LOCAL_MACHINE,
                             'Comment': 'AI-BS private local service connection; current Windows user only.'}, 0)


class LocalConnection:
    def __init__(self, *, vault=None, current_identity=None, listener_identity=None):
        self.vault = vault if vault is not None else WindowsCredentialVault()
        self.current_identity = current_identity or _current_identity
        self.listener_identity = listener_identity or _listener_identity

    def publish_if_owned(self, secret):
        try:
            if not isinstance(secret, str) or not secret.strip():
                return False
            current = _validate_identity(self.current_identity())
            try:
                listener = self.listener_identity()
            except LocalConnectionError:
                # Startup may expose a bound row before its accept loop is
                # ready. Refuse publication now; the bounded owner task waits.
                # Credential writes remain outside this retryable observation.
                return False
            if listener is None or not _same_service(current, listener):
                return False
            blob = json.dumps({'schema': 1, 'origin': ORIGIN,
                               'service': asdict(current), 'secret': secret}, allow_nan=False).encode('utf-8')
            if len(blob) > MAX_BLOB:
                raise _unavailable()
            self.vault.write(blob, current.owner_sid)
            return True
        except LocalConnectionError:
            raise
        except Exception:
            raise _unavailable() from None

    def headers(self):
        try:
            blob = self.vault.read()
            if blob is None:
                return {}
            if not isinstance(blob, bytes) or len(blob) > MAX_BLOB:
                raise _unavailable()
            data = json.loads(blob)
            if (not isinstance(data, dict) or type(data.get('schema')) is not int or data['schema'] != 1
                    or data.get('origin') != ORIGIN or not isinstance(data.get('secret'), str)
                    or not data['secret'].strip()):
                raise _unavailable()
            saved = _validate_identity(ServiceIdentity(**data['service']))
            current = _validate_identity(self.current_identity())
            listener = self.listener_identity()
            if (current.owner_sid != saved.owner_sid or listener is None
                    or not _same_service(saved, listener)):
                raise _unavailable()
            return {'X-Admin-Key': data['secret']}
        except LocalConnectionError:
            raise
        except Exception:
            raise _unavailable() from None


def local_service_headers(base_url=ORIGIN, *, connection=None):
    if base_url != ORIGIN:
        return {}
    # Preserve explicit development launch environments; never forward remotely.
    explicit = os.environ.get('AI_BS_ADMIN_KEY', '').strip()
    if explicit:
        return {'X-Admin-Key': explicit}
    return (connection or LocalConnection()).headers()


def connection_diagnostics(*, connection=None):
    """Read only this application's profile; return no credentials or identities."""
    connection = connection or LocalConnection()
    report = {'available': False, 'stage': 'vault_read'}
    probe_before = _probe_counts()
    try:
        blob = connection.vault.read()
        report['profilePresent'] = blob is not None
        if blob is None:
            return report
        report['stage'] = 'profile_schema'
        if not isinstance(blob, bytes) or len(blob) > MAX_BLOB:
            raise _unavailable()
        data = json.loads(blob)
        if (not isinstance(data, dict) or type(data.get('schema')) is not int
                or data['schema'] != 1 or data.get('origin') != ORIGIN
                or not isinstance(data.get('secret'), str) or not data['secret'].strip()):
            raise _unavailable()
        saved = _validate_identity(ServiceIdentity(**data['service']))
        report['stage'] = 'current_identity'
        current = _validate_identity(connection.current_identity())
        report['currentOwnerMatches'] = current.owner_sid == saved.owner_sid
        report['stage'] = 'listener_identity'
        listener = connection.listener_identity()
        report['listenerPresent'] = listener is not None
        if listener is None:
            return report
        _validate_identity(listener)
        report.update(servicePidMatches=saved.pid == listener.pid,
                      serviceCreationMatches=saved.created == listener.created,
                      serviceExeMatches=ntpath.normcase(ntpath.normpath(saved.exe)) == ntpath.normcase(ntpath.normpath(listener.exe)),
                      serviceOwnerMatches=saved.owner_sid == listener.owner_sid)
        report['stage'] = 'connection_validation'
        report['available'] = bool(connection.headers())
        if report['available']:
            report['stage'] = 'ready'
    except Exception as error:
        report['errorType'] = type(error).__name__
        code = getattr(error, 'winerror', None)
        if type(code) is int:
            report['windowsErrorCode'] = code
    finally:
        probe_after = _probe_counts()
        attempts = probe_after[0] - probe_before[0]
        connected = probe_after[1] - probe_before[1]
        report.update(tcpProbeAttempts=attempts, tcpConnectionsOpened=connected,
                      networkRequestsSent=bool(attempts), httpRequestsSent=False,
                      credentialBytesSent=0)
    return report


def write_connection_diagnostic():
    """Save one credential-free support report privately, without opening the UI."""
    try:
        from datetime import datetime, timezone
        from native_studio.broadcast_ipc import private_profile_root, _secure_directory
        import sys
        base = private_profile_root()
        folder = base / 'NativeDiagnostics'
        _secure_directory(base)
        _secure_directory(folder)
        report = connection_diagnostics()
        report.update(frozen=bool(getattr(sys, 'frozen', False)),
                      profileWritten=False, utc=datetime.now(timezone.utc).isoformat())
        filename = 'local_connection_' + datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ') + '.json'
        with (folder / filename).open('x', encoding='utf-8') as stream:
            json.dump(report, stream, indent=2)
        return report['available']
    except Exception:
        # A support-report storage failure must not open an unhandled-error
        # dialog in a windowed executable or expose private exception details.
        return False


async def publish_when_listening(secret, *, connection=None, attempts=40, interval=0.25):
    """Bounded service-owned startup task; cancellation propagates on shutdown."""
    if not secret:
        return False
    connection = connection or LocalConnection()
    for attempt in range(attempts):
        if await asyncio.to_thread(connection.publish_if_owned, secret):
            return True
        if attempt + 1 < attempts:
            await asyncio.sleep(interval)
    return False
