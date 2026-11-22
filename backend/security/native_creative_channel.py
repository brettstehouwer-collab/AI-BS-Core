"""Private pipe resources for a future exact owned creative launch.

No process creation, transport admission or authority grant occurs here. The
launcher must pass ONLY child_handles in its explicit inheritance allowlist,
then call child_started; every failure path must close this resource.
"""
import os
import threading


class CreativePipes:
    def __init__(self):
        if os.name != 'nt':
            raise OSError('Creative inherited pipes require Windows.')
        self._lock = threading.Lock()
        self._fds = set()
        self._closed = False
        self._started = False
        try:
            self._parent_read, self._child_write = os.pipe()
            self._fds.update((self._parent_read, self._child_write))
            self._child_read, self._parent_write = os.pipe()
            self._fds.update((self._child_read, self._parent_write))
            import msvcrt
            self._handles = tuple(msvcrt.get_osfhandle(fd) for fd in
                                  (self._child_read, self._child_write))
            for handle in self._handles:
                os.set_handle_inheritable(handle, True)
        except BaseException:
            self.close()
            raise

    @property
    def child_handles(self):
        with self._lock:
            if self._closed or self._started:
                raise OSError('Child inheritance window is closed.')
            return self._handles

    @property
    def parent_fds(self):
        with self._lock:
            if self._closed:
                raise OSError('Creative channel is closed.')
            return self._parent_read, self._parent_write

    def child_started(self):
        """Release parent copies of child ends AFTER successful owned launch."""
        with self._lock:
            if self._closed:
                raise OSError('Creative channel is closed.')
            if self._started:
                return
            self._release((self._child_read, self._child_write))
            self._started = True

    def _release(self, descriptors):
        error = None
        for fd in descriptors:
            if fd not in self._fds:
                continue
            try:
                os.close(fd)
                self._fds.remove(fd)
            except OSError as caught:
                error = caught
        if error is not None:
            raise error

    def close(self):
        with self._lock:
            self._release(tuple(self._fds))
            self._closed = True

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.close()
