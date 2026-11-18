"""Read-only PDS storage health report. No cleanup or modifications are performed.

Usage: python scripts/pds_storage_preflight.py --data-dir /path/to/data
This script avoids opening production data files: it only reads file metadata.
"""
from __future__ import annotations

import argparse
import json
import os
import heapq
from pathlib import Path


def inspect_storage(data_dir: str | Path, *, top_n: int = 12, warning_percent: float = 85.0) -> dict:
    root = Path(data_dir).expanduser().resolve(strict=True)
    if not root.is_dir():
        raise ValueError("Data directory must exist")
    usage = os.statvfs(root)
    total = usage.f_blocks * usage.f_frsize
    available = usage.f_bavail * usage.f_frsize
    used = max(total - usage.f_bfree * usage.f_frsize, 0)
    capacity_used_percent = round(100 * used / total, 2) if total else 100.0
    dirs: dict[str, int] = {}
    # Bounded heap: avoid retaining millions of paths on a large calendar disk.
    largest_heap: list[tuple[int, str]] = []
    calendar_breakdown: dict[str, int] = {}
    keep = max(0, top_n)
    count = 0
    errors: list[str] = []
    # Do not follow symbolic links. This is diagnostic only, even with malformed paths.
    def onerror(exc: OSError):
        errors.append(type(exc).__name__)
    for current, subdirs, files in os.walk(root, followlinks=False, onerror=onerror):
        subdirs[:] = [d for d in subdirs if not (Path(current) / d).is_symlink()]
        for name in files:
            path = Path(current) / name
            try:
                if path.is_symlink():
                    continue
                size = path.stat().st_size
                relative = path.relative_to(root)
                bucket = relative.parts[0] if len(relative.parts) > 1 else '(root files)'
                dirs[bucket] = dirs.get(bucket, 0) + size
                if bucket == 'calendar':
                    group = relative.parts[1] if len(relative.parts) > 2 else '(calendar root)'
                    calendar_breakdown[group] = calendar_breakdown.get(group, 0) + size
                count += 1
                if keep:
                    entry = (size, relative.as_posix())
                    if len(largest_heap) < keep:
                        heapq.heappush(largest_heap, entry)
                    elif entry > largest_heap[0]:
                        heapq.heapreplace(largest_heap, entry)
            except (OSError, ValueError) as exc:
                errors.append(type(exc).__name__)
    largest = [{'path': path, 'bytes': size} for size, path in sorted(largest_heap, key=lambda item: (-item[0], item[1]))]
    return {
        'data_dir': str(root), 'total_bytes': total, 'used_bytes': used,
        'available_bytes': available, 'disk_used_percent': capacity_used_percent,
        'disk_warning': capacity_used_percent >= warning_percent,
        'files_counted': count, 'directory_bytes': dict(sorted(dirs.items(), key=lambda x: -x[1])),
        'largest_files': largest, 'calendar_breakdown_bytes': dict(sorted(calendar_breakdown.items(), key=lambda x: -x[1])), 'scan_errors': errors,
        'read_only': True, 'note': 'Sizes are file metadata; disk usage also includes filesystem overhead and unlinked-open files.'
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--data-dir', required=True, help='Existing persistent data directory')
    parser.add_argument('--top', type=int, default=12)
    parser.add_argument('--warning-percent', type=float, default=85.0)
    args = parser.parse_args()
    try:
        report = inspect_storage(args.data_dir, top_n=args.top, warning_percent=args.warning_percent)
    except (OSError, ValueError) as exc:
        parser.exit(2, f'Storage report unavailable: {exc}\n')
    print(json.dumps(report, indent=2))
    return 0  # Reporting warnings must not block a running business app.


if __name__ == '__main__':
    raise SystemExit(main())
