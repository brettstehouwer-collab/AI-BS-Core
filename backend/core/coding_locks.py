"""Process-owned file locks, automatically released by the OS on worker exit."""
from contextlib import contextmanager
import hashlib
import os
from pathlib import Path


@contextmanager
def record_lock(path):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    handle = path.open('a+b')
    acquired = False
    try:
        if path.stat().st_size == 0:
            handle.write(b'0')
            handle.flush()
        handle.seek(0)
        if os.name == 'nt':
            import msvcrt
            msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
        else:
            import fcntl
            fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        acquired = True
        yield
    except OSError as exc:
        if not acquired:
            raise ValueError('Another operation holds the coding task or repository lock') from exc
        raise
    finally:
        if acquired:
            handle.seek(0)
            if os.name == 'nt':
                import msvcrt
                msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                import fcntl
                fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
        handle.close()


def task_lock(folder):
    return record_lock(Path(folder)/'state.lock')


def repository_lock(store, repository):
    identity = os.path.normcase(str(Path(repository).resolve()))
    key = hashlib.sha256(identity.encode('utf-8')).hexdigest()
    return record_lock(Path(store).parent/'coding_locks'/(key+'.lock'))
