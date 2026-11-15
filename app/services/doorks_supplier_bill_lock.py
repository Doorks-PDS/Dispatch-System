"""Shared cross-worker lock for Doorks supplier bill writes.

Use in every supplier_bills.json read-modify-write endpoint, including Moses.
An advisory flock works only when all writers participate and share a
filesystem with working POSIX locks; validate this on Render before enabling.
"""
from contextlib import contextmanager
from pathlib import Path
import fcntl
from app.routers import doorks_accounting as accounting, doorks_workflow as workflow

@contextmanager
def supplier_bill_lock(request):
    lock_path: Path = accounting.base(request) / '.supplier_bills.lock'
    with lock_path.open('a+b') as file:
        fcntl.flock(file.fileno(), fcntl.LOCK_EX)
        try:
            with workflow.lock:
                yield
        finally:
            fcntl.flock(file.fileno(), fcntl.LOCK_UN)
