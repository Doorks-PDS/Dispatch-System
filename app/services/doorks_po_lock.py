"""Cross-process PO / receiving lock scoped to the workspace.

All participating writers need the same shared POSIX filesystem. An OS lock
is advisory: this does not protect separate Render disks or older deployments.
The per-process RLock and thread-local depth allow nested Moses -> legacy
receiving calls without deadlocking flock on a second descriptor.
"""
from contextlib import contextmanager
from pathlib import Path
from threading import RLock, local
import fcntl

_gate = RLock()
_state = local()

@contextmanager
def po_write_lock(request, platform):
    if platform not in ('pds', 'doorks', 'sdc'):
        raise ValueError('Unsupported workspace for PO lock')
    root = Path(request.app.state.data_dir) / 'po_receiving' / platform
    root.mkdir(parents=True, exist_ok=True)
    lock_file = root / '.po_writes.lock'
    with _gate:
        depth = getattr(_state, 'depth', 0)
        if depth:
            # Nested legacy operations keep the single outer filesystem lock.
            if _state.platform != platform:
                raise RuntimeError('Cross-workspace nested PO lock is not supported')
            _state.depth = depth + 1
            try:
                yield
            finally:
                _state.depth -= 1
        else:
            with lock_file.open('a+b') as handle:
                fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
                _state.depth = 1
                _state.platform = platform
                try:
                    yield
                finally:
                    _state.depth = 0
                    _state.platform = None
                    fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
