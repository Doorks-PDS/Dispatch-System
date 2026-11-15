"""Offline snapshot and isolated restore verification for a quiesced Doorks data dir.

This utility NEVER restores into the source directory and never edits the source.
A passing test proves archive integrity, not a production-consistent backup.
Use a separately verified backup destination, NOT the same Render disk.
"""
from __future__ import annotations

import argparse
import hashlib
import io
import json
import os
from pathlib import Path, PurePosixPath
import stat
import tempfile
import zipfile

MANIFEST = "__doorks_backup_manifest__.json"


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _source_inventory(source: Path) -> dict[str, tuple[int, int]]:
    """Capture the complete file tree, including empty dirs, without following symlinks."""
    result = {}
    for item in sorted(source.rglob('*')):
        rel = item.relative_to(source).as_posix()
        st = item.lstat()
        if stat.S_ISLNK(st.st_mode):
            raise ValueError(f"Symlink excluded: {rel}")
        if stat.S_ISDIR(st.st_mode):
            result[rel + '/'] = (0, 0)
        elif stat.S_ISREG(st.st_mode):
            result[rel] = (st.st_size, st.st_mtime_ns)
        else:
            raise ValueError(f"Non-regular source entry excluded: {rel}")
    return result


def snapshot(source: Path, destination: Path) -> dict:
    # Reject a symlink *before* resolving it; resolve() erases the evidence.
    source_arg = Path(source)
    if source_arg.is_symlink():
        raise ValueError("Source must be a real directory, not a symlink")
    source = source_arg.resolve(strict=True)
    destination = Path(destination).resolve(strict=False)
    if not source.is_dir():
        raise ValueError("Source must be a real directory")
    if source == destination or source in destination.parents:
        raise ValueError("Backup must be outside the source data directory")
    if destination.exists():
        raise FileExistsError("Backup destination already exists; refusing overwrite")
    destination.parent.mkdir(parents=True, exist_ok=True)
    initial_inventory = _source_inventory(source)
    entries = []
    fd, temp_name = tempfile.mkstemp(prefix='.moses-backup-', suffix='.zip', dir=destination.parent)
    os.close(fd)
    try:
        with zipfile.ZipFile(temp_name, 'w', compression=zipfile.ZIP_DEFLATED, allowZip64=True) as z:
            for item in sorted(source.rglob('*')):
                rel = item.relative_to(source).as_posix()
                st = item.lstat()
                if stat.S_ISLNK(st.st_mode):
                    raise ValueError(f"Symlink excluded: {rel}")
                if stat.S_ISDIR(st.st_mode):
                    continue
                if not stat.S_ISREG(st.st_mode):
                    raise ValueError(f"Non-regular source file excluded: {rel}")
                if rel == MANIFEST:
                    raise ValueError("Reserved manifest filename exists in source")
                data = item.read_bytes()
                # Catch a source write that overlaps this file's read.
                st_after = item.stat()
                if (st.st_size, st.st_mtime_ns) != (st_after.st_size, st_after.st_mtime_ns):
                    raise RuntimeError(f"Source file changed during snapshot: {rel}")
                entries.append({'path': rel, 'size': len(data), 'sha256': _sha(data)})
                z.writestr(rel, data)
            # A single file-level check cannot detect additions, removals, or
            # changes to files already processed. Re-scan the complete tree.
            if _source_inventory(source) != initial_inventory:
                raise RuntimeError("Source directory changed during snapshot; quiesce writes and retry")
            manifest = {'format': 'doorks-data-backup-v1', 'files': entries,
                        'note': 'Consistent only if data writes were quiesced for the full snapshot.'}
            z.writestr(MANIFEST, json.dumps(manifest, sort_keys=True, indent=2))
        verify(Path(temp_name))
        # Also refuse an interrupted snapshot if the live tree changes during
        # archive verification. This is only a detection mechanism: callers must
        # still stop application writes to guarantee a consistent production copy.
        if _source_inventory(source) != initial_inventory:
            raise RuntimeError("Source directory changed during snapshot verification")
        os.replace(temp_name, destination)
        return {'archive': str(destination), 'file_count': len(entries), 'verified': True,
                'production_consistency_verified': False}
    finally:
        if os.path.exists(temp_name):
            os.unlink(temp_name)


def _safe_rel(name: str) -> str:
    p = PurePosixPath(name)
    if not name or name.startswith('/') or '\\' in name or any(x in ('', '.', '..') for x in name.split('/')) or p.is_absolute():
        raise ValueError('Unsafe archive path')
    return name


def verify(archive: Path) -> dict:
    with zipfile.ZipFile(archive) as z:
        names = z.namelist()
        if len(names) != len(set(names)) or MANIFEST not in names:
            raise ValueError('Missing manifest or duplicate archive members')
        for info in z.infolist():
            _safe_rel(info.filename)
            # No symlinks or special files in archive.
            mode = info.external_attr >> 16
            if stat.S_ISLNK(mode) or (mode and stat.S_IFMT(mode) not in (0, stat.S_IFREG)):
                raise ValueError('Unsafe archive member type')
        manifest = json.loads(z.read(MANIFEST))
        if manifest.get('format') != 'doorks-data-backup-v1':
            raise ValueError('Unknown backup format')
        entries = manifest.get('files')
        if not isinstance(entries, list):
            raise ValueError('Invalid manifest entries')
        paths = [_safe_rel(e['path']) for e in entries]
        if len(set(paths)) != len(paths) or sorted(paths + [MANIFEST]) != sorted(names):
            raise ValueError('Manifest/archive member mismatch')
        with tempfile.TemporaryDirectory(prefix='moses-restore-check-') as td:
            root = Path(td)
            for entry in entries:
                data = z.read(entry['path'])
                if len(data) != entry['size'] or _sha(data) != entry['sha256']:
                    raise ValueError(f"Checksum mismatch: {entry['path']}")
                out = root / entry['path']
                out.parent.mkdir(parents=True, exist_ok=True)
                out.write_bytes(data)
                if _sha(out.read_bytes()) != entry['sha256']:
                    raise ValueError('Isolated restoration mismatch')
        return {'file_count': len(entries), 'checksum_verified': True,
                'isolated_restore_verified': True, 'production_consistency_verified': False}


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    sub = p.add_subparsers(dest='mode', required=True)
    a = sub.add_parser('snapshot'); a.add_argument('source'); a.add_argument('archive')
    b = sub.add_parser('verify'); b.add_argument('archive')
    opts = p.parse_args()
    result = snapshot(Path(opts.source), Path(opts.archive)) if opts.mode == 'snapshot' else verify(Path(opts.archive))
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
