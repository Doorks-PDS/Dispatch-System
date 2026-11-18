"""Read-only compatibility check; does NOT install, modify, or deploy any files.

Run BEFORE unzipping the cumulative package, using its two scripts directory files:
python3 scripts/check_cumulative_baseline.py --root ~/doorks-deploy-edit

This check compares current local files to the Nov 18 uploaded project snapshot.
If it fails, stop and reconcile newer local changes rather than overwriting them.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path


def inspect(root: Path, manifest: dict) -> list[str]:
    root = root.expanduser().resolve()
    problems = []
    for rel, entry in manifest['paths'].items():
        candidate = (root / rel)
        # Never allow manifest path traversal or following symlinks outside checkout.
        if candidate.resolve().is_relative_to(root) is False:
            problems.append(f'UNSAFE PATH: {rel}')
            continue
        if candidate.is_symlink():
            problems.append(f'SYMLINK: {rel}')
            continue
        expected = entry.get('baseline_sha256')
        if expected is None:
            if candidate.exists():
                problems.append(f'NEW FILE CONFLICT: {rel}')
        elif not candidate.is_file():
            problems.append(f'MISSING BASELINE FILE: {rel}')
        else:
            actual = hashlib.sha256(candidate.read_bytes()).hexdigest()
            if actual != expected:
                problems.append(f'LOCAL FILE CHANGED: {rel}')
    return problems


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--root', required=True, type=Path)
    p.add_argument('--manifest', type=Path, default=Path(__file__).with_name('cumulative_baseline_manifest.json'))
    args = p.parse_args()
    if not args.root.expanduser().is_dir():
        p.error('Checkout directory does not exist')
    data = json.loads(args.manifest.read_text(encoding='utf-8'))
    failures = inspect(args.root, data)
    if failures:
        print(f'BLOCKED: {len(failures)} baseline mismatch(es). Do not unzip over these files.')
        for msg in failures:
            print('  '+msg)
        return 1
    print(f'PASS: {len(data["paths"])} patch paths match the Nov 18 uploaded source baseline.')
    print('This confirms only source compatibility; not production readiness or clean Git status.')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
