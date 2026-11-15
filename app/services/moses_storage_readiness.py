"""Read-only storage release diagnostics; do not confuse a path with durable storage."""
from __future__ import annotations

import os
from pathlib import Path


def _mount_info(path: Path, mountinfo: str) -> dict:
    """Identify the enclosing mount; no assumption that a mount is durable."""
    # On macOS /var is commonly a symlink to /private/var.  Test both the
    # supplied pathname and its resolved form against mountinfo entries.
    paths = {str(path.absolute()), str(path.resolve(strict=False))}
    candidates = []
    for line in mountinfo.splitlines():
        fields = line.split(' - ', 1)[0].split()
        if len(fields) < 5:
            continue
        point = fields[4].replace('\\040', ' ')
        if point == '/' or any(p == point or p.startswith(point.rstrip('/') + '/') for p in paths):
            candidates.append(point)
    point = max(candidates, key=len) if candidates else None
    return {'mount_point': point, 'dedicated_mount_detected': bool(point and point != '/')}


def inspect(data_dir: str, *, mountinfo_path='/proc/self/mountinfo', expected_disk_mount: str | None = None) -> dict:
    """Never create a directory or file. No credentials or records returned."""
    path = Path(data_dir).expanduser()
    exists = path.is_dir()
    mount = {'mount_point': None, 'dedicated_mount_detected': False}
    if os.path.isfile(mountinfo_path):
        try:
            mount = _mount_info(path, Path(mountinfo_path).read_text(encoding='utf-8'))
        except OSError:
            pass
    # The Render API reports a disk mount separately from the app's own data-dir
    # setting. Never assume that a writable path is on that disk. Do not create
    # directories or automatically move historical business records.
    expected = Path(expected_disk_mount).expanduser() if expected_disk_mount else None
    configured = path.resolve(strict=False)
    expected_resolved = expected.resolve(strict=False) if expected else None
    on_expected_disk = (configured == expected_resolved or expected_resolved in configured.parents) if expected_resolved else None
    return {
        'expected_disk_mount': str(expected) if expected else None,
        'configured_path_under_expected_disk': on_expected_disk,
        'disk_path_mismatch': on_expected_disk is False,
        'configured_data_dir': str(path),
        'directory_exists': exists,
        'writable_by_process': bool(exists and os.access(path, os.W_OK)),
        **mount,
        'durability_verified': False,
        'deployment_ready': False,
        'note': ('A mount or writable directory is NOT proof of durable Render storage. '
                 'Verify the Render persistent disk/database and perform backup/restore checks before enabling writes.'),
    }
